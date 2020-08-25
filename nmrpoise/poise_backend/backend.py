import sys
import json
from traceback import print_exc
from datetime import datetime
from pathlib import Path
from collections import namedtuple

import numpy as np

# Enable relative imports when invoked directly as __main__ by TopSpin.
# cf. PEP 366 and https://stackoverflow.com/a/54490918
# This allows us to import the optpoise.py that is inside $ts/py/user, instead
# of the one inside site-packages. Essentially, that allows us to maintain
# internal consistency as the version of code that is run is always the one
# inside $ts/py/user.
if __name__ == "__main__" and __package__ is None:
    __package__ = "poise_backend"
    sys.path.insert(1, str(Path(__file__).parents[1].resolve()))
    __import__(__package__)

from .optpoise import (scale, unscale, deco_count,
                       nelder_mead, multid_search, pybobyqa_interface)

Routine = namedtuple("Routine", "name pars lb ub init tol cf au")


class _g():
    """
    Class to store the "global" variables.
    """
    optimiser = None
    routine_id = None
    p_spectrum = None
    p_optlog = None
    p_errlog = None
    maxfev = 0
    p_poise = Path(__file__).parent.resolve()
    spec_f1p = None
    spec_f2p = None


def main():
    """
    Main routine.
    """
    tic = datetime.now()

    # Load the routine and cost function.
    routine, cost_function = get_routine_cf(_g.routine_id)

    # Choose the optimisation function. optpoise implements a PyBOBYQA
    # interface so that the returned result has the same attributes as our
    # other optimisers.
    optimfndict = {"nm": nelder_mead,
                   "mds": multid_search,
                   "bobyqa": pybobyqa_interface
                   }
    try:
        optimfn = optimfndict[_g.optimiser.lower()]
    except KeyError:
        raise ValueError(f"Invalid optimiser {_g.optimiser} specified.")

    # Scale the initial values and tolerances
    npars = len(routine.pars)
    scaled_x0, scaled_lb, scaled_ub, scaled_xtol = scale(routine.init,
                                                         routine.lb,
                                                         routine.ub,
                                                         routine.tol,
                                                         scaleby="tols")

    # Some logging
    with open(_g.p_optlog, "a") as log:
        print("\n\n\n", file=log)
        print("=" * 40, file=log)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file=log)
        fmt = "{:25s} - {}"
        print(fmt.format("Routine name", routine.name), file=log)
        print(fmt.format("Optimisation parameters", routine.pars), file=log)
        print(fmt.format("Cost function", routine.cf), file=log)
        print(fmt.format("AU programme", routine.au), file=log)
        print(fmt.format("Initial values", routine.init), file=log)
        print(fmt.format("Lower bounds", routine.lb), file=log)
        print(fmt.format("Upper bounds", routine.ub), file=log)
        print(fmt.format("Tolerances", routine.tol), file=log)
        print(fmt.format("Optimisation algorithm", _g.optimiser), file=log)
        print("", file=log)
        fmt = "{:^10s}  " * (npars + 1)
        print(fmt.format(*routine.pars, "cf"), file=log)
        print("-" * 12 * (npars + 1), file=log)

    # Get F1P/F2P parameters
    x, y = getpar("F1P"), getpar("F2P")
    if isinstance(x, float) and isinstance(y, float):  # 1D
        if x != 0 and y != 0:
            _g.spec_f1p, _g.spec_f2p = x, y
    elif isinstance(x, np.ndarray) and isinstance(y, np.ndarray):  # 2D
        if not np.array_equal(x, [0, 0]) and not np.array_equal(y, [0, 0]):
            _g.spec_f1p, _g.spec_f2p = x, y

    # Set up optimisation arguments
    optimargs = (cost_function, routine)
    # Carry out the optimisation
    opt_result = optimfn(acquire_nmr, scaled_x0, scaled_xtol, optimargs,
                         scaled_lb=scaled_lb, scaled_ub=scaled_ub,
                         maxfev=_g.maxfev)

    # Tell frontend script that the optimisation is done
    best_values = unscale(opt_result.xbest, routine.lb,
                          routine.ub, routine.tol, scaleby="tols")
    print("optima: " + " ".join([str(i) for i in best_values]))

    # More logging
    toc = datetime.now()
    time_taken = str(toc - tic).split(".")[0]  # remove microseconds
    with open(_g.p_optlog, "a") as log:
        print("", file=log)
        fmt = "{:27s} - {}"
        print(fmt.format("Best values found", best_values.tolist()), file=log)
        print(fmt.format("Cost function at minimum", opt_result.fbest),
              file=log)
        print(fmt.format("Number of spectra ran", acquire_nmr.calls),
              file=log)
        print(fmt.format("Total time taken", time_taken), file=log)


