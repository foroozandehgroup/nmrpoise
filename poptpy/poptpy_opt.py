from functools import wraps

import numpy as np


# Function counter decorator. We should probably keep this here and not in
# poptpy_be, so that we can reuse code (because of the input() calls to set
# global variables, poptpy_be cannot be imported).
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


def nelder_mead(cf, x0, xtol, args=(), plot=False):
    """
    Nelder-Mead optimiser.

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
        o.fvals (ndarray)   : List of corresponding cost functions at each point
                              of the simplex.
    """

    # Convert x0 to vector
    x0 = np.asfarray(x0).flatten()
    xtol = np.asfarray(xtol).flatten()
    N = x0.size

    # Default maxiter and maxfev. We could make this customisable in future.
    # For example, we could use TopSpin's `expt' to calculate the duration of
    # one experiment, and then set maxiter to not overshoot a given time.
    maxiter = 200*N
    maxfev = 500*N

    # Check length of xtol
    if len(x0) != len(xtol):
        raise ValueError("Nelder-Mead: x0 and xtol have incompatible lengths")
    # Calculate geometric mean of xtol and make sure that it's sensible
    xtol_gm = np.prod(xtol) ** (1 / np.size(xtol))
    if xtol_gm > 0.35:
        raise ValueError("Nelder-Mead: xtol is too large. "
                         "Please reduce the tolerances.")

    # Set up the initial simplex.
    sim = np.zeros((N + 1, N))
    sim[0] = x0
    for k in range(N):
        # Each point x_i (\neq x_0) is equal to x_0 \pm [0.2, 0.4).
        # However, we also need to make sure that each point is sufficiently
        # "far away" from x0, so that the optimisation doesn't just converge
        # immediately. We do this by making sure that the distance between the
        # two points is at least xtol_gm.
        y = x0.copy()
        while np.linalg.norm(y - x0) < xtol_gm:
            y = x0.copy() + ((np.random.rand(N)*0.2 + 0.2) *
                             np.sign(np.random.randn(N)))
        sim[k + 1] = y

    # Number of iterations. Function evaluations are stored as cf.calls.
    niter = 0

    # Array to store results of function evaluation.
    fvals = np.zeros(N + 1)

    # Set up parameters for Nelder-Mead.
    # Notation follows that used in Section 8.1 of  Kelley, 'Iterative Methods
    # for Optimization'.
    mu_ic = -0.5   # Inside contraction parameter
    mu_oc = 0.5    # Outside contraction parameter
    mu_r = 1       # Reflect parameter
    mu_e = 2       # Expansion parameter

    # Helper functions.
    def xnew(mu, sim):
        """
        Function which calculates the new point to place in the simplex.
        Eq 8.2 (Kelley).
        'sim' must already be sorted in ascending order of fval..
        """
        xbar = np.average(sim[0:N], axis=0)   # Centroid.
        xworst = sim[N]   # Worst point. Note N not N+1 because zero-indexing.
        return ((1 + mu) * xbar) - (mu * xworst)

    def sort_simplex(sim, fvals):
        """
        Sorts the simplex and associated function values in ascending order
        of the cost function, i.e. sim[0] contains the current best point,
        sim[N] contains the current worst point.
        """
        indices = np.argsort(fvals)
        sim = np.take(sim, indices, 0)
        fvals = np.take(fvals, indices, 0)
        return sim, fvals

    def shrink(sim, fvals):
        """
        Performs shrink step (Step 3(f) in Algorithm 8.1.1, Kelley).
        Doesn't sort the simplex after it's done.
        """
        for i in range(1, N + 1):
            sim[i] = sim[0] - (sim[i] - sim[0])/2
            fvals[i] = cf(sim[i], *args)
        return sim, fvals

    def converged(sim, xtol):
        """
        Convergence criteria. To be converged, each dimension of the simplex
        must have a range smaller than or equal to the corresponding xtol in
        that dimension.
        """
        simplex_range = np.amax(sim, axis=0) - np.amin(sim, axis=0)
        return all(np.less_equal(simplex_range, xtol))
        ## Scipy convergence criteria. Assumes that the simplex is already
        ## sorted. It is slightly looser (i.e. will converge before mine),
        ## but hardly makes a difference to the average fevals (tested on
        ## Rosenbrock function).
        # return np.max(np.ravel(np.abs(sim[1:] - sim[0]))) <= xtol[0]

    # Decorate cost function so that it keeps tracks of nfev.
    cf = deco_count(cf)

    # Evaluate the cost function for the initial simplex.
    # Steps 1 and 2 in Algorithm 8.1.1
    for i in range(N + 1):
        fvals[i] = cf(sim[i], *args)
    # Sort simplex
    sim, fvals = sort_simplex(sim, fvals)

    # Plotting initialisation.
    if plot:
        import matplotlib.pyplot as plt
        plot_iters, plot_fvals = [], []

    # Main loop.
    while not converged(sim, xtol):
        niter += 1

        # Plotting
        if plot:
            plot_iters.append(niter)
            plot_fvals.append(fvals[0])
            plt.cla()
            plt.xlabel("Iteration number")
            plt.ylabel("Cost function")
            plt.plot(plot_iters, plot_fvals)
            plt.pause(0.0001)

        # Check number of iterations
        if niter >= maxiter:
            break

        # Step 3(a)
        f_r = cf(xnew(mu_r, sim), *args)

        # Step 3(b): Reflect (+ 3g if needed)
        if cf.calls >= maxfev:
            break
        if fvals[0] <= f_r and f_r < fvals[N - 1]:
            sim[N] = xnew(mu_r, sim)
            fvals[N] = f_r
            sim, fvals = sort_simplex(sim, fvals)  # Step 3(g)
            continue

        # Step 3(c): Expand (+ 3g if needed)
        if cf.calls >= maxfev:
            break
        if f_r < fvals[0]:
            f_e = cf(xnew(mu_e, sim), *args)
            if f_e < f_r:
                sim[N] = xnew(mu_e, sim)
                fvals[N] = f_e
            else:
                sim[N] = xnew(mu_r, sim)
                fvals[N] = f_r
            sim, fvals = sort_simplex(sim, fvals)  # Step 3(g)
            continue

        # Step 3(d): Outside contraction (+ 3f and 3g if needed)
        if cf.calls >= maxfev:
            break
        if fvals[N - 1] <= f_r and f_r < fvals[N]:
            f_c = cf(xnew(mu_oc, sim), *args)
            if f_c <= f_r:
                sim[N] = xnew(mu_oc, sim)
                fvals[N] = f_c
                sim, fvals = sort_simplex(sim, fvals)  # Step 3(g)
                continue
            else:
                if cf.calls >= maxfev - N:             # Step 3(f)
                    break
                sim, fvals = shrink(sim, fvals)
                sim, fvals = sort_simplex(sim, fvals)  # Step 3(g)
                continue

        # Step 3(e): Inside contraction (+ 3f and 3g if needed)
        if cf.calls >= maxfev:
            break
        if f_r >= fvals[N]:
            f_c = cf(xnew(mu_ic, sim), *args)
            if f_c < fvals[N]:
                sim[N] = xnew(mu_ic, sim)
                fvals[N] = f_c
                sim, fvals = sort_simplex(sim, fvals)  # Step 3(g)
                continue
            else:
                if cf.calls >= maxfev - N:             # Step 3(f)
                    break
                sim, fvals = shrink(sim, fvals)
                sim, fvals = sort_simplex(sim, fvals)  # Step 3(g)
                continue
    # END while loop

    # sort the simplex in ascending order of fvals
    sim, fvals = sort_simplex(sim, fvals)

    return OptResult(xbest=sim[0], fbest=fvals[0],
                     niter=niter, nfev=cf.calls,
                     simplex=sim, fvals=fvals)
