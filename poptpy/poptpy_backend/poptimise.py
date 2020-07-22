from functools import wraps

import numpy as np


class Simplex():
    """
    Simplex class.
    """
    def __init__(self, x0, method="spendley", length=0.3):
        """
        Initialises a Simplex object.

        Arguments:
            x0     : Initial guess.
            method : Method for construction of initial simplex. Options:
                      - "spendley" : Regular simplex of Spendley et al. (1962)
                                     DOI 10.1080/00401706.1962.10490033.
                                     Default, because it works well.
                      - "axis"     : Simplex extended along each axis by a
                                     fixed length from x0.
                      - "random"   : Every point is randomly generated in [0,1]
            length : A measure of the size of the initial simplex.
        """
        self.x0 = np.ravel(np.asfarray(x0))
        self.N = np.size(self.x0)

        # Generate simplex
        self.x = np.zeros((self.N + 1, self.N))
        self.f = np.zeros(self.N + 1)

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
        Sorts the simplex and associated function values in ascending order
        of the cost function, i.e. sim.x[0] contains the current best point,
        sim.x[N] contains the current worst point.
        """
        indices = np.argsort(self.f)
        self.x = np.take(self.x, indices, 0)
        self.f = np.take(self.f, indices, 0)

    def xbar(self):
        """
        Calculates the centroid. Assumes the function is already sorted.
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
        Performs shrink step (Step 3(f) in Algorithm 8.1.1, Kelley).
        Doesn't evaluate cost functions!
        """
        for i in range(1, self.N + 1):
            self.x[i] = self.x[0] - (self.x[i] - self.x[0])/2


# Custom exceptions.
class MaxFevalsReached(Exception):
    pass


class MaxItersReached(Exception):
    pass


# Function counter decorator. We should probably keep this here and not in
# backend, so that we can reuse code (because of the input() calls to set
# global variables, backend cannot be imported).
def deco_count(fn):
    @wraps(fn)
    def counter(*args, **kwargs):
        counter.calls += 1
        return fn(*args, **kwargs)
    counter.calls = 0
    return counter


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


def nelder_mead(cf, x0, xtol, args=(), plot=False, simplex_method="spendley"):
    """
    Nelder-Mead optimiser, as described in Section 8.1 of Kelley, "Iterative
    Methods for Optimization".

    Inputs to this function should already be scaled to have lower and upper
    bounds of 0 and 1.

    The scipy implementation has a few tricks which are useful in making the
    actual computation run faster. However, here we have opted for readability
    since speed is limited by the acquisition time of the NMR experiment.

    Arguments:
        cf:   The cost function.
        args: A tuple of arguments to pass to the cost function.
        x0:   List containing initial point for optimisation.
        xtol: List containing tolerances for each parameter.
        plot: Bool. If true then this plots the cost function value against
              function evaluation. NOTE: This makes the optimisation run a lot
              more slowly (~ 3 orders of magnitude!!). If this is coupled to
              NMR acquisition, though, this isn't an issue, since we go from
              ~ ms to ~ s.
        simplex_method: Method for generation of initial simplex.

    Returns:
        OptResult object 'o' which contains the following attributes:

        o.xbest (ndarray)   : Optimal values for the optimisation.
        o.fbest (float)     : Cost function at the optimum.
        o.niter (int)       : Number of iterations.
        o.nfev (int)        : Number of function evaluations. Note that in the
                              specific context of NMR optimisation, this is in
                              general not equal to the number of experiments
                              acquired.
        o.simplex (ndarray) : (N+1, N)-sized matrix of the final simplex.
        o.fvals (ndarray)   : List of corresponding cost functions at each
                              point of the simplex.
        o.message (str)     : Message indicating reason for termination.
    """

    # Convert x0 to vector
    x0 = np.asfarray(x0).flatten()
    xtol = np.asfarray(xtol).flatten()
    N = x0.size

    # Default maxiter and maxfev. We could make this customisable in future.
    # For example, we could use TopSpin's `expt' to calculate the duration of
    # one experiment, and then set maxiter to not overshoot a given time.
    maxiter = 200 * N
    maxfev = 500 * N

    # Check length of xtol
    if len(x0) != len(xtol):
        raise ValueError("Nelder-Mead: x0 and xtol have incompatible lengths")
    # Calculate geometric mean of xtol and make sure that it's sensible
    xtol_gm = np.prod(xtol) ** (1 / np.size(xtol))

    # Create and initialise simplex object.
    sim = Simplex(x0, method=simplex_method, length=min(10 * xtol_gm, 0.999))
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

    # Decorate cost function so that it keeps tracks of nfev.
    cf = deco_count(cf)

    # Evaluate the cost function for the initial simplex.
    # Steps 1 and 2 in Algorithm 8.1.1
    for i in range(N + 1):
        sim.f[i] = cf(sim.x[i], *args)
    # Sort simplex
    sim.sort()

    # Plotting initialisation.
    if plot:
        import matplotlib.pyplot as plt
        plot_iters, plot_fvals = [], []

    # Main loop.
    try:
        while not converged(sim, xtol):
            niter += 1
            sim.sort()  # for good measure

            # Plotting
            if plot:
                plot_iters.append(niter)
                plot_fvals.append(sim.f[0])
                plt.cla()
                plt.xlabel("Iteration number")
                plt.ylabel("Cost function")
                plt.plot(plot_iters, plot_fvals)
                plt.pause(0.0001)

            # Check number of iterations
            if niter >= maxiter:
                raise MaxItersReached

            # Step 3(a)
            x_r = xnew(mu_r, sim)  # shorthand for x(mu_r)
            f_r = cf(x_r, *args)

            # Step 3(b): Reflect (+ 3g if needed)
            if cf.calls >= maxfev:
                raise MaxFevalsReached
            if sim.f[0] <= f_r and f_r < sim.f[N - 1]:
                sim.replace_worst(x_r, f_r)
                sim.sort()  # Step 3(g)
                continue

            # Step 3(c): Expand (+ 3g if needed)
            if cf.calls >= maxfev:
                raise MaxFevalsReached
            if f_r < sim.f[0]:
                x_e = xnew(mu_e, sim)
                f_e = cf(x_e, *args)
                if f_e < f_r:
                    sim.replace_worst(x_e, f_e)
                else:
                    sim.replace_worst(x_r, f_r)
                sim.sort()  # Step 3(g)
                continue

            # Step 3(d): Outside contraction (+ 3f and 3g if needed)
            if cf.calls >= maxfev:
                raise MaxFevalsReached
            if sim.f[N - 1] <= f_r and f_r < sim.f[N]:
                x_oc = xnew(mu_oc, sim)
                f_c = cf(x_oc, *args)
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
            if cf.calls >= maxfev:
                raise MaxFevalsReached
            if f_r >= sim.f[N]:
                x_ic = xnew(mu_ic, sim)
                f_c = cf(x_ic, *args)
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
        message = "Maximum iterations reached."
    except MaxFevalsReached:
        message = "Maximum function evaluations reached."
    else:
        message = "Optimisation terminated successfully."

    # sort the simplex in ascending order of fvals
    sim.sort()

    return OptResult(xbest=sim.x[0], fbest=sim.f[0],
                     niter=niter, nfev=cf.calls,
                     simplex=sim.x, fvals=sim.f,
                     message=message)


def multid_search(cf, x0, xtol, args=(), plot=False,
                  simplex_method="spendley"):
    """
    Multidimensional search optimiser, as described in Secion 8.2 of Kelley,
    "Iterative Methods for Optimization".

    Inputs to this function should already be scaled to have lower and upper
    bounds of 0 and 1.

    Arguments:
        cf:   The cost function.
        args: A tuple of arguments to pass to the cost function.
        x0:   List containing initial point for optimisation.
        xtol: List containing tolerances for each parameter.
        plot: Bool. If true then this plots the cost function value against
              function evaluation. NOTE: This makes the optimisation run a lot
              more slowly (~ 3 orders of magnitude!!). If this is coupled to
              NMR acquisition, though, this isn't an issue, since we go from
              ~ ms to ~ s.
        simplex_method: Method for generation of initial simplex.

    Returns:
        OptResult object 'o' which contains the following attributes:

        o.xbest (ndarray)   : Optimal values for the optimisation.
        o.fbest (float)     : Cost function at the optimum.
        o.niter (int)       : Number of iterations.
        o.nfev (int)        : Number of function evaluations. Note that in the
                              specific context of NMR optimisation, this is in
                              general not equal to the number of experiments
                              acquired.
        o.simplex (ndarray) : (N+1, N)-sized matrix of the final simplex.
        o.fvals (ndarray)   : List of corresponding cost functions at each
                              point of the simplex.
        o.message (str)     : Message indicating reason for termination.
    """
    # Convert x0 to vector
    x0 = np.asfarray(x0).flatten()
    xtol = np.asfarray(xtol).flatten()
    N = x0.size

    # Default maxiter and maxfev. We could make this customisable in future.
    # For example, we could use TopSpin's `expt' to calculate the duration of
    # one experiment, and then set maxiter to not overshoot a given time.
    maxiter = 200 * N
    maxfev = 500 * N

    # Check length of xtol
    if len(x0) != len(xtol):
        raise ValueError("Multidimensional search: x0 and xtol have "
                         "incompatible lengths")
    # Calculate geometric mean of xtol and make sure that it's sensible
    xtol_gm = np.prod(xtol) ** (1 / np.size(xtol))

    # Create and initialise simplex object.
    sim = Simplex(x0, method=simplex_method, length=min(10 * xtol_gm, 0.999))
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

    # Decorate cost function so that it keeps tracks of nfev.
    cf = deco_count(cf)

    # Evaluate the cost function for the initial simplex.
    # Steps 1 and 2 in Algorithm 8.2.1
    for i in range(N + 1):
        sim.f[i] = cf(sim.x[i], *args)
    # Sort simplex
    sim.sort()

    # Plotting initialisation.
    if plot:
        import matplotlib.pyplot as plt
        plot_iters, plot_fvals = [], []

    # Main loop.
    try:
        while not converged(sim, xtol):
            niter += 1
            sim.sort()  # for good measure

            # Plotting
            if plot:
                plot_iters.append(niter)
                plot_fvals.append(sim.f[0])
                plt.cla()
                plt.xlabel("Iteration number")
                plt.ylabel("Cost function")
                plt.plot(plot_iters[-100:], plot_fvals[-100:])
                plt.pause(0.0001)

            # Check number of iterations and function evaluations
            if niter >= maxiter:
                raise MaxItersReached
            if cf.calls >= maxfev:
                raise MaxFevalsReached

            # Step 3(a): Reflect
            r_j = np.zeros((N, N))
            f_r_j = np.zeros(N)
            for j in range(1, N + 1):
                r_j[j - 1] = sim.x[0] - (sim.x[j] - sim.x[0])
                f_r_j[j - 1] = cf(r_j[j - 1], *args)

            # Step 3(b): Expand
            if sim.f[0] > np.amin(f_r_j):
                e_j = np.zeros((N, N))
                f_e_j = np.zeros(N)
                for j in range(1, N + 1):
                    e_j[j - 1] = sim.x[0] - mu_e * (sim.x[j] - sim.x[0])
                    f_e_j[j - 1] = cf(e_j[j - 1], *args)
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
                    sim.f[j] = cf(sim.x[j], *args)
                sim.sort()  # Step 3(d)
                continue
    except MaxItersReached:
        message = "Maximum iterations reached."
    except MaxFevalsReached:
        message = "Maximum function evaluations reached."
    else:
        message = "Optimisation terminated successfully."

    # sort the simplex in ascending order of fvals
    sim.sort()

    return OptResult(xbest=sim.x[0], fbest=sim.f[0],
                     niter=niter, nfev=cf.calls,
                     simplex=sim.x, fvals=sim.f,
                     message=message)


def pybobyqa_interface(cf, x0, xtol, args=(), plot=False):
    # This should be optional, i.e. we shouldn't force people to install it.
    try:
        import pybobyqa as pb
    except ImportError:
        # Give a nice useful message.
        raise ImportError("The Py-BOBYQA package and/or its dependencies "
                          "have not been installed. Please install them "
                          "before using the Py-BOBYQA optimiser.")
    x0 = np.asfarray(x0).flatten()
    # Instead of returning np.inf when x is out of bounds, we'll use
    # PyBOBYQA's bounds argument. But first we need to calculate the bounds.
    # The unscaled bounds are attributes of the Routine object which is the
    # second element of args.
    r = args[1]
    lb, ub, tol = (np.array(i) for i in (r.lb, r.ub, r.tol))
    scaled_lb = (lb - lb) * 0.03 / tol
    scaled_ub = (ub - lb) * 0.03 / tol
    # Run the optimisation.
    pb_sol = pb.solve(cf, x0, args=args,
                      rhobeg=min(0.3, max(scaled_ub) * 0.499), rhoend=0.03,
                      bounds=(scaled_lb, scaled_ub), objfun_has_noise=True,
                      user_params={'restarts.use_restarts': False})
    # Catch Py-BOBYQA complaints.
    if pb_sol.flag in [pb_sol.EXIT_INPUT_ERROR,
                       pb_sol.EXIT_TR_INCREASE_ERROR,
                       pb_sol.EXIT_LINALG_ERROR]:
        raise RuntimeError(pb_sol.msg)
    # We just need to coerce the returned information into our OptResult
    # format, so that the backend sees a unified interface for all optimisers.
    # Note that niter is not applicable to PyBOBYQA.
    return OptResult(xbest=pb_sol.x, fbest=pb_sol.f,
                     niter=0, nfev=pb_sol.nf,
                     message=pb_sol.msg)