def get_routine_cf(routine_id, p_routine_dir=None, p_cf_dir=None):
    """
    First finds the routine file and instantiates a Routine. Then finds the
    associated cost function script and exec's it, which defines
    cost_function().

    Parameters
    ----------
    routine_id : str
        Name of the routine being used.

    Returns
    -------
    Routine
        The Routine object requested.
    function
        The cost function object associated with the routine.

    Other Parameters
    ----------------
    p_routine_dir : pathlib.Path, optional
        Path to the folder containing the routines. Defaults to the
        poise_backend/routines directory. This parameter only exists for
        unit test purposes and should not otherwise be used.
    p_cf_dir : pathlib.Path, optional
        Path to the folder containing the cost functions. Defaults to the
        poise_backend/cost_functions directory. This parameter only exists for
        unit test purposes and should not otherwise be used.
    """
    # Load the routine.
    p_routine_dir = p_routine_dir or (_g.p_poise / "routines")
    with open(p_routine_dir / (routine_id + ".json"), "rb") as f:
        routine = Routine(**json.load(f))

    # Load the cost function
    p_cf_dir = p_cf_dir or (_g.p_poise / "cost_functions")
    p_cf_file = p_cf_dir / (routine.cf + ".py")
    ld = {}
    exec(open(p_cf_file).read(), globals(), ld)
    # in p_cf, the cost function is defined as cost_function().
    # executing the file will define it for us
    # but see also https://stackoverflow.com/questions/1463306/
    try:
        cost_function = ld["cost_function"]
    except KeyError:
        if len(ld) == 1:
            cost_function = ld[list(ld)[0]]
        else:
            raise
    return routine, cost_function


@deco_count
def acquire_nmr(x, cost_function, routine):
    """
    This is the function which is actually passed to the optimisation function
    as the "cost function", and is responsible for triggering acquisition in
    the frontend.

    Briefly, this function does the following:

     - Returns np.inf immediately if the values are outside the given bounds.
     - Otherwise, prints the values to stdout, which triggers acquisition by
       the frontend.
     - Waits for the frontend to pass the message "done" back, indicating that
       the spectrum has been acquired and processed.
     - Calculates the cost function using the user-defined cost_function().
     - Performs logging throughout.

    Parameters
    ----------
    x : ndarray
        Scaled values to be used for spectrum acquisition and cost function
        evaluation.
    cost_function : function
        User-defined cost function object.
    routine : Routine
        The active optimisation routine.

    Returns
    -------
    cf_val : float
        Value of the cost function.
    """
    unscaled_val = unscale(x, routine.lb, routine.ub,
                           routine.tol, scaleby="tols")
    # Format string for logging.
    fstr = "{:^10.4f}  " * (len(x) + 1)

    with open(_g.p_optlog, "a") as log:
        # Enforce constraints on optimisation.
        # This doesn't need to be done for BOBYQA, because we pass the `bounds`
        # parameter, which automatically stops it from sampling outside the
        # bounds. If we *do* enforce the constraints on BOBYQA, this can lead
        # to bad errors, as due to floating-point inaccuracy sometimes it tries
        # to sample a point that is ___just___ outside of the bounds (see #39).
        # Instead, we should just let it evaluate the point as usual.
        if (_g.optimiser in ["nm", "mds"] and
                (np.any(unscaled_val < routine.lb)
                 or np.any(unscaled_val > routine.ub))):
            # Set the value of the cost function to infinity.
            cf_val = np.inf
            # Log that.
            print(fstr.format(*unscaled_val, cf_val), file=log)
            # Return immediately.
            return cf_val

        # Print unscaled values, prompting frontend script to start acquisition
        print("values: " + " ".join([str(i) for i in unscaled_val]))
        # Wait for acquisition to complete, then calculate cost function
        signal = input()  # frontend prints "done" here
        # Set p_spectrum according to which spectrum the frontend evaluated.
        # This is important when using the separate_expnos option.
        _g.p_spectrum = Path(input())  # frontend prints path to active spec.
        # Evaluate the cost function, log, pass the cost function value back
        # to the frontend (it's stored in the `TI` parameter), and return.
        if signal == "done":
            cf_val = cost_function()
            fstr = "{:^10.4f}  " * (len(x) + 1)
            print(fstr.format(*unscaled_val, cf_val), file=log)
            print(f"cf: {cf_val}")
            return cf_val
        else:
            # This really shouldn't happen.
            raise ValueError(f"Invalid signal passed from frontend: {signal}")


