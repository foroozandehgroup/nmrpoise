import numpy as np
import pytest

from nmrpoise.poise_backend.optpoise import (nelder_mead,
                                             multid_search,
                                             pybobyqa_interface,
                                             deco_count,
                                             scale,
                                             unscale,
                                             MESSAGE_OPT_SUCCESS,
                                             MESSAGE_OPT_MAXFEV_REACHED,
                                             MESSAGE_OPT_MAXITER_REACHED)
from nmrpoise.poise_backend.cfhelpers import CostFunctionError


RNG_SEED = 5


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


@deco_count
def quadratic_with_error(x):
    """
    This is the same as quadratic() but raises an error when the cost function
    gets close to 0. We just use it to test what happens.
    """
    cf_val = np.sum(x ** 2)
    if cf_val < 0.3:
        raise CostFunctionError("Cost function is below 0.3")
    else:
        return cf_val


# This xtol is extremely large, but more closely parallels the
# real-life situations we are likely to face.
lb = np.array([-5, -5, -5, -5, -5])
ub = np.array([5, 5, 5, 5, 5])
x0 = np.array([1.3, 0.7, 0.8, 1.9, 1.2])
xtol = np.array([1e-2] * len(x0))


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
    for method in ["spendley", "axis", "random"]:
        quadratic.calls = 0  # reset fevals
        optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                scaled_lb=lb, scaled_ub=ub,
                                simplex_method=method, seed=RNG_SEED)
        assert np.allclose(optResult.xbest, np.zeros(len(x0)), atol=2e-2)


def test_NM_niters_fevals():
    for method in ["spendley", "axis", "random"]:
        quadratic.calls = 0  # reset fevals
        optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                scaled_lb=lb, scaled_ub=ub,
                                simplex_method=method, seed=RNG_SEED)
        # Check optResult.__repr__() while we're at it.
        assert all(s in repr(optResult) for s in ["xbest", "fbest",
                                                  "niter", "nfev",
                                                  "fvals", "simplex"])
        assert optResult.niter < 500
        assert optResult.nfev < 850


def test_MDS_accuracy():
    for method in ["spendley", "axis"]:
        quadratic.calls = 0  # reset fevals
        optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                  scaled_lb=lb, scaled_ub=ub,
                                  simplex_method=method,
                                  seed=RNG_SEED)
        assert np.allclose(optResult.xbest, np.zeros(len(x0)), atol=2e-2)


def test_MDS_iters_fevals():
    for method in ["spendley", "axis"]:
        quadratic.calls = 0  # reset fevals
        optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                  scaled_lb=lb, scaled_ub=ub,
                                  simplex_method=method, seed=RNG_SEED)
        assert optResult.niter < 500
        assert optResult.nfev < 1000


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
    MAXFEV = 10

    quadratic.calls = 0
    optResult = nelder_mead(cf=quadratic, x0=x0, xtol=([1e-6] * len(x0)),
                            scaled_lb=lb, scaled_ub=ub, maxfev=MAXFEV)
    assert optResult.message == MESSAGE_OPT_MAXFEV_REACHED
    assert optResult.nfev == MAXFEV

    quadratic.calls = 0
    optResult = multid_search(cf=quadratic, x0=x0, xtol=([1e-6] * len(x0)),
                              scaled_lb=lb, scaled_ub=ub, maxfev=MAXFEV)
    assert optResult.message == MESSAGE_OPT_MAXFEV_REACHED
    assert optResult.nfev == MAXFEV


def test_CostFunctionError():
    for method in ["spendley", "axis", "random"]:
        quadratic_with_error.calls = 0  # reset fevals
        optResult = nelder_mead(cf=quadratic_with_error, x0=x0, xtol=xtol,
                                scaled_lb=lb, scaled_ub=ub,
                                simplex_method=method, seed=RNG_SEED)
        assert "Cost function is below 0.3" in optResult.message
        assert optResult.fbest >= 0.3
    for method in ["spendley", "axis", "random"]:
        quadratic_with_error.calls = 0  # reset fevals
        optResult = multid_search(cf=quadratic_with_error, x0=x0, xtol=xtol,
                                  scaled_lb=lb, scaled_ub=ub,
                                  simplex_method=method, seed=RNG_SEED)
        assert "Cost function is below 0.3" in optResult.message
        assert optResult.fbest >= 0.3
