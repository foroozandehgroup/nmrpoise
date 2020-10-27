import numpy as np
import pytest

from nmrpoise.poise_backend.optpoise import (nelder_mead,
                                             multid_search,
                                             pybobyqa_interface,
                                             deco_count,
                                             scale,
                                             unscale)


def test_scale_unscale():
    # Scale by bounds.
    rng = np.random.default_rng()
    # Generate and sort a random 3x20 matrix.
    mat = rng.uniform(low=-500, high=500, size=(3, 20))
    mat.sort(axis=0)
    lb, val, ub = mat[0], mat[1], mat[2]
    # Generate random percentage tolerances.
    tol = rng.uniform(low=0.01, high=0.5, size=(1, 20))
    # Convert to actual tolerances.
    tol = tol * (ub - lb)
    # Scale.
    sval, slb, sub, stol = scale(val, lb, ub, tol)
    # Make sure that lb's and ub's are zeros and ones.
    assert np.allclose(slb, np.zeros(np.shape(val)))
    assert np.allclose(sub, np.ones(np.shape(val)))
    # Make sure that unscaling gives the right things.
    usval = unscale(sval, lb, ub, tol)
    assert np.allclose(usval, val)

    # Scale by tols.
    # Generate and sort a random 3x20 matrix.
    mat = rng.uniform(low=-500, high=500, size=(3, 20))
    mat.sort(axis=0)
    lb, val, ub = mat[0], mat[1], mat[2]
    # Generate random percentage tolerances.
    tol = rng.uniform(low=0.01, high=0.5, size=(1, 20))
    # Convert to actual tolerances.
    tol = tol * (ub - lb)
    # Scale by tolerances.
    sval, slb, sub, stol = scale(val, lb, ub, tol, scaleby="tols")
    # Make sure that lb's and tol's are 0's and 0.03's.
    assert np.allclose(slb, np.zeros(np.shape(val)))
    assert np.allclose(stol, 0.03 * np.ones(np.shape(val)))
    # Check that unscaling gives back the same values.
    usval = unscale(sval, lb, ub, tol, scaleby="tols")
    assert np.allclose(usval, val)

    # Check other scaleby values for scale and unscale
    with pytest.raises(ValueError, match="Invalid argument"):
        _, _, _, _ = scale(val, lb, ub, tol, scaleby="penguins")
    with pytest.raises(ValueError, match="Invalid argument"):
        _ = unscale(sval, lb, ub, tol, scaleby="penguins")

    # Check out of bounds values
    # Generate and sort a random 3x20 matrix.
    mat = rng.uniform(low=-500, high=500, size=(3, 20))
    mat.sort(axis=0)
    lb, val, ub = mat[1], mat[0], mat[2]  # note how this is out of order
    assert scale(val, lb, ub, tol, scaleby="bounds") is None
    lb, val, ub = mat[0], mat[2], mat[1]  # note how this is out of order
    assert scale(val, lb, ub, tol, scaleby="bounds") is None


def test_deco_count():
    @deco_count
    def peep():
        print("PEEP")

    n = 10
    for i in range(n):
        peep()
    assert peep.calls == n


@deco_count
def rosenbrock(x, arg1=None, arg2=None):
    # Using scipy's definition. We have a couple of dummy arguments because
    # because PyBOBYQA *requires* optimargs and then passes them to the cost
    # function, so rosenbrock() has to accept a couple of extra arguments,
    # even though it doesn't do anything with them.
    return sum(100.0*(x[1:] - x[:-1]**2.0)**2.0 + (1 - x[:-1])**2.0)


@deco_count
def quadratic(x):
    return np.sum(x ** 2)


# This xtol is extremely large, but more closely parallels the
# real-life situations we are likely to face.
lb = np.array([-5, -5, -5, -5, -5])
ub = np.array([5, 5, 5, 5, 5])
x0 = np.array([1.3, 0.7, 0.8, 1.9, 1.2])
xtol = np.array([1e-2] * len(x0))
nm_simplex_methods_nexpts = {
    "spendley": 1,
    "axis": 1,
    "random": 20,
}


