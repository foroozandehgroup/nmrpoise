import time

from scipy import optimize
import numpy as np
from tqdm import tqdm

import poptpy_opt

# Test optimisation on Rosenbrock function.
cf = optimize.rosen
x0 = np.array([1.3, 0.7, 0.8, 1.9, 1.2])
N = len(x0)
xtol = 1e-6

##########################
# Test accuracy of result.
##########################

# x = time.time()
# scipyRes = optimize.minimize(cf, x0, method='Nelder-Mead', options={'xatol':1e-6, 'fatol':np.inf})
# y = time.time()
# print("time  : ", "{:.4f} seconds".format(y - x))
# print("x     : ", scipyRes.x)
# print("nfev  : ", scipyRes.nfev)
# print("nit   : ", scipyRes.nit)
# print("fun   : ", scipyRes.fun)
# print("fvals : ", scipyRes.final_simplex[1])
# print()
# print("======================================")
# print()
# xtol = [1e-6] * len(x0)
# x = time.time()
# myRes = poptpy_opt.nelder_mead(cf, x0, xtol, plot=False)
# y = time.time()
# print("time  : ", "{:.4f} seconds".format(y - x))
# print("x     : ", myRes.xbest)
# print("nfev  : ", myRes.nfev)
# print("nit   : ", myRes.niter)
# print("fun   : ", myRes.fbest)
# print("fvals : ", myRes.fvals)


#####################################################
# Test average nfev and niter, i.e. convergence rate.
#####################################################

nexpts = 1000
nfevs = {}
nits = {}
for m in ["spendley", "axis", "random", "jon"]:
    nfevs[m] = []
    nits[m] = []

for i in tqdm(range(nexpts)):
    # ## Can use this code to feed our simplex generation mechanism into Scipy's optimiser.
    # sim = np.zeros((N + 1, N))
    # sim[0] = x0
    # for k in range(N):
    #     y = x0.copy()
    #     while np.linalg.norm(y - x0) < xtol:
    #         y = x0.copy() + ((np.random.rand(N)*0.2 + 0.2) *
    #                          np.sign(np.random.randn(N)))
    #     sim[k + 1] = y
    # scipyRes = optimize.minimize(cf, x0, method='Nelder-Mead', options={'xatol':xtol, 'fatol':np.inf, 'initial_simplex':sim})

    ## Otherwise, this is the original Scipy optimiser.
    # scipyRes = optimize.minimize(cf, x0, method='Nelder-Mead', options={'xatol':xtol, 'fatol':np.inf}

    ## This is my optimiser.
    for m in ["spendley", "axis", "random", "jon"]:
        nfevs[m].append(poptpy_opt.nelder_mead(cf, x0, [xtol] * N, simplex=m).nfev)
        nits[m].append(poptpy_opt.nelder_mead(cf, x0, [xtol] * N, simplex=m).niter)

    ## Append results.
    # nfev_scipy.append(scipyRes.nfev)
    # nit_scipy.append(scipyRes.nit)
    # nfev_mynm.append(myRes.nfev)
    # nit_mynm.append(myRes.niter)

# # print("nfev_scipy:", sum(nfev_scipy)/nexpts)
# # print("nit_scipy:", sum(nit_scipy)/nexpts)
# print("nfev_mynm:", sum(nfev_mynm)/nexpts)
# print("nit_mynm:", sum(nit_mynm)/nexpts)

for m in ["spendley", "axis", "random", "jon"]:
    print(m)
    print("nfevs:", sum(nfevs[m]) / nexpts)
    print("nits:", sum(nits[m]) / nexpts)