###############################################################################
# Helper functions used in cost functions -- below                            #
# ---------------------------------------                                     #
#                                                                             #
# Unfortunately, these need to be in backend.py instead of being imported     #
# from a different module, because many of them rely on _g.p_spectrum to      #
# work.                                                                       #
###############################################################################


def _parse_bounds(b):
    """
    Parses the bounds string "lower..upper", or the bounds tuple (lower,
    upper), to get the lower and upper bounds.

    Parameters
    ----------
    b : str or tuple
        The bounds string "lower..upper", or the tuple (lower, upper).

    Returns
    -------
    lower : float or None
        Lower bound. None if not specified.
    upper : float or None
        Upper bound. None if not specified.
    """
    try:
        if isinstance(b, str):
            if b == "":
                return None, None
            elif b.startswith(".."):   # "..5" -> (None, 5)
                return None, float(b[2:])
            elif b.endswith(".."):   # "3.." -> (3, None)
                return float(b[:-2]), None
            elif ".." in b:
                x, y = b.split("..")
                return float(x), float(y)
            else:
                raise ValueError
        else:  # not a string, hopefully a tuple
            if len(b) != 2:
                raise ValueError
            # ValueError if b[0] isn't numeric
            lower = float(b[0]) if b[0] is not None else None
            upper = float(b[1]) if b[1] is not None else None
            return lower, upper
    except (ValueError, TypeError):
        raise ValueError(f"Invalid value {b} provided for bounds.")


def _ppm_to_point(shift, axis=None, p_spec=None):
    """
    Round a specific chemical shift to the nearest point in the spectrum.

    For unknown reasons, this does not correlate perfectly to the "index" that
    is displayed in TopSpin. However, the difference between the indices
    calculated here and the index in TopSpin is on the order of 1e-4 to 1e-3
    ppm. (More precisely, it's ca. 0.25 * SW / SI.)

    Parameters
    ----------
    shift : float
        Desired chemical shift.
    axis : int, optional
        Axis along which to calculate this. For 1D spectra this should be left
        as None. For 2D spectra, axis=0 and axis=1 correspond to the f1 and f2
        dimensions respectively.

    Returns
    -------
    int or None
        The desired point. None if the chemical shift lies outside the spectral
        window.

    Notes
    -----
    The p_spec parameter is only used in unit tests and should not actually be
    passed in a cost function. Under normal circumstances this will default to
    the FID or spectrum being measured.
    """
    p_spec = p_spec or _g.p_spectrum
    si = getpar("SI", p_spec)
    o1p = getpar("O1", p_spec) / getpar("SFO1", p_spec)
    sw = getpar("SW", p_spec)

    # Pick out the appropriate value according to the relevant axis
    if axis is not None:
        if axis in [0, 1]:
            si, o1p, sw = si[axis], o1p[axis], sw[axis]
        else:
            raise ValueError(f"Invalid value '{axis}' for axis.")

    # Make sure it's within range
    highest_shift = o1p + 0.5*sw
    lowest_shift = o1p - 0.5*sw
    if shift > highest_shift or shift < lowest_shift:
        return None

    # Calculate the value
    spacing = (highest_shift - lowest_shift)/(si - 1)
    x = 1 + round((highest_shift - shift)/spacing)
    return int(x)


