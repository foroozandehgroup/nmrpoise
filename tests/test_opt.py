import numpy as np
import pytest

from nmrpoise.poise_backend.optpoise import (nelder_mead,
                                             multid_search,
                                             pybobyqa_interface)
from nmrpoise.poise_backend.backend import scale, unscale


def rosenbrock(x, arg1=None, arg2=None):
    # Using scipy's definition. We have a couple of dummy arguments because
    # because PyBOBYQA *requires* optimargs and then passes them to the cost
    # function, so rosenbrock() has to accept a couple of extra arguments,
    # even though it doesn't do anything with them.
    return sum(100.0*(x[1:] - x[:-1]**2.0)**2.0 + (1 - x[:-1])**2.0)


def quadratic(x):
    return np.sum(x ** 2)


# This xtol is extremely large, but more closely parallels the
# real-life situations we are likely to face.
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
                                simplex_method="Penguin")
    with pytest.raises(ValueError):
        optResult = nelder_mead(cf=quadratic, x0=x0[:-1], xtol=xtol,
                                simplex_method="Penguin")
    with pytest.raises(ValueError):
        optResult = nelder_mead(cf=quadratic, x0=x0, xtol=np.ones(len(x0)),
                                simplex_method="Penguin")


def test_NM_accuracy():
    for method, nexpt in nm_simplex_methods_nexpts.items():
        optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                simplex_method=method)
        if not np.allclose(optResult.xbest, np.zeros(len(x0)), atol=1e-2):
            optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                    simplex_method=method)
        assert np.allclose(optResult.xbest, np.zeros(len(x0)), atol=1e-2)


def test_NM_iters():
    for method, nexpt in nm_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
                                    simplex_method=method)
            count += optResult.niter
        count /= nexpt
        assert count < 500


def test_NM_fevals():
    for method, nexpt in nm_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            optResult = nelder_mead(cf=quadratic, x0=x0, xtol=xtol,
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
        optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                  simplex_method=method)
        assert np.allclose(optResult.xbest, np.zeros(len(x0)), atol=1e-2)


def test_MDS_iters():
    for method, nexpt in mds_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                      simplex_method=method)
            count += optResult.niter
        count /= nexpt
        assert count < 500


def test_MDS_fevals():
    for method, nexpt in mds_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                      simplex_method=method)
            count += optResult.nfev
        count /= nexpt
        assert count < 1000


def test_maxfevals_reached():
    optResult = multid_search(cf=rosenbrock, x0=x0, xtol=([1e-6] * len(x0)),
                              simplex_method="random")
    assert optResult.message == "Maximum function evaluations reached."
