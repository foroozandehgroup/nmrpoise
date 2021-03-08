"""
optpoise.py
-----------

Module containing optimisation functions.

SPDX-License-Identifier: GPL-3.0-or-later
"""

from .cfhelpers import CostFunctionError

from functools import wraps

import numpy as np
import pybobyqa as pb

# Magic constant which tells us how much to scale each tolerance to when
# scaling by tols. It is basically arbitrarily chosen, but should not have an
# effect on the actual optimisation.
MAGIC_TOL = 0.03

# Constant strings denoting "standard" optimisation outcomes.
MESSAGE_OPT_SUCCESS = ("Optimisation terminated successfully"
                       " due to convergence.")
MESSAGE_OPT_PREMATURE_TERMINATION = ("Optimisation terminated"
                                     " before convergence.")
MESSAGE_OPT_MAXFEV_REACHED = "Maximum function evaluations reached."
MESSAGE_OPT_MAXITER_REACHED = "Maximum iterations reached."


def scale(val, lb, ub, tol, scaleby="bounds"):
    """
    Scales a set of values so that the optimisation behaves better.

    For scaleby="bounds", scales a set of values such that the lower and upper
    bounds for all variables are 0 and 1 respectively). We used to use this.
    As of the current version it's no longer being used.

    For scaleby="tols", scales a set of values such that the tolerances for all
    variables are MAGIC_TOL.

    Parameters
    ----------
    val : ndarray or list
        The unscaled values.
    lb : ndarray or list
        The unscaled lower bounds.
    ub : ndarray or list
        The unscaled upper bounds.
    tol : ndarray or list
        The unscaled tolerances.
    scaleby : str from {"bounds", "tols"}
        Method to scale by.

    Returns
    -------
    scaled_val : ndarray
        The scaled values.
    scaled_lb : ndarray
        The scaled lower bounds.
    scaled_ub : ndarray
        The scaled upper bounds.
    scaled_tol : ndarray
        The scaled tolerances.
    """
    if scaleby not in ["bounds", "tols"]:
        raise ValueError(f"Invalid argument scaleby={scaleby} given.")
    # Convert to ndarray
    val, lb, ub, tol = (np.array(i) for i in (val, lb, ub, tol))
    # Check if any are outside bounds
    if np.any(val < lb) or np.any(val > ub):
        return None
    # Scale them
    if scaleby == "bounds":
        scaled_val = (val - lb)/(ub - lb)
        scaled_lb = (lb - lb)/(ub - lb)  # all 0's
        scaled_ub = (ub - lb)/(ub - lb)  # all 1's
        scaled_tol = tol/(ub - lb)
    elif scaleby == "tols":
        scaled_val = (val - lb) * MAGIC_TOL / tol
        scaled_lb = (lb - lb) * MAGIC_TOL / tol   # all 0's
        scaled_ub = (ub - lb) * MAGIC_TOL / tol
        scaled_tol = tol * MAGIC_TOL / tol        # all MAGIC_TOL's
    return scaled_val, scaled_lb, scaled_ub, scaled_tol


def unscale(scaled_val, orig_lb, orig_ub, orig_tol, scaleby="bounds"):
    """
    Unscales a set of scaled values to their original values.

    Parameters
    ----------
    scaled_val : ndarray or list
        The scaled values.
    orig_lb : ndarray or list
        The *unscaled* lower bounds.
    orig_ub : ndarray or list
        The *unscaled* upper bounds.
    orig_tol : ndarray or list
        The *unscaled* tolerances.
    scaleby : str from {"bounds", "tols"}
        Method to scale by.

    Returns
    -------
    ndarray
        The unscaled values.
    """
    if scaleby not in ["bounds", "tols"]:
        raise ValueError(f"Invalid argument scaleby={scaleby} given.")
    scaled_val, orig_lb, orig_ub, orig_tol = (np.array(i) for i in (scaled_val,
                                                                    orig_lb,
                                                                    orig_ub,
                                                                    orig_tol))
    if scaleby == "bounds":
        return orig_lb + (scaled_val * (orig_ub - orig_lb))
    elif scaleby == "tols":
        return (scaled_val * orig_tol / MAGIC_TOL) + orig_lb