def get1d_fid(p_spec=None):
    """
    Returns the FID as a |ndarray|.

    Note that this does *not* modify the "group delay" at the beginning of the
    FID.

    Also, Bruker spectrometers record real and imaginary points in a sequential
    fashion. Therefore, each imaginary point in the ndarray is actually
    measured ``DW`` *after* the corresponding real point. When Fourier
    transforming, this can be accounted for by using fftshift().

    Parameters
    ----------
    None

    Returns
    -------
    ndarray
        Complex-valued array containing the FID.

    Notes
    -----
    The p_spec parameter is only used in unit tests and should not actually be
    passed in a cost function. Under normal circumstances this will default to
    the FID or spectrum being measured.
    """
    p_spec = p_spec or _g.p_spectrum
    p_fid = p_spec.parents[1] / "fid"
    fid = np.fromfile(p_fid, dtype=np.int32)
    td = fid.size
    fid = fid.reshape(int(td/2), 2)
    fid = np.transpose(fid)
    # so now fid[0] is the real part, fid[1] the imaginary
    return fid[0] + (1j * fid[1])


def _get_1d(spec_fname, bounds="", epno=None, p_spec=None):
    """
    Get a 1D spectrum. This function accounts for TopSpin's NC_PROC variable,
    scaling the spectrum intensity accordingly.

    To get the real spectrum and imaginary spectrum, pass spec_fname="1r" or
    spec_fname="1i" respectively.

    Note that this function only works for 1D spectra. It does *not* work for
    1D projections of 2D spectra. If you want to work with projections, you can
    use get_2d_spectrum() to get the full 2D spectrum, then manipulate it using
    numpy functions as appropriate. Examples can be found in the docs.

    The bounds parameter may be specified in the following formats:
       - between 5 and 8 ppm:   bounds="5..8"  OR bounds=(5, 8)
       - greater than 9.3 ppm:  bounds="9.3.." OR bounds=(9.3, None)
       - less than -2 ppm:      bounds="..-2"  OR bounds=(None, -2)

    Parameters
    ----------
    spec_fname : str
        File name of the spectrum; "1r" for real or "1i" for imaginary.
    bounds : str or tuple, optional
        String or tuple describing the region of interest. See above for
        examples. If no bounds are provided, uses the ``F1P`` and ``F2P``
        processing parameters, which can be specified via ``dpl``. If these are
        not specified, defaults to the whole spectrum.
    epno : tuple of int, optional
        (expno, procno) of spectrum of interest. Defaults to the spectrum
        being evaluated. As of now, there is no way to read in a spectrum in a
        folder with a different name (please let us know if this is a useful
        feature that should be implemented).

    Returns
    -------
    ndarray
        Array containing the spectrum or the desired section of it (if bounds
        were specified).

    Notes
    -----
    The p_spec parameter is only used in unit tests and should not actually be
    passed in a cost function.
    """
    # Check whether user has specified epno
    if epno is not None:
        if len(epno) == 2:
            p_spec = p_spec or _g.p_spectrum
            p_spec = p_spec.parents[2] / str(epno[0]) / "pdata" / str(epno[1])
        else:
            raise ValueError("Please provide a valid [expno, procno] "
                             "combination.")

    p_spec = p_spec or _g.p_spectrum
    p_specdata = p_spec / spec_fname
    spec = np.fromfile(p_specdata, dtype=np.int32)
    nc_proc = int(getpar("NC_proc", p_spec))
    spec = spec * (2 ** nc_proc)

    if bounds == "":
        if _g.spec_f1p is None and _g.spec_f2p is None:  # DPL not used
            return spec
        else:
            left, right = _g.spec_f1p, _g.spec_f2p
    else:
        right, left = _parse_bounds(bounds)

    # Get default bounds
    si = int(getpar("SI", p_spec))
    left_point, right_point = 0, si - 1
    # Then replace them if necessary
    if left is not None:
        left_point = _ppm_to_point(left, p_spec=p_spec)
    if right is not None:
        right_point = _ppm_to_point(right, p_spec=p_spec)

    return spec[left_point:right_point + 1]


