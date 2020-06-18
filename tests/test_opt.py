import numpy as np
import pytest

from poptpy.poptpy_backend.poptimise import nelder_mead, multid_search


def rosenbrock(x):
    # Using scipy's definition.
    return sum(100.0*(x[1:] - x[:-1]**2.0)**2.0 + (1 - x[:-1])**2.0)


x0 = np.array([1.3, 0.7, 0.8, 1.9, 1.2])
xtol = np.array([1e-6] * len(x0))
simplex_method = "spendley"
nexpt = 1 if simplex_method in ["spendley", "axis"] else 50


def test_NM_accuracy():
    optResult = nelder_mead(cf=rosenbrock, x0=x0, xtol=xtol,
                            simplex_method=simplex_method)
    assert np.all(np.isclose(optResult.xbest, np.ones(len(x0)), atol=1e-6))


def test_NM_iters():
    count = 0
    for i in range(nexpt):
        optResult = nelder_mead(cf=rosenbrock, x0=x0, xtol=xtol,
                                simplex_method=simplex_method)
        count += optResult.niter
    count /= nexpt
    assert count < 450


def test_NM_fevals():
    count = 0
    for i in range(nexpt):
        optResult = nelder_mead(cf=rosenbrock, x0=x0, xtol=xtol,
                                simplex_method=simplex_method)
        count += optResult.nfev
    count /= nexpt
    assert count < 750


# MDS is very difficult to test with Rosenbrock because it converges awfully
# slowly. See: Torczon (1989). https://scholarship.rice.edu/handle/1911/16304

def quadratic(x):
    return np.sum(x ** 2)


def test_MDS_accuracy():
    optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                              simplex_method=simplex_method)
    assert np.all(np.isclose(optResult.xbest, np.zeros(len(x0)), atol=1e-6))


def test_MDS_iters():
    count = 0
    for i in range(nexpt):
        optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                  simplex_method=simplex_method)
        count += optResult.niter
    count /= nexpt
    assert count < 500


def test_MDS_fevals():
    count = 0
    for i in range(nexpt):
        optResult = multid_search(cf=quadratic, x0=x0, xtol=xtol,
                                  simplex_method=simplex_method)
        count += optResult.nfev
    count /= nexpt
    assert count < 1000