class Simplex():
    """
    Simplex class.
    """
    def __init__(self, x0, method="spendley", length=MAGIC_TOL * 10):
        """
        Initialises a Simplex object.

        Parameters
        ----------
        x0: ndarray
            Initial guess.
        method : str, optional
            Method for construction of initial simplex. Options are:
                - "spendley" : Regular simplex of Spendley et al. (1962) (DOI
                               10.1080/00401706.1962.10490033). This is the
                               default, because it works well.
                - "axis"     : Simplex extended along each axis by a fixed
                               length from x0.
                - "random"   : Every point is randomly generated in [0,1].
                               Don't recommend using this.
        length : float, optional
            A measure of the size of the initial simplex. Defaults to
            MAGIC_TOL * 10, because that's 10 times the tolerances after the
            problem is scaled by tols.
        """
        self.x0 = np.ravel(np.asfarray(x0))
        self.N = np.size(self.x0)

        # Generate simplex
        self.x = np.zeros((self.N + 1, self.N))
        self.f = np.full(self.N + 1, fill_value=np.inf)

        if method == "spendley":
            # Default method.
            # Spendley (1962). DOI 10.1080/00401706.1962.10490033
            # Rosenbrock with x0 = [1.3, 0.7, 0.8, 1.9, 1.2]: 472 nfev, 284 nit
            p = (1/(self.N * np.sqrt(2))) * (self.N - 1 + np.sqrt(self.N + 1))
            q = (1/(self.N * np.sqrt(2))) * (np.sqrt(self.N + 1) - 1)
            self.x[0] = self.x0
            for i in range(1, self.N + 1):
                for j in range(self.N):
                    self.x[i, j] = self.x0[j] + length*p \
                        if j == i - 1 else self.x0[j] + length*q
        elif method == "axis":
            # Axis-by-axis simplex. Each point is just x0 extended along
            # a different axis.
            # Rosenbrock with x0 = [1.3, 0.7, 0.8, 1.9, 1.2]: 566 nfev, 342 nit
            self.x[0] = self.x0
            for i in range(1, self.N + 1):
                for j in range(self.N):
                    self.x[i, j] = self.x0[j] + length \
                        if j == i - 1 else self.x0[j]
        elif method == "random":
            # Every point except x0 is random.
            # Rosenbrock with x0 = [1.3, 0.7, 0.8, 1.9, 1.2]: 705 nfev, 431 nit
            # (average over 1000 iterations)
            self.x[0] = self.x0
            rng = np.random.default_rng()
            for i in range(1, self.N + 1):
                self.x[i] = rng.uniform(size=self.N)
        else:
            raise ValueError(f"invalid simplex generation method "
                             "'{method}' specified")

    def sort(self):
        """
        Sorts the simplex and associated function values in ascending order of
        the cost function, i.e. sim.x[0] contains the current best point,
        sim.x[N] contains the current worst point.
        """
        indices = np.argsort(self.f)
        self.x = np.take(self.x, indices, 0)
        self.f = np.take(self.f, indices, 0)

    def xbar(self):
        """
        Calculates the centroid. Assumes the function values are already
        sorted.
        """
        return np.average(self.x[0:self.N], axis=0)

    def xworst(self):
        """
        Worst point. Assumes the simplex is already sorted.
        """
        return self.x[self.N]

    def replace_worst(self, xnew, fnew):
        """
        Replaces the worst point with the new point xnew, and the corresponding
        function value fnew.
        """
        self.sort()
        self.x[self.N], self.f[self.N] = xnew, fnew

    def shrink(self):
        """
        Performs shrink step (Step 3(f) in Algorithm 8.1.1, Kelley). Doesn't
        evaluate cost functions, only replaces the points!
        """
        for i in range(1, self.N + 1):
            self.x[i] = self.x[0] - (self.x[i] - self.x[0])/2


# Custom exceptions.
class MaxFevalsReached(Exception):
    pass


class MaxItersReached(Exception):
    pass


class EarlyTerminationError(Exception):
    pass


def deco_count(fn):
    """
    Decorator which counts the number of times a function has been called, as
    long as the function does not return np.inf. This makes sure that
    acquire_nmr.calls is not incremented when an out-of-bounds value is
    "sampled".
    """
    @wraps(fn)
    def counter(*args, **kwargs):
        result = fn(*args, **kwargs)
        if result != np.inf:
            counter.calls += 1
        return result
    counter.calls = 0
    return counter