def get1d_real(bounds="", epno=None, p_spec=None):
    """
    Get the real spectrum. This function accounts for TopSpin's NC_PROC
    variable, scaling the spectrum intensity accordingly.

    Note that this function only works for 1D spectra. It does *not* work for
    1D projections of 2D spectra. If you want to work with projections, you can
    use get_2d_spectrum() to get the full 2D spectrum, then manipulate it using
    numpy functions as appropriate. Examples can be found in the docs.

    The bounds parameter may be specified in the following formats:
       - between 5 and 8 ppm:   bounds="5..8"  OR bounds=(5, 8)
       - greater than 9.3 ppm:  bounds="9.3.." OR bounds=(9.3, None)
       - less than -2 ppm:      bounds="..-2"  OR bounds=(None, -2)

    Parameters
    ----------
    spec_fname : str
        File name of the spectrum; "1r" for real or "1i" for imaginary.
    bounds : str or tuple, optional
        String or tuple describing the region of interest. See above for
        examples. If no bounds are provided, uses the ``F1P`` and ``F2P``
        processing parameters, which can be specified via ``dpl``. If these are
        not specified, defaults to the whole spectrum.
    epno : tuple of int, optional
        (expno, procno) of spectrum of interest. Defaults to the spectrum
        being evaluated. As of now, there is no way to read in a spectrum in a
        folder with a different name (please let us know if this is a useful
        feature that should be implemented).

    Returns
    -------
    ndarray
        Array containing the spectrum or the desired section of it (if bounds
        were specified).

    Notes
    -----
    The p_spec parameter is only used in unit tests and should not actually be
    passed in a cost function.
    """
    return _get_1d(spec_fname="1r", bounds=bounds, epno=epno, p_spec=p_spec)


def get1d_imag(bounds="", epno=None, p_spec=None):
    """
    Same as `get1d_real`, except that it reads the imaginary spectrum.
    """
    return _get_1d(spec_fname="1i", bounds=bounds, epno=epno, p_spec=p_spec)