def test_errors():
    with pytest.raises(ValueError):
        optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                scaled_lb=lb, scaled_ub=ub,
                                simplex_method="Penguin")
    with pytest.raises(ValueError):
        optResult = nelder_mead(cf=quadratic, x0=x0[:-1], xtol=xtol,
                                scaled_lb=lb, scaled_ub=ub,
                                simplex_method="Penguin")
    with pytest.raises(ValueError):
        optResult = nelder_mead(cf=quadratic, x0=x0, xtol=np.ones(len(x0)),
                                scaled_lb=lb, scaled_ub=ub,
                                simplex_method="Penguin")


def test_NM_accuracy():
    for method, nexpt in nm_simplex_methods_nexpts.items():
        quadratic.calls = 0  # reset fevals
        optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                scaled_lb=lb, scaled_ub=ub,
                                simplex_method=method)
        if not np.allclose(optResult.xbest, np.zeros(len(x0)), atol=2e-2):
            quadratic.calls = 0  # reset fevals
            optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                    scaled_lb=lb, scaled_ub=ub,
                                    simplex_method=method)
        assert np.allclose(optResult.xbest, np.zeros(len(x0)), atol=2e-2)


def test_NM_iters():
    for method, nexpt in nm_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            quadratic.calls = 0  # reset fevals
            optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                    scaled_lb=lb, scaled_ub=ub,
                                    simplex_method=method)
            # Check optResult.__repr__() while we're at it.
            assert all(s in repr(optResult) for s in ["xbest", "fbest",
                                                      "niter", "nfev",
                                                      "fvals", "simplex"])
            count += optResult.niter
        count /= nexpt
        assert count < 500


def test_NM_fevals():
    for method, nexpt in nm_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            quadratic.calls = 0  # reset fevals
            optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                    scaled_lb=lb, scaled_ub=ub,
                                    simplex_method=method)
            count += optResult.nfev
        count /= nexpt
        assert count < 850


mds_simplex_methods_nexpts = {
    "spendley": 1,
    "axis": 1,
}


def test_MDS_accuracy():
    for method, nexpt in mds_simplex_methods_nexpts.items():
        quadratic.calls = 0  # reset fevals
        optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                  scaled_lb=lb, scaled_ub=ub,
                                  simplex_method=method)
        assert np.allclose(optResult.xbest, np.zeros(len(x0)), atol=2e-2)


def test_MDS_iters():
    for method, nexpt in mds_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            quadratic.calls = 0  # reset fevals
            optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                      scaled_lb=lb, scaled_ub=ub,
                                      simplex_method=method)
            count += optResult.niter
        count /= nexpt
        assert count < 500


def test_MDS_fevals():
    for method, nexpt in mds_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            quadratic.calls = 0  # reset fevals
            optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                      scaled_lb=lb, scaled_ub=ub,
                                      simplex_method=method)
            count += optResult.nfev
        count /= nexpt
        assert count < 1000


def test_bobyqa_accuracy():
    quadratic.calls = 0  # reset fevals
    sval, slb, sub, stol = scale(x0, lb, ub, xtol, scaleby="tols")
    sbest, _, _, _ = scale(np.zeros(len(x0)), lb, ub, xtol, scaleby="tols")

    def scaled_quadratic(x):
        return np.sum((x - sbest) ** 2)

    optResult = pybobyqa_interface(cf=scaled_quadratic, x0=sval, xtol=stol,
                                   scaled_lb=slb, scaled_ub=sub)
    unscaled_xbest = unscale(optResult.xbest, lb, ub, xtol, scaleby="tols")
    assert np.allclose(unscaled_xbest, np.zeros(len(x0)), atol=2e-2)


def test_maxfevals_reached():
    optResult = nelder_mead(cf=quadratic, x0=x0, xtol=([1e-6] * len(x0)),
                            scaled_lb=lb, scaled_ub=ub, maxfev=10)
    assert optResult.message == "Maximum function evaluations reached."
    optResult = multid_search(cf=quadratic, x0=x0, xtol=([1e-6] * len(x0)),
                              scaled_lb=lb, scaled_ub=ub, maxfev=10)
    assert optResult.message == "Maximum function evaluations reached."
