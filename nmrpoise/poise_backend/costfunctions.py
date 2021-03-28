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


def epsi_gradient_drift():
    """
    Calculates the amount of 'gradient drift' seen in a 1D EPSI acquisition, as
    reflected by the position of the 'echo' moving over time. This can be
    caused by imbalanced positive and negative gradients.
    """
    from numpy.polynomial.polynomial import Polynomial
    # --- Calculate key parameters -------------------------------
    fid = get1d_fid(remove_grpdly=True)
    # Number of complex points in k-space, i.e. number of points per EPSI
    # gradient. TD2 is total number of real & imag points in FID. L3 is number
    # of EPSI loops (one loop includes both pos + neg gradient). So TD2 / (2 *
    # L3) is the number of points in one EPSI gradient (i.e. only positive
    # gradient). The extra factor of 2 is because we're interested only in
    # complex points.
    td_k = int(getpar("TD") / (2 * 2 * getpar("L3")))
    # Time between consecutive EPSI positive gradients, in seconds
    td_t2 = int(getpar("L3"))
    dw_eff = getpar("AQ") / td_t2

    # --- Perform EPSI processing --------------------------------
    # Reshape into 2D matrix
    ser = fid.reshape((-1, td_k))
    # Discard the part acquired with negative gradients
    ser = ser[0::2, :]

    # Discard any part of the spectrum that was not acquired during an EPSI
    # gradient, i.e. if the delay D6 was nonzero.
    if getpar("D6") > 0:
        ineligible_epsi_points = int(1e6 * getpar("D6") / (getpar("DW") * 2))
        td_k = td_k - ineligible_epsi_points
        ser = ser[:, :td_k]

    # --- Apodisation --------------------------------------------
    # Along k-dimension (Hamming window)
    alpha_0 = 0.54
    ks = np.linspace(0, 1, td_k)
    k_winfunc = (alpha_0
                 - (1 - alpha_0) * np.cos(2 * np.pi * np.linspace(0, 1, td_k)))
    ser = ser * k_winfunc[np.newaxis, :]
    # Along direct dimension
    t2_winfunc = np.sin(np.pi * np.linspace(0, 1, td_t2))
    ser = ser * t2_winfunc[:, np.newaxis]
    abs_ser = np.abs(ser)

    # Calculate k- and t2-axes
    t2_values = np.arange(td_t2) * dw_eff
    k_values = np.linspace(-0.5, 0.5, td_k)

    # Drop all rows (i.e. all values of t2) for which the maximum is less than
    # 20% of the overall maximum.
    threshold_amp = 0.2 * np.max(abs_ser)
    maxima_along_rows = np.max(abs_ser, axis=1)
    indices_to_use = np.nonzero(maxima_along_rows > threshold_amp)
    # Locate the maxima
    maximal_indices_along_k = np.argmax(abs_ser, axis=1)
    # Get the value of k at each maximum
    k_max_values = k_values[maximal_indices_along_k]
    poly = Polynomial.fit(x=t2_values[indices_to_use],
                          y=k_max_values[indices_to_use], deg=1)
    return np.abs(poly.coef[1])


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
def specdiff():
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