def _get_2d(spec_fname, f1_bounds="", f2_bounds="", epno=None, p_spec=None):
    """
    Get a 2D spectrum. This function takes into account the NC_proc value in
    TopSpin's processing parameters.

    The f1_bounds and f2_bounds parameters may be specified in the following
    formats:
       - between 5 and 8 ppm:   f1_bounds="5..8"  OR f1_bounds=(5, 8)
       - greater than 9.3 ppm:  f1_bounds="9.3.." OR f1_bounds=(9.3, None)
       - less than -2 ppm:      f1_bounds="..-2"  OR f1_bounds=(None, -2)

    Parameters
    ----------
    spec_fname : str
        Filename of the spectrum of interest. Can be "2rr", "2ri", "2ir", or
        "2ii", corresponding to the four hypercomplex quadrants.
    f1_bounds : str or tuple, optional
        String or tuple describing the indirect-dimension region of interest.
        See above for examples. If no bounds are provided, uses the ``1 F1P``
        and ``1 F2P`` processing parameters, which can be specified via
        ``dpl``. If these are not specified, defaults to the whole spectrum.
    f2_bounds : str or tuple, optional
        String or tuple describing the direct-dimension region of interest. See
        above for examples. If no bounds are provided, uses the ``2 F1P`` and
        ``2 F2P`` processing parameters, which can be specified via ``dpl``. If
        these are not specified, defaults to the whole spectrum.
    epno : tuple of int, optional
        (expno, procno) of spectrum of interest. Defaults to the spectrum
        being evaluated. As of now, there is no way to read in a spectrum in a
        folder with a different name (please let us know if this is a useful
        feature that should be implemented).

    Returns
    -------
    ndarray
        2D array containing the spectrum or the desired section of it (if
        *f1_bounds* or *f2_bounds* were specified).

    Notes
    -----
    The p_spec parameter is only used in unit tests and should not actually be
    passed in a cost function.
    """
    # Check whether user has specified epno
    if epno is not None:
        if len(epno) == 2:
            p_spec = p_spec or _g.p_spectrum
            p_spec = p_spec.parents[2] / str(epno[0]) / "pdata" / str(epno[1])
        else:
            raise ValueError("Please provide a valid [expno, procno] "
                             "combination.")

    p_spec = p_spec or _g.p_spectrum
    p_specdata = p_spec / "2rr"

    # Check data type (TopSpin 3 int vs TopSpin 4 float)
    dtypp = getpar("dtypp", p_spec)
    if dtypp[0] == 0 and dtypp[1] == 0:  # TS3 data
        dt = "<" if np.all(getpar("bytordp", p_spec) == 0) else ">"
        dt += "i4"
    else:
        raise NotImplementedError("get_2d_spectrum(): "
                                  "float data not yet accepted")
    sp = np.fromfile(p_specdata, dtype=np.dtype(dt))
    # Format according to xdim. See TopSpin "data format" manual.
    # See also http://docs.nmrfx.org/viewer/files/datasets.
    # Get si and xdim
    si = getpar("si", p_spec)
    si = (int(si[0]), int(si[1]))
    xdim = getpar("xdim", p_spec)
    xdim = (int(xdim[0]), int(xdim[1]))
    sp = sp.reshape(si)
    # Reshape.
    nrows, ncols = int(si[0]/xdim[0]), int(si[1]/xdim[1])
    submatrix_size = np.prod(xdim)
    sp = sp.reshape(si[0] * ncols, xdim[1])
    sp = np.vsplit(sp, nrows * ncols)
    sp = np.concatenate(sp, axis=1)
    sp = np.hsplit(sp, nrows)
    sp = np.concatenate(sp, axis=0)
    sp = sp.reshape(si)
    sp = sp * (2 ** getpar("nc_proc", p_spec)[1])

    # Read in DPL and overwrite bounds if the bounds were not set
    if f1_bounds == "":
        if _g.spec_f1p is not None and _g.spec_f2p is not None:  # DPL was used
            # f2p is lower than f1p.
            f1_bounds = f"{_g.spec_f2p[0]}..{_g.spec_f1p[0]}"
    if f2_bounds == "":
        if _g.spec_f1p is not None and _g.spec_f2p is not None:  # DPL was used
            f2_bounds = f"{_g.spec_f2p[1]}..{_g.spec_f1p[1]}"
    f1_lower, f1_upper = _parse_bounds(f1_bounds)
    f2_lower, f2_upper = _parse_bounds(f2_bounds)
    # Convert ppm to points
    f1_lower_point = _ppm_to_point(f1_lower, axis=0, p_spec=p_spec) \
        if f1_lower is not None else si[0] - 1
    f1_upper_point = _ppm_to_point(f1_upper, axis=0, p_spec=p_spec) \
        if f1_upper is not None else 0
    f2_lower_point = _ppm_to_point(f2_lower, axis=1, p_spec=p_spec) \
        if f2_lower is not None else si[1] - 1
    f2_upper_point = _ppm_to_point(f2_upper, axis=1, p_spec=p_spec) \
        if f2_upper is not None else 0
    return sp[f1_upper_point:f1_lower_point + 1,
              f2_upper_point:f2_lower_point + 1]