def deco_cf(maxfev):
    """
    Decorator factory which returns a decorator for cost functions. The
    decorator in turn causes the cost function to raise MaxFevalsReached if its
    number of calls is greater than ``maxfev``.

    Usage
    =====
    The decorator factory itself must take a parameter ``maxfev`` so that the
    maximum number of function evaluations can be dynamically chosen. Thus,

    >>> deco_cf(maxfev=maxfev)

    returns a decorator, which can then be used to decorate a cost function:

    >>> cf = deco_cf(maxfev=maxfev)(cf)
    """
    def decorator(fn):
        @wraps(fn)
        def decorated_cf(*args, **kwargs):
            # Check if maximum function evaluations have been reached.
            if fn.calls >= maxfev:
                raise MaxFevalsReached
            # If not, then we can try to run the original function. The
            # parameters returned are the cost function value, a flag
            # indicating whether to break, and a message.
            else:
                return fn(*args, **kwargs)
        return decorated_cf
    return decorator


class OptResult:
    """
    A *very* generic class that exists solely to store the result of an
    optimisation. There's no functionality needed because this is just used
    as a way of passing a message back to the calling script.
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return str(self.__dict__)


def nelder_mead(cf, x0, xtol, scaled_lb, scaled_ub,
                args=(), maxfev=0, simplex_method="spendley"):
    """
    Nelder-Mead optimiser, as described in Section 8.1 of Kelley, "Iterative
    Methods for Optimization".

    Parameters
    ----------
    cf : function
        The cost function. For POISE, this means acquire_nmr(), not the
        user-defined cost function. However in general, this can be any cost
        function. The cost function *must* be decorated with deco_count() (for
        POISE, this is already done).
    x0 : ndarray or list
        Initial point for optimisation. This should already be scaled.
    xtol : ndarray or list
        Tolerances for each optimisation dimension. This should already be
        scaled.
    scaled_lb : ndarray
        Scaled lower bounds for the optimisation.
    scaled_ub : ndarray
        Scaled upper bounds for the optimisation. This is used to place an
        upper bound on the simplex size.
    args : tuple, optional
        A tuple of arguments to pass to the cost function.
    maxfev : int, optional
        Maximum function evaluations to use. Defaults to 500 times the number
        of parameters.
    simplex_method : str, optional
        Method for generation of initial simplex.

    Returns
    -------
    OptResult
        Object which contains the following attributes:
            xbest (ndarray)   : Optimal values for the optimisation.
            fbest (float)     : Cost function at the optimum.
            niter (int)       : Number of iterations.
            nfev (int)        : Number of function evaluations. Note that in
                                the specific context of NMR optimisation, this
                                is in general not equal to the number of
                                experiments acquired.
            simplex (ndarray) : (N+1, N)-sized matrix of the final simplex.
            fvals (ndarray)   : List of corresponding cost functions at each
                                point of the simplex.
            message (str)     : Message indicating reason for termination.

    Notes
    -----
    The scipy implementation has a few tricks which are useful in making the
    actual computation run faster. However, here we have ignored these in
    favour of readability, since the speed of the optimisation is largely
    limited by the acquisition time of the NMR experiment.
    """

    # Convert x0 to vector
    x0 = np.asfarray(x0).flatten()
    xtol = np.asfarray(xtol).flatten()
    N = x0.size

    # Default maxiter and maxfev. We could make this customisable in future.
    # For example, we could use TopSpin's `expt' to calculate the duration of
    # one experiment, and then set maxiter to not overshoot a given time.
    maxiter = 500 * N
    if maxfev <= 0:
        maxfev = 500 * N
    # Decorate the cost function to raise MaxFevalsReached
    cf = deco_cf(maxfev)(cf)

    # Check length of xtol
    if len(x0) != len(xtol):
        raise ValueError("Nelder-Mead: x0 and xtol have incompatible lengths")

    # Create and initialise simplex object.
    sim = Simplex(x0, method=simplex_method, length=MAGIC_TOL * 10)
    # Number of iterations. Function evaluations are stored as cf.calls.
    niter = 0

    # Set up parameters for Nelder-Mead.
    # Notation follows that used in Section 8.1 of Kelley, 'Iterative Methods
    # for Optimization'.
    mu_ic = -0.5   # Inside contraction parameter
    mu_oc = 0.5    # Outside contraction parameter
    mu_r = 1       # Reflect parameter
    mu_e = 2       # Expansion parameter

    # Helper function.
    def xnew(mu, sim):
        return ((1 + mu) * sim.xbar()) - (mu * sim.xworst())

    def converged(sim, xtol):
        """
        Convergence criteria. To be converged, each dimension of the simplex
        must have a range smaller than or equal to the corresponding xtol in
        that dimension.
        """
        simplex_range = np.amax(sim.x, axis=0) - np.amin(sim.x, axis=0)
        return all(np.less_equal(simplex_range, xtol))
        # Scipy convergence criteria. Assumes that the simplex is already
        # sorted. It is slightly looser (i.e. will converge before mine),
        # but hardly makes a difference to the average fevals (tested on
        # Rosenbrock function).
        #
        # return np.max(np.ravel(np.abs(sim[1:] - sim[0]))) <= xtol[0]

    # Create temporary list of points evaluated during this iteration (and
    # their corresponding cost function values).
    iter_xs, iter_fs = [], []
    try:
        # Evaluate the cost function for the initial simplex.
        # Steps 1 and 2 in Algorithm 8.1.1
        for i in range(N + 1):
            sim.f[i] = cf(sim.x[i], *args)
            # Sort simplex
            sim.sort()

        # Main loop.
        while not converged(sim, xtol):
            # Proceed to next iteration.
            niter += 1
            sim.sort()  # for good measure

            # Check number of iterations.
            if niter >= maxiter:
                raise MaxItersReached

            # Reset both lists.
            iter_xs, iter_fs = [], []

            # Step 3(a)
            x_r = xnew(mu_r, sim)  # shorthand for x(mu_r)
            iter_xs.append(x_r)
            f_r = cf(x_r, *args)
            iter_fs.append(f_r)

            # Step 3(b): Reflect (+ 3g if needed)
            if sim.f[0] <= f_r and f_r < sim.f[N - 1]:
                sim.replace_worst(x_r, f_r)
                sim.sort()  # Step 3(g)
                continue

            # Step 3(c): Expand (+ 3g if needed)
            if f_r < sim.f[0]:
                x_e = xnew(mu_e, sim)
                iter_xs.append(x_e)
                f_e = cf(x_e, *args)
                iter_fs.append(f_e)
                if f_e < f_r:
                    sim.replace_worst(x_e, f_e)
                else:
                    sim.replace_worst(x_r, f_r)
                sim.sort()  # Step 3(g)
                continue

            # Step 3(d): Outside contraction (+ 3f and 3g if needed)
            if sim.f[N - 1] <= f_r and f_r < sim.f[N]:
                x_oc = xnew(mu_oc, sim)
                iter_xs.append(x_oc)
                f_c = cf(x_oc, *args)
                iter_fs.append(f_c)
                if f_c <= f_r:
                    sim.replace_worst(x_oc, f_c)
                    sim.sort()  # Step 3(g)
                    continue
                else:
                    if cf.calls >= maxfev - N:             # Step 3(f)
                        raise MaxFevalsReached
                    sim.shrink()
                    for i in range(1, N + 1):
                        sim.f[i] = cf(sim.x[i], *args)
                    sim.sort()  # Step 3(g)
                    continue

            # Step 3(e): Inside contraction (+ 3f and 3g if needed)
            if f_r >= sim.f[N]:
                x_ic = xnew(mu_ic, sim)
                iter_xs.append(x_ic)
                f_c = cf(x_ic, *args)
                iter_fs.append(f_c)
                if f_c < sim.f[N]:
                    sim.replace_worst(x_ic, f_c)
                    sim.sort()  # Step 3(g)
                    continue
                else:
                    if cf.calls >= maxfev - N:             # Step 3(f)
                        raise MaxFevalsReached
                    sim.shrink()
                    for i in range(1, N + 1):
                        sim.f[i] = cf(sim.x[i], *args)
                    sim.sort()  # Step 3(g)
                    continue
        # END while loop
    except MaxItersReached:
        message = MESSAGE_OPT_MAXITER_REACHED
    except MaxFevalsReached:
        message = MESSAGE_OPT_MAXFEV_REACHED
    except CostFunctionError as e:
        # Check if a value was returned: if so, add it to iter_fs (iter_xs will
        # already have been updated prior to cost function calculation).
        if isinstance(e.cf_val, (int, float)):
            iter_fs.append(e.cf_val)
        message = MESSAGE_OPT_PREMATURE_TERMINATION
        if e.message.strip() != "":
            message += ("\nReason: " + e.message)
    else:
        message = MESSAGE_OPT_SUCCESS

    # sort the simplex in ascending order of fvals
    sim.sort()
    # Check whether the simplex or iter_fs has the lowest cost function.
    if len(iter_fs) != 0 and np.amin(iter_fs) < sim.f[0]:
        xbest, fbest = iter_xs[np.argmin(iter_fs)], np.amin(iter_fs)
    else:
        xbest, fbest = sim.x[0], sim.f[0]

    return OptResult(xbest=xbest, fbest=fbest,
                     niter=niter, nfev=cf.calls,
                     simplex=sim.x, fvals=sim.f,
                     message=message)


def multid_search(cf, x0, xtol, scaled_lb, scaled_ub,
                  args=(), maxfev=0, simplex_method="spendley"):
    """
    Multidimensional search optimiser, as described in Secion 8.2 of Kelley,
    "Iterative Methods for Optimization".

    Parameters
    ----------
    cf : function
        The cost function. For POISE, this means acquire_nmr(), not the
        user-defined cost function. However in general, this can be any cost
        function. The cost function *must* be decorated with deco_count() (for
        POISE, this is already done).
    x0 : ndarray or list
        Initial point for optimisation. This should already be scaled.
    xtol : ndarray or list
        Tolerances for each optimisation dimension. This should already be
        scaled.
    scaled_lb : ndarray
        Scaled lower bounds for the optimisation.
    scaled_ub : ndarray
        Scaled upper bounds for the optimisation. This is used to place an
        upper bound on the simplex size.
    args : tuple, optional
        A tuple of arguments to pass to the cost function.
    maxfev : int, optional
        Maximum function evaluations to use. Defaults to 500 times the number
        of parameters.
    simplex_method : str, optional
        Method for generation of initial simplex.

    Returns
    -------
    OptResult
        Object which contains the following attributes:
            xbest (ndarray)   : Optimal values for the optimisation.
            fbest (float)     : Cost function at the optimum.
            niter (int)       : Number of iterations.
            nfev (int)        : Number of function evaluations. Note that in
                                the specific context of NMR optimisation, this
                                is in general not equal to the number of
                                experiments acquired.
            simplex (ndarray) : (N+1, N)-sized matrix of the final simplex.
            fvals (ndarray)   : List of corresponding cost functions at each
                                point of the simplex.
            message (str)     : Message indicating reason for termination.
    """
    # Convert x0 to vector
    x0 = np.asfarray(x0).flatten()
    xtol = np.asfarray(xtol).flatten()
    N = x0.size

    # Default maxiter and maxfev. We could make this customisable in future.
    # For example, we could use TopSpin's `expt' to calculate the duration of
    # one experiment, and then set maxiter to not overshoot a given time.
    maxiter = 500 * N
    if maxfev <= 0:
        maxfev = 500 * N
    # Decorate cost function so that it handles MaxFevalsReached and
    # CostFunctionError exceptions correctly.
    cf = deco_cf(maxfev)(cf)

    # Check length of xtol
    if len(x0) != len(xtol):
        raise ValueError("Multidimensional search: x0 and xtol have "
                         "incompatible lengths")

    # Create and initialise simplex object.
    sim = Simplex(x0, method=simplex_method, length=MAGIC_TOL * 10)
    # Number of iterations. Function evaluations are stored as cf.calls.
    niter = 0

    # Set up parameters for Nelder-Mead.
    mu_e = 2       # Expansion parameter
    mu_c = 0.5     # Contraction parameter

    def converged(sim, xtol):
        """
        Convergence criteria. To be converged, each dimension of the simplex
        must have a range smaller than or equal to the corresponding xtol in
        that dimension.
        """
        simplex_range = np.amax(sim.x, axis=0) - np.amin(sim.x, axis=0)
        return all(np.less_equal(simplex_range, xtol))
        # Scipy convergence criteria. Assumes that the simplex is already
        # sorted. It is slightly looser (i.e. will converge before mine),
        # but hardly makes a difference to the average fevals (tested on
        # Rosenbrock function).
        #
        # return np.max(np.ravel(np.abs(sim[1:] - sim[0]))) <= xtol[0]

    # Create temporary list of points evaluated during this iteration (and
    # their corresponding cost function values).
    iter_xs, iter_fs = [], []
    # Flag to indicate whether we should break out of the main loop. If a
    # CostFunctionError is raised in the previous iteration, this will be
    # incremented.
    break_on_next_iter = 0

    try:
        # Evaluate the cost function for the initial simplex.
        # Steps 1 and 2 in Algorithm 8.2.1
        for i in range(N + 1):
            sim.f[i] = cf(sim.x[i], *args)
            # Sort simplex
            sim.sort()

        # Main loop.
        while not converged(sim, xtol):
            niter += 1
            sim.sort()  # for good measure

            # Check number of iterations
            if niter >= maxiter:
                raise MaxItersReached

            # Reset the xs and fs lists.
            iter_xs, iter_fs = [], []

            # Step 3(a): Reflect
            r_j = np.zeros((N, N))
            f_r_j = np.zeros(N)
            for j in range(1, N + 1):
                r_j[j - 1] = sim.x[0] - (sim.x[j] - sim.x[0])
                iter_xs.append(r_j[j - 1])
                f_r_j[j - 1] = cf(r_j[j - 1], *args)
                iter_fs.append(f_r_j[j - 1])

            # Step 3(b): Expand
            if sim.f[0] > np.amin(f_r_j):
                e_j = np.zeros((N, N))
                f_e_j = np.zeros(N)
                for j in range(1, N + 1):
                    e_j[j - 1] = sim.x[0] - mu_e * (sim.x[j] - sim.x[0])
                    iter_xs.append(e_j[j - 1])
                    f_e_j[j - 1] = cf(e_j[j - 1], *args)
                    iter_fs.append(f_e_j[j - 1])
                # Replace the values, 3(b)(ii)
                if np.amin(f_r_j) > np.amin(f_e_j):
                    for j in range(1, N + 1):
                        sim.x[j] = e_j[j - 1]
                        sim.f[j] = f_e_j[j - 1]
                else:
                    for j in range(1, N + 1):
                        sim.x[j] = r_j[j - 1]
                        sim.f[j] = f_r_j[j - 1]
                sim.sort()  # Step 3(d)
                continue
            # Step 3(c): Contract
            else:
                for j in range(1, N + 1):
                    sim.x[j] = sim.x[0] + mu_c * (sim.x[j] - sim.x[0])
                    iter_xs.append(sim.x[j])
                    sim.f[j] = cf(sim.x[j], *args)
                    iter_fs.append(sim.f[j])
                sim.sort()  # Step 3(d)
                continue
    except MaxItersReached:
        message = MESSAGE_OPT_MAXITER_REACHED
    except MaxFevalsReached:
        message = MESSAGE_OPT_MAXFEV_REACHED
    except CostFunctionError as e:
        # Check if a value was returned: if so, add it to iter_fs (iter_xs will
        # already have been updated prior to cost function calculation).
        if isinstance(e.cf_val, (int, float)):
            iter_fs.append(e.cf_val)
        message = MESSAGE_OPT_PREMATURE_TERMINATION
        if e.message.strip() != "":
            message += ("\nReason: " + e.message)
    else:
        message = MESSAGE_OPT_SUCCESS

    # sort the simplex in ascending order of fvals
    sim.sort()
    # Check whether the simplex or iter_fs has the lowest cost function.
    if len(iter_fs) != 0 and np.amin(iter_fs) < sim.f[0]:
        xbest, fbest = iter_xs[np.argmin(iter_fs)], np.amin(iter_fs)
    else:
        xbest, fbest = sim.x[0], sim.f[0]

    return OptResult(xbest=xbest, fbest=fbest,
                     niter=niter, nfev=cf.calls,
                     simplex=sim.x, fvals=sim.f,
                     message=message)


def pybobyqa_interface(cf, x0, xtol, scaled_lb, scaled_ub,
                       args=(), maxfev=0):
    """
    Interface to pybobyqa.solve() which takes similar arguments to the other
    two optimisation functions and returns an OptResult object.

    Parameters
    ----------
    cf : function
        The cost function. For POISE, this means acquire_nmr(), not the
        user-defined cost function. However in general, this can be any cost
        function.
    x0 : ndarray or list
        Initial point for optimisation. This must already be scaled by tols.
    xtol : ndarray or list
        Tolerances for each optimisation dimension. This is actually not used
        at all and is only here so that there is a unified interface for all
        three optimisers.
    args : tuple, optional
        A tuple of arguments to pass to the cost function.
    simplex_method : str, optional
        Method for generation of initial simplex.
    scaled_lb : ndarray, optional
        Scaled lower bounds for the optimisation.
    scaled_ub : ndarray, optional
        Scaled upper bounds for the optimisation. This is used to place an
        upper bound on the simplex size.

    Returns
    -------
    OptResult
        Object which contains the following attributes:
            xbest (ndarray)   : Optimal values for the optimisation.
            fbest (float)     : Cost function at the optimum.
            niter (int)       : Number of iterations. solve() does not actually
                                provide this information directly, so this
                                value is simply set to zero. (It is indirectly
                                available if diagnostic info is requested.)
            nfev (int)        : Number of function evaluations. Note that in
                                the specific context of NMR optimisation, this
                                is in general not equal to the number of
                                experiments acquired.
            message (str)     : Message indicating reason for termination.
    """
    x0 = np.asfarray(x0).flatten()
    # Calculate maxfev
    N = x0.size
    if maxfev <= 0:
        maxfev = 500 * N
    # Run the optimisation, using PyBOBYQA's bounds keyword arguments.
    bounds = (scaled_lb, scaled_ub)
    min_ub = np.min(scaled_ub)
    try:
        pb_sol = pb.solve(cf, x0, args=args,
                          rhobeg=min(MAGIC_TOL * 10, min_ub * 0.499),
                          rhoend=MAGIC_TOL,
                          maxfun=maxfev,
                          bounds=bounds, objfun_has_noise=True,
                          user_params={'restarts.use_restarts': False})
    except CostFunctionError as e:
        # Catch user-thrown errors. Because the BOBYQA optimiser is opaque,
        # there's no way we can return any useful info to the user, so we just
        # convert it into a RuntimeError which will be passed on to the
        # frontend.
        raise RuntimeError(e.message) from None
    # Catch Py-BOBYQA complaints if the optimiser exited with failure.
    if pb_sol.flag in [pb_sol.EXIT_INPUT_ERROR,
                       pb_sol.EXIT_TR_INCREASE_ERROR,
                       pb_sol.EXIT_LINALG_ERROR]:
        raise RuntimeError(pb_sol.msg)
    # If we reached here, it means the optimisation completed successfully.
    # We just need to coerce the returned information into our OptResult
    # format, so that the backend sees a unified interface for all optimisers.
    # Note that niter is not applicable to PyBOBYQA.
    # TODO: Convert PyBOBYQA's messages (success, maxiter, maxfev) back into
    # our standardised messages, so that the frontend can check what happened.
    if pb_sol.flag == pb_sol.EXIT_SUCCESS:
        msg = MESSAGE_OPT_SUCCESS
    elif pb_sol.flag == pb_sol.EXIT_MAXFUN_WARNING:
        msg = MESSAGE_OPT_MAXFEV_REACHED
    elif pb_sol.flag == pb_sol.EXIT_SLOW_WARNING:
        msg = "Optimisation terminated (slow progress)."
    elif pb_sol.flag == pb_sol.EXIT_FALSE_SUCCESS_WARNING:
        msg = "Optimisation terminated (max false good steps)."
    else:
        msg = pb_sol.msg
    return OptResult(xbest=pb_sol.x, fbest=pb_sol.f,
                     niter=0, nfev=pb_sol.nf,
                     message=msg)
