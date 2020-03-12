import numpy as np

def minimize_nm(func, x0, args=(), xtol=None, ftol=None,
                maxiter=None, maxfev=None):
    """
    Nelder-Mead minimiser.

    x0 must be a numpy ndarray.
    """

    # Convert x0 to vector
    x0 = np.asfarray(x0).flatten()
    N = x0.size

    if maxiter is None:
        maxiter = 200*N
    if maxfev is None:
        maxfev = 500*N

    # Set up the simplex
    # Each point x_i (\neq x_0) is equal to x_0 \pm [0.2, 0.4)
    sim = np.zeros((N + 1, N))
    sim[0] = x0
    for k in range(N):
        sim[k + 1] = x0 + (np.random.rand(N)*0.2 + 0.2)*np.sign(np.random.randn(N))

    # Wrapper for cost function evaluation
