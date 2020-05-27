import numpy as np
from scipy.optimize import rosen

from poptpy.poptpy_backend.poptimise import nelder_mead


x0 = np.array([1.3, 0.7, 0.8, 1.9, 1.2])
xtol = np.array([1e-6] * len(x0))
optResult = nelder_mead(cf=rosen, x0=x0, xtol=xtol,
                        simplex_method="spendley")


def testNMAccuracy():
    assert np.all(np.isclose(optResult.xbest, np.ones(len(x0)), atol=1e-6))

def testNMIters():
    # very lax, but depending on the simplex method this is necessary
    assert optResult.niter < 450

def testNMFevals():
    assert optResult.nfev < 750
