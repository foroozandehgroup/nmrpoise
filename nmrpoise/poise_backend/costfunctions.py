"""
costfunctions.py
----------------

Contains default cost functions. Custom cost functions should be added in
costfunctions_user.py (using the same format).

You can add custom cost functions in here (they will work), but they will be
shadowed by any similarly named cost functions in costfunctions_user.py. Also,
this file will be overwritten if POISE is reinstalled.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import numpy as np

from .cfhelpers import *
from .shared import _g


def noe_1d():
    """
    Measures the intensity of peaks in the spectrum, *except* for anything
    within 25 Hz of the selectively excited peak.
    """
    # SPOFFS2 plus O1 is the frequency of the selective pulse, in Hz.
    # We can get the values of both using getpar(), which automatically
    # converts numeric parameters to floats.
    f = getpar("SPOFFS2") + getpar("O1")
    # Define the (rough) bandwidth of the selective pulse. We will ignore the
    # region of the spectrum that is bw Hz wide and centred on the selective
    # pulse.
    bw = 50.0
    # To get the spectrum *without* the ignored region, we split up the
    # spectrum into two "portions". We need to construct the 'bounds' parameter
    # for both portions.
    sfo1 = getpar("SFO1")
    lowerhalf = f"{(f + bw/2)/sfo1:.3f}.."   # frequencies (f + bw)/2 and above
    upperhalf = f"..{(f - bw/2)/sfo1:.3f}"   # frequencies up to (f - bw)/2
    # We use get1d_real() to get both portions of the spectrum, passing the
    # bounds as appropriate. The intensities of the spectrum are obtained by
    # summing all points (np.sum).
    # Note that manually passing the bounds parameter will override the F1P/F2P
    # parameters if set by the user (this is probably a good thing).
    upper_integral = np.sum(get1d_real(bounds=upperhalf))
    lower_integral = np.sum(get1d_real(bounds=lowerhalf))
    # Lastly, we take the negative absolute value of the resulting sum, in
    # order to make sure that the resulting cost function is negative
    # regardless of how the NOE peaks are phased (positive or negative).
    return -abs(upper_integral + lower_integral)


def minabsint():
    """
    Cost function which minimises the absolute (magnitude-mode) intensity of
    the spectrum. This is probably the easiest cost function. :-)
    """
    # Get the real part of the spectrum as a numpy ndarray. Because no bounds
    # are explicitly passed, this defaults to the whole spectrum if F1P/F2P are
    # not specified. If F1P/F2P *are* specified (either via the `dpl` TopSpin
    # command, or manually), this will only return the part of the spectrum
    # between those two values.
    r = get1d_real()
    # ...and the imaginary part
    i = get1d_imag()
    # The magnitude-mode spectrum is obtained by combining these.
    mag = np.abs(r + 1j * i)
    # The intensity of the magnitude-mode spectrum is just the sum of all
    # points.
    return np.sum(mag)


def maxabsint():
    """
    Cost function which maximises the absolute (magnitude-mode) intensity of
    the spectrum.
    """
    r = get1d_real()
    i = get1d_imag()
    # This is the same as minabsint except that we have a negative sign.
    # Because the optimisation always seeks to *minimise* the cost function,
    # this essentially tries to *maximise* np.sum(...), i.e. maximise the
    # spectral intensity.
    return -np.sum(np.abs(r + 1j*i))


def minrealint():
    """
    Minimises the intensity of the real part of the spectrum. If the spectrum
    has negative peaks this cost function will try to maximise those.
    """
    return np.sum(get1d_real())


def maxrealint():
    """
    Maximises the intensity of the real part of the spectrum.
    """
    return -np.sum(get1d_real())


def zerorealint():
    """
    Tries to get the intensity of the real spectrum to be as close to zero as
    possible. This works by summation, so dispersion-mode peaks will not
    contribute to this cost function (as they add to zero).
    """
    return np.abs(np.sum(get1d_real()))


def dosy():
    """
    Tries to make a spectrum (1D diffusion experiment with variable gradient
    strength) have 25% intensity of a target spectrum (1D diffusion experiment
    with minimum gradient strength). This should be used in conjunction with
    the dosy_opt Python programme (after POISE is installed via `pip`, this can
    be installed from the TopSpin command-line via `poise --install dosy`.)
    """
    # The target spectrum is hardcoded to have EXPNO 99998. See psyche() for
    # more discussion about this.
    # As in psyche(), the F1P/F2P parameters are not taken from the reference
    # spectrum but from the spectrum being optimised.
    reference_path = make_p_spec(expno=99998, procno=1)
    target = get1d_real(p_spec=reference_path)
    # This is the spectrum being optimised.
    spec = get1d_real()
    # The intensity of the optimised spectrum is np.sum(spec), and likewise for
    # the target spectrum. We take the ratio of the two and measure how "far
    # away" this is from the ideal value of 0.25 (which corresponds to 75%
    # attenuation).
    return np.abs(np.sum(spec)/np.sum(target) - 0.25)


def dosy_aux():
    """
    Non-absolute value of dosy(). To be used in the first stage of dosy_opt.
    """
    reference_path = make_p_spec(expno=99998, procno=1)
    target = get1d_real(p_spec=reference_path)
    spec = get1d_real()
    return np.sum(spec)/np.sum(target) - 0.25


# The cost functions below were used in the POISE paper, but are less likely to
# be generally useful. If you want to use them, simply uncomment them (remove
# the three single quotes around them).

'''
def asaphsqc():
    """
    Maximises the intensity of the projection of a 2D spectrum onto the f2
    axis.
    """
    # First we get the 'rr' part of the spectrum (the displayed part). This
    # assumes that it has been phased already (by the AU program).
    # This is a 2D numpy array:
    # [ [1  , 2, 3, ..., si2],
    #   [.  , ., ., ..., ...],
    #   [.  , ., ., ..., ...],
    #   [si1, ., ., ..., ...]]
    # where si1 and si2 are the values of SI in the indirect and direct
    # dimension respectively.
    spec = get2d_rr()
    # We take the 'skyline' projection, i.e. the highest point along each
    # column. This is basically equivalent to TopSpin's `f2projp` command.
    # If you want a projection onto f1 instead of f2, you can use axis=1.
    proj = np.amax(spec, axis=0)
    return -np.sum(proj)
'''

'''
def psyche():
    """
    Returns the "spectral difference" between the current spectrum and a
    reference spectrum with EXPNO 1 and PROCNO 1.
    """
    # We can construct the path to the reference spectrum using make_p_spec().
    reference_path = make_p_spec(expno=1, procno=1)
    # The way this is currently coded, the reference spectrum has to be placed
    # in EXPNO 1 and PROCNO 1. In theory, this can be specified using a TopSpin
    # parameter in the optimisation dataset, for example "cnst30" (or any other
    # random cnst). In order to use this, just add:
    #     expno = # int(getpar("cnst30"))
    # and then after that you can use
    #     make_p_spec(expno=expno, procno=1)
    # Then we can get the reference, or 'target', spectrum as a numpy array.
    # Note that this will respect the F1P/F2P parameters, *not* of the
    # reference spectrum, but of the spectrum being optimised. This is because
    # get1d_real() does not actually read F1P and F2P from the spectrum. It
    # just uses the global values stored in _g.spec_f1p and _g.spec_f2p, which
    # refer to the F1P/F2P values of the spectrum being optimised.
    target = get1d_real(p_spec=reference_path)
    # ... and the current spectrum that is being optimised.
    spec = get1d_real()
    # Finally, return the 2-norm of the difference between the two normalised
    # spectra.
    return np.linalg.norm(target/np.linalg.norm(target) -
                          spec/np.linalg.norm(spec))
'''


'''
def dosy_2p():
    """
    Two-parameter DOSY optimisation.
    """
    reference_path = make_p_spec(expno=99998, procno=1)
    target = get1d_real(p_spec=reference_path)
    spec = get1d_real()
    return np.abs(np.sum(spec)/np.sum(target) - 0.25) + getpar("D20")
'''
