import numpy as np
import pytest

from poptpy.poptpy_backend.poptimise import nelder_mead, multid_search


def rosenbrock(x):
    # Using scipy's definition.
    return sum(100.0*(x[1:] - x[:-1]**2.0)**2.0 + (1 - x[:-1])**2.0)


x0 = np.array([1.3, 0.7, 0.8, 1.9, 1.2])
xtol = np.array([1e-6] * len(x0))
nm_simplex_methods_nexpts = {
    "spendley": 1,
    "axis": 1,
    "random": 20,   # We don't test these. Sometimes they converge to a false
    # "jon": 20,      # minimum with x0 = -1... This should be documented
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
    for method, nexpt in nm_simplex_methods_nexpts.items():
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
        assert count < 800


# MDS is very difficult to test with Rosenbrock because it converges awfully
# slowly. See: Torczon (1989). https://scholarship.rice.edu/handle/1911/16304

def quadratic(x):
    return np.sum(x ** 2)


mds_simplex_methods_nexpts = {
    "spendley": 1,
    "axis": 1,
    # "random": 20,
    # "jon": 20,
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