def get2d_rr(f1_bounds="", f2_bounds="", epno=None, p_spec=None):
    """
    Get the real part of the 2D spectrum (the "RR" quadrant). This function
    takes into account the NC_proc value in TopSpin's processing parameters.

    The f1_bounds and f2_bounds parameters may be specified in the following
    formats:
       - between 5 and 8 ppm:   f1_bounds="5..8"  OR f1_bounds=(5, 8)
       - greater than 9.3 ppm:  f1_bounds="9.3.." OR f1_bounds=(9.3, None)
       - less than -2 ppm:      f1_bounds="..-2"  OR f1_bounds=(None, -2)

    Parameters
    ----------
    spec_fname : str
        Filename of the spectrum of interest. Can be "2rr", "2ri", "2ir", or
        "2ii", corresponding to the four hypercomplex quadrants.
    f1_bounds : str or tuple, optional
        String or tuple describing the indirect-dimension region of interest.
        See above for examples. If no bounds are provided, uses the ``1 F1P``
        and ``1 F2P`` processing parameters, which can be specified via
        ``dpl``. If these are not specified, defaults to the whole spectrum.
    f2_bounds : str or tuple, optional
        String or tuple describing the direct-dimension region of interest. See
        above for examples. If no bounds are provided, uses the ``2 F1P`` and
        ``2 F2P`` processing parameters, which can be specified via ``dpl``. If
        these are not specified, defaults to the whole spectrum.
    epno : tuple of int, optional
        (expno, procno) of spectrum of interest. Defaults to the spectrum
        being evaluated. As of now, there is no way to read in a spectrum in a
        folder with a different name (please let us know if this is a useful
        feature that should be implemented).

    Returns
    -------
    ndarray
        2D array containing the spectrum or the desired section of it (if
        *f1_bounds* or *f2_bounds* were specified).

    Notes
    -----
    The p_spec parameter is only used in unit tests and should not actually be
    passed in a cost function.
    """
    return _get_2d(spec_fname="2rr",
                   f1_bounds=f1_bounds, f2_bounds=f2_bounds,
                   epno=epno, p_spec=p_spec)


def get2d_ri(f1_bounds="", f2_bounds="", epno=None, p_spec=None):
    """
    Same as `get2d_rr`, except that it reads the '2ri' file.
    """
    return _get_2d(spec_fname="2ri",
                   f1_bounds=f1_bounds, f2_bounds=f2_bounds,
                   epno=epno, p_spec=p_spec)


def get2d_ir(f1_bounds="", f2_bounds="", epno=None, p_spec=None):
    """
    Same as `get2d_rr`, except that it reads the '2ir' file.
    """
    return _get_2d(spec_fname="2ir",
                   f1_bounds=f1_bounds, f2_bounds=f2_bounds,
                   epno=epno, p_spec=p_spec)


def get2d_ii(f1_bounds="", f2_bounds="", epno=None, p_spec=None):
    """
    Same as `get2d_rr`, except that it reads the '2ii' file.
    """
    return _get_2d(spec_fname="2ii",
                   f1_bounds=f1_bounds, f2_bounds=f2_bounds,
                   epno=epno, p_spec=p_spec)


def _get_acqu_par(par, p_acqus):
    """
    Obtains the value of an acquisition parameter.

    Note that pulse powers in dB (PLdB / SPdB) cannot be obtained using this
    function, as they are not stored in the acqus file.

    Parameters
    ----------
    par : str
        Name of the acquisition parameter.
    p_acqus : pathlib.Path
        Path to the status acquisition file (this is 'acqus' for 1D spectra and
        direct dimension of 2D spectra, or 'acqu2s' for indirect dimension of
        2D spectra).

    Returns
    -------
    float or None
        Value of the acquisition parameter. None if the value is not a number,
        or if the parameter doesn't exist.
    """
    # Capitalise and remove any spaces from par
    par = par.upper()
    if len(par.split()) > 1:
        par = "".join(par.split())

    # Split par into number-less bit and number bit
    parl = par.rstrip("1234567890")
    parr = par[len(parl):]
    params_with_space = ["CNST", "D", "P", "PLW", "PCPD", "GPX", "GPY", "GPZ",
                         "SPW", "SPOAL", "SPOFFS", "L", "IN", "INP", "PHCOR"]
    # Get the parameter
    if (parr != "") and (parl in params_with_space):  # e.g. cnst2
        with open(p_acqus, "r") as file:
            # Read up to the line declaring the parameters
            for line in file:
                if line.upper().startswith(f"##${parl}="):
                    break
            else:   # triggers if didn't break -- i.e. parameter was not found
                return None
            # Grab the values and put them in a list
            s = ""
            # Read until next parameter
            line = file.readline()
            while line != "" and not line.startswith("##"):
                s = s + line + " "
                line = file.readline()
            # Pick out the desired value and return it
            value = s.split()[int(parr)]
            try:
                return float(value)
            except ValueError:  # not a float
                return None
    else:                                             # e.g. sfo1 or rg
        with open(p_acqus, "r") as file:
            for line in file:
                if line.upper().startswith(f"##${par}="):
                    value = line.split(maxsplit=1)[-1].strip()
                    # strip away surrounding angle brackets
                    if value[0] == '<' and value[-1] == '>':
                        value = value[1:-1]
                    try:
                        return float(value)
                    except ValueError:  # not a float
                        return None
    # If it hasn't been found
    return None


