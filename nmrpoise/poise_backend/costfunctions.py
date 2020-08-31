"""
costfunctions.py
----------------

Contains default (and user-defined) cost functions.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import numpy as np

from .cfhelpers import *


def noe_1d():
    f = getpar("SPOFFS2") + getpar("O1")   # frequency of selective pulse
    bw = 50.0                              # rough bandwidth of selective pulse
    sfo1 = getpar("SFO1")
    upperhalf = f"{(f + bw/2)/sfo1:.3f}.."
    lowerhalf = f"..{(f - bw/2)/sfo1:.3f}"
    return -abs(np.sum(get1d_real(bounds=upperhalf)) +
                np.sum(get1d_real(bounds=lowerhalf)))


def minabsint():
    r = get1d_real()
    i = get1d_imag()
    return np.sum(np.abs(r + 1j*i))


def maxabsint():
    r = get1d_real()
    i = get1d_imag()
    return -np.sum(np.abs(r + 1j*i))


def minrealint():
    return np.sum(get1d_real())


def maxrealint():
    return -np.sum(get1d_real())


def zerorealint():
    return np.abs(np.sum(get1d_real()))


# The cost functions below were used in the POISE paper, but are less likely to
# be generally useful. If you want to use them, simply uncomment them.


# def asaphsqc():
#     spec = get2d_rr()
#     proj = np.amax(spec, axis=0)
#     return -np.sum(proj)


# def psyche():
#     target = get1d_real(epno=[1, 1])
#     spec = get1d_real()
#     return np.linalg.norm(target/np.linalg.norm(target) -
#                           spec/np.linalg.norm(spec))


# def dosy():
#     target = get1d_real(epno=[99998, 1])
#     spec = get1d_real()
#     return np.abs(np.sum(spec)/np.sum(target) - 0.25)


# def dosy_aux():
#     target = get1d_real(epno=[99998, 1])
#     spec = get1d_real()
#     return np.sum(spec)/np.sum(target) - 0.25


# def dosy_2p():
#     target = get1d_real(epno=[99998, 1])
#     spec = get1d_real()
#     return np.abs(np.sum(spec)/np.sum(target) - 0.25) + getpar("D20")
