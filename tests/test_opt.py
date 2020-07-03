import numpy as np
import pytest

from poptpy.poptpy_backend.poptimise import (nelder_mead,
                                             multid_search,
                                             pybobyqa_interface)
from poptpy.poptpy_backend.backend import scale, unscale


def rosenbrock(x, arg1=None, arg2=None):
    # Using scipy's definition. We have a couple of dummy arguments because
    # because PyBOBYQA *requires* optimargs and then passes them to the cost
    # function, so rosenbrock() has to accept a couple of extra arguments,
    # even though it doesn't do anything with them.
    return sum(100.0*(x[1:] - x[:-1]**2.0)**2.0 + (1 - x[:-1])**2.0)


x0 = np.array([1.3, 0.7, 0.8, 1.9, 1.2])
xtol = np.array([1e-6] * len(x0))
nm_simplex_methods_nexpts = {
    "spendley": 1,
    "axis": 1,
    "random": 20,
}


def test_errors():
    with pytest.raises(ValueError):
        optResult = nelder_mead(cf=rosenbrock, x0=x0, xtol=xtol,
                                simplex_method="Penguin")
    with pytest.raises(ValueError):
        optResult = nelder_mead(cf=rosenbrock, x0=x0[:-1], xtol=xtol,
                                simplex_method="Penguin")
    with pytest.raises(ValueError):
        optResult = nelder_mead(cf=rosenbrock, x0=x0, xtol=np.ones(len(x0)),
                                simplex_method="Penguin")


def test_NM_accuracy():
    # There is an annoying issue where sometimes NM converges to the local
    # minimum where some parameter x_i is -1 instead of 1. In order to get
    # around this we allow it to not work once. It appears highly unlikely
    # that it will converge to the local minimum twice out of two runs.
    for method, nexpt in nm_simplex_methods_nexpts.items():
        optResult = nelder_mead(cf=rosenbrock, x0=x0, xtol=xtol,
                                simplex_method=method)
        if not np.allclose(optResult.xbest, np.ones(len(x0)), atol=1e-6):
            optResult = nelder_mead(cf=rosenbrock, x0=x0, xtol=xtol,
                                    simplex_method=method)
        assert np.allclose(optResult.xbest, np.ones(len(x0)), atol=1e-6)


def test_NM_iters():
    for method, nexpt in nm_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            optResult = nelder_mead(cf=rosenbrock, x0=x0, xtol=xtol,
                                    simplex_method=method)
            count += optResult.niter
        count /= nexpt
        assert count < 500


def test_NM_fevals():
    for method, nexpt in nm_simplex_methods_nexpts.items():
        count = 0
        for i in range(nexpt):
            optResult = nelder_mead(cf=rosenbrock, x0=x0, xtol=xtol,
                                    simplex_method=method)
            count += optResult.nfev
        count /= nexpt
        assert count < 850


# MDS is very difficult to test with Rosenbrock because it converges awfully
# slowly. See: Torczon (1989). https://scholarship.rice.edu/handle/1911/16304

def quadratic(x):
    return np.sum(x ** 2)


mds_simplex_methods_nexpts = {
    "spendley": 1,
    "axis": 1,
}


def test_MDS_accuracy():
    for method, nexpt in mds_simplex_methods_nexpts.items():
        optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                  simplex_method=method)
        assert np.allclose(optResult.xbest, np.zeros(len(x0)), atol=1e-6)


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
    optResult = multid_search(cf=rosenbrock, x0=x0, xtol=xtol,
                              simplex_method="random")
    assert optResult.message == "Maximum function evaluations reached."