def _get_proc_par(par, p_procs):
    """
    Obtains the value of a processing parameter.

    Parameters
    ----------
    par : str
        Name of the processing parameter.
    p_procs : pathlib.Path
        Path to the status processing file (this is 'procs' for 1D spectra and
        direct dimension of 2D spectra, or 'proc2s' for indirect dimension of
        2D spectra).

    Returns
    -------
    float or None
        Value of the processing parameter. None if the value is not a number,
        or if the parameter doesn't exist.
    """
    # Capitalise and remove any spaces from par
    par = par.upper()
    if len(par.split()) > 1:
        par = "".join(par.split())
    # Get the value (for processing parameters there aren't any lists like
    # CNST/D/P)
    with open(p_procs, "r") as file:
        for line in file:
            if line.upper().startswith(f"##${par}="):
                value = line.split(maxsplit=1)[-1].strip()
                # strip away surrounding angle brackets
                if value[0] == '<' and value[-1] == '>':
                    value = value[1:-1]
                try:
                    return float(value)
                except ValueError:
                    return None


def getpar(par, p_spec=None):
    """
    Obtains the value of an (acquisition or processing) parameter. Works for
    both 1D and 2D spectra (see return type below).

    Parameters
    ----------
    par : str
        Name of the parameter.

    Returns
    -------
    float or ndarray
        Value(s) of the requested parameter. None if the given parameter was
        not found.

        For parameters that exist for both dimensions of 2D spectra, getpar()
        returns an ndarray consisting of (f1_value, f2_value).  Otherwise (for
        1D spectra, or for 2D parameters which only apply to the direct
        dimension), getpar() returns a float.

    Notes
    -----
    The p_spec parameter is only used in unit tests and should not actually be
    passed in a cost function.
    """
    p_spec = p_spec or _g.p_spectrum

    # Try to get acquisition parameter first.
    # Check indirect dimension
    p_acqus = p_spec.parents[1] / "acqus"
    p_acqu2s = p_spec.parents[1] / "acqu2s"
    v1, v2 = None, None
    if p_acqu2s.exists():
        v1 = _get_acqu_par(par, p_acqu2s)
    v2 = _get_acqu_par(par, p_acqus)
    if v1 is not None and v2 is not None:
        return np.array([v1, v2])
    elif v2 is not None:
        return v2

    # If reached here, means that acquisition parameter was not found
    # Try to get processing parameter
    # Check indirect dimension
    p_procs = p_spec / "procs"
    p_proc2s = p_spec / "proc2s"
    v1, v2 = None, None
    if p_proc2s.exists():
        v1 = _get_proc_par(par, p_proc2s)
    v2 = _get_proc_par(par, p_procs)
    if v1 is not None and v2 is not None:
        return np.array([v1, v2])
    elif v2 is not None:
        return v2

    # If reached here, neither was found
    return None


if __name__ == "__main__":
    # All errors in main() must be propagated back to the frontend so that
    # timely feedback can be provided to the user. The frontend is responsible
    # for the error logging.
    try:
        # Set global variables by reading in input from frontend.
        _g.optimiser = input()
        _g.routine_id = input()
        _g.p_spectrum = Path(input())
        _g.maxfev = int(input())
        _g.p_optlog = _g.p_spectrum.parents[1] / "poise.log"
        _g.p_errlog = _g.p_spectrum.parents[1] / "poise_err_backend.log"
        # Run main routine.
        main()
    except Exception as e:
        # Because the frontend is only reading one line at a time, there's
        # no point in printing the entire traceback. Thus we just print a
        # very short summary line.
        print(f"Backend exception: {type(e).__name__}({repr(e.args)})")
        # Then print it to the errlog.
        with open(_g.p_errlog, "a") as ferr:
            print("======= From backend =======", file=ferr)
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file=ferr)
            print_exc(file=ferr)
            print("\n\n", file=ferr)
