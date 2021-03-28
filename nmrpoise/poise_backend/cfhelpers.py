"""
cfhelpers.py
------------

Script containing functions to read spectra, etc. which can be used in cost
functions.

SPDX-License-Identifier: GPL-3.0-or-later
"""

from pathlib import Path

import numpy as np

from .shared import _g


class CostFunctionError(Exception):
    """
    Custom exception class which can be raised *inside* a cost function in
    order to stop the optimisation immediately.

    For the Nelder-Mead and MDS optimisers, the optimisation will still return
    the best value found so far. For the BOBYQA optimiser, no value will be
    returned.

    If raised directly with ``CostFunctionError(str)``, the current iteration
    (i.e. the iteration on which it was raised) will *not* be included in the
    optimisation results. If you wish to include the current iteration, then
    pass the value of the cost function as the second parameter, viz.
    ``CostFunctionError(str, cf_val=1e6)``.

    Examples
    --------
    One might envision a scenario in which *any* value of the cost function
    below a certain threshold is considered 'good enough' to be the optimum.
    To obtain this effect, write a cost function with the following structure:

    >>>def cost_function():
    >>>    cf_val = foo()   # whatever calculation you want here
    >>>    if cf_val < threshold:
    >>>       raise CostFunctionError("Cost function was below threshold.",
    >>>                               cf_val=cf_val)
    >>>    return cf_val
    """
    def __init__(self,
                 message=("The cost function raised an error."),
                 cf_val=None):
        self.message = message
        self.cf_val = cf_val


def make_p_spec(path=None, expno=None, procno=None):
    """
    Constructs a |Path| object corresponding to the procno folder
    ``<path>/<expno>/pdata/<procno>``. If parameters are not passed, they are
    inherited from the currently active spectrum (``_g.p_spectrum``).

    Thus, for example, ``make_p_spec(expno=1, procno=1)`` returns a path to the
    spectrum with EXPNO 1 and PROCNO 1, but with the same name as the currently
    active spectrum.

    Parameters
    ----------
    path : str or |Path|, optional
        Path to the main folder of the spectrum (one level above the expno
        folders).
    expno : int, optional
    procno : int, optional

    Returns
    -------
    p_spec : |Path|
        Path pointing to the requested spectrum.
    """
    # this check is only needed for the unit tests, during normal usage it
    # should never be None
    if _g.p_spectrum is not None:
        default_procno = int(_g.p_spectrum.name)
        default_expno = int(_g.p_spectrum.parents[1].name)
        default_path = _g.p_spectrum.parents[2]
    # overwrite defaults with user-passed parameters
    if path is not None:
        path = Path(path)
    else:
        path = default_path
    expno = expno or default_expno
    procno = procno or default_procno
    return path / str(expno) / "pdata" / str(procno)


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
        raise ValueError(f"Invalid value {b} provided for bounds.") from None


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


def get1d_fid(remove_grpdly=True, p_spec=None):
    """
    Returns the FID as a |ndarray|.

    Parameters
    ----------
    remove_grpdly : bool, optional
        Whether to remove the group delay (to be precise, it is shifted to the
        end of the FID). Defaults to True.

    p_spec : |Path|, optional
        Path to the procno folder of interest. (The FID is taken from the expno
        folder two levels up.) Defaults to the currently active spectrum (i.e.
        ``_g.p_spectrum``).

    Returns
    -------
    |ndarray|
        Complex-valued array containing the FID.
    """
    p_spec = p_spec or _g.p_spectrum
    if getndim(p_spec=p_spec) != 1:
        raise ValueError("get1d_fid(): current spectrum is not 1D")
    p_fid = p_spec.parents[1] / "fid"
    fid = np.fromfile(p_fid, dtype=np.int32)
    td = fid.size
    fid = fid.reshape(int(td/2), 2)
    fid = np.transpose(fid)
    # so now fid[0] is the real part, fid[1] the imaginary
    complex_fid = fid[0] + (1j * fid[1])
    # Trim any extra points in the FID file (not sure why this happens, but it
    # could be because data is written as blocks of 1024 points)
    real_td = int(getpar("TD", p_spec=p_spec) / 2)
    complex_fid = complex_fid[0:real_td]
    # Remove group delay if necessary
    if remove_grpdly:
        complex_fid = np.roll(complex_fid,
                              -int(getpar("GRPDLY", p_spec=p_spec)))
    return complex_fid


def _get_1d(spec_fname, bounds="", p_spec=None):
    """
    Helper-helper function which does the real work in reading the spectrum.

    The interface is the same as get1d_real, but with an additional parameter
    spec_fname. This is a string that is either "1r" (for the real spectrum) or
    "1i" (for the imaginary spectrum).
    """
    p_spec = p_spec or _g.p_spectrum
    p_specdata = p_spec / spec_fname
    spec = np.fromfile(p_specdata, dtype=np.int32)
    nc_proc = int(getpar("NC_proc", p_spec))
    spec = spec * (2 ** nc_proc)

    # Handle an edge case where _g.spec_f1p and _g.spec_f2p can be ndarrays
    # (for a 1D spectrum they should be floats). This occurs when the spectrum
    # is 2D *before* the optimisation is started (i.e. when backend.py
    # initialises these values), and then is changed to 1D before the first
    # acquisition. (This used to happen in the dosy_opt.py script, which has
    # since been removed from POISE; however, keeping this code here won't
    # hurt.)
    if isinstance(_g.spec_f1p, np.ndarray):
        _g.spec_f1p = _g.spec_f1p[1]
    if isinstance(_g.spec_f2p, np.ndarray):
        _g.spec_f2p = _g.spec_f2p[1]
    # We don't need to check if they're equal to zero. If they are, then
    # backend.py will already have set the variables in _g to be None.
    # OK now we can proceed as normal.
    if bounds == "":
        if _g.spec_f1p is None and _g.spec_f2p is None:  # DPL not used
            return spec
        else:
            # set the bounds to F1P and F2P if they are not None.
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


def get1d_real(bounds="", p_spec=None):
    """
    Return the real spectrum as a |ndarray|. This function accounts for
    TopSpin's ``NC_PROC`` variable, scaling the spectrum intensity accordingly.

    Note that this function only works for 1D spectra. It does *not* work for
    1D projections of 2D spectra. If you want to work with projections, you can
    use `get2d_rr` to get the full 2D spectrum, then manipulate it using numpy
    functions as appropriate. A documented example can be found in the
    ``asaphsqc()`` function in ``costfunctions.py`` (commented out by default).

    The *bounds* parameter may be specified in the following formats:

     - between 5 and 8 ppm:  ``bounds="5..8"``  OR ``bounds=(5, 8)``
     - greater than 9.3 ppm: ``bounds="9.3.."`` OR ``bounds=(9.3, None)``
     - less than -2 ppm:     ``bounds="..-2"``  OR ``bounds=(None, -2)``

    Parameters
    ----------
    bounds : str or tuple, optional
        String or tuple describing the region of interest. See above for
        examples. If no bounds are provided, uses the ``F1P`` and ``F2P``
        processing parameters, which can be specified via ``dpl``. If these are
        not specified, defaults to the whole spectrum.
    p_spec : |Path|, optional
        Path to the procno folder of interest. Defaults to the currently active
        spectrum (i.e. ``_g.p_spectrum``).

    Returns
    -------
    |ndarray|
        Array containing the spectrum or the desired section of it (if bounds
        were specified).
    """
    if getndim(p_spec=p_spec) != 1:
        raise ValueError("get1d_real(): current spectrum is not 1D")
    return _get_1d(spec_fname="1r", bounds=bounds, p_spec=p_spec)


def get1d_imag(bounds="", p_spec=None):
    """
    Same as `get1d_real`, except that it reads the imaginary spectrum.
    """
    if getndim(p_spec=p_spec) != 1:
        raise ValueError("get1d_imag(): current spectrum is not 1D")
    return _get_1d(spec_fname="1i", bounds=bounds, p_spec=p_spec)


def _get_2d(spec_fname, f1_bounds="", f2_bounds="", p_spec=None):
    """
    Helper-helper function which does the real work in reading the spectrum.

    The interface is the same as get2d_rr, but with an additional parameter
    spec_fname. This is a string that is either "2rr", "2ri", "2ir", or "2ii".
    """
    p_spec = p_spec or _g.p_spectrum
    p_specdata = p_spec / spec_fname

    # Check data type (TopSpin 3 int vs TopSpin 4 float)
    dtypp = getpar("dtypp", p_spec)
    if dtypp[0] == 0 and dtypp[1] == 0:  # TS3 data
        dt = "<" if np.all(getpar("bytordp", p_spec) == 0) else ">"
        dt += "i4"
    else:
        raise NotImplementedError("_get_2d: "
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


def get2d_rr(f1_bounds="", f2_bounds="", p_spec=None):
    """
    Return the real part of the 2D spectrum (the "RR" quadrant) as a 2D
    |ndarray|. This function takes into account the ``NC_PROC`` value in
    TopSpin's processing parameters.

    The *f1_bounds* and *f2_bounds* parameters may be specified in the
    following formats:

     - between 5 and 8 ppm:  ``f1_bounds="5..8"``  OR ``f1_bounds=(5, 8)``
     - greater than 9.3 ppm: ``f1_bounds="9.3.."`` OR ``f1_bounds=(9.3, None)``
     - less than -2 ppm:     ``f1_bounds="..-2"``  OR ``f1_bounds=(None, -2)``

    Parameters
    ----------
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
    p_spec : |Path|, optional
        Path to the procno folder of interest. Defaults to the currently active
        spectrum (i.e. ``_g.p_spectrum``).

    Returns
    -------
    |ndarray|
        2D array containing the spectrum or the desired section of it (if
        *f1_bounds* or *f2_bounds* were specified).
    """
    if getndim(p_spec=p_spec) != 2:
        raise ValueError("get2d_rr(): current spectrum is not 2D")
    return _get_2d(spec_fname="2rr",
                   f1_bounds=f1_bounds,
                   f2_bounds=f2_bounds,
                   p_spec=p_spec)


def get2d_ri(f1_bounds="", f2_bounds="", p_spec=None):
    """
    Same as `get2d_rr`, except that it reads the '2ri' file.
    """
    if getndim(p_spec=p_spec) != 2:
        raise ValueError("get2d_ri(): current spectrum is not 2D")
    return _get_2d(spec_fname="2ri",
                   f1_bounds=f1_bounds,
                   f2_bounds=f2_bounds,
                   p_spec=p_spec)


def get2d_ir(f1_bounds="", f2_bounds="", p_spec=None):
    """
    Same as `get2d_rr`, except that it reads the '2ir' file.
    """
    if getndim(p_spec=p_spec) != 2:
        raise ValueError("get2d_ir(): current spectrum is not 2D")
    return _get_2d(spec_fname="2ir",
                   f1_bounds=f1_bounds,
                   f2_bounds=f2_bounds,
                   p_spec=p_spec)


def get2d_ii(f1_bounds="", f2_bounds="", p_spec=None):
    """
    Same as `get2d_rr`, except that it reads the '2ii' file.
    """
    if getndim(p_spec=p_spec) != 2:
        raise ValueError("get2d_ii(): current spectrum is not 2D")
    return _get_2d(spec_fname="2ii",
                   f1_bounds=f1_bounds,
                   f2_bounds=f2_bounds,
                   p_spec=p_spec)


def _get_acqu_par(par, p_acqus):
    """
    Obtains the value of an acquisition parameter.

    Note that pulse powers in dB (PLdB / SPdB) cannot be obtained using this
    function, as they are not stored in the acqus file.

    Parameters
    ----------
    par : str
        Name of the acquisition parameter.
    p_acqus : |Path|
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
    list_params = ("AMP AMPCOIL BWFAC CAGPARS CNST CPDPRG D FCUCHAN"
                   " FN_INDIRECT FS GPNAM GPX GPY GPZ HGAIN HPMOD IN INF INP"
                   " INTEGFAC L MULEXPNO P PACOIL PCPD PEXSEL PHCOR PL PLW"
                   " PLWMAX PRECHAN PROBINPUTS RECCHAN RECPRE RECPRFX RECSEL"
                   " RSEL S SELREC SP SPNAM SPOAL SPOFFS SPPEX SPW SUBNAM"
                   " SWIBOX TD_INDIRECT TE_STAB TL TOTROT XGAIN").split()
    # Get the parameter
    if (parr != "") and (parl in list_params):  # e.g. cnst2
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
    p_procs : |Path|
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
    Obtains the value of a numeric (acquisition or processing) parameter.
    Non-numeric parameters (i.e. strings) are not currently accessible! Works
    for both 1D and 2D spectra (see return type below), but nothing higher.

    Parameters
    ----------
    par : str
        Name of the parameter.
    p_spec : |Path|, optional
        Path to the procno folder of interest. Defaults to the currently active
        spectrum (i.e. ``_g.p_spectrum``).

    Returns
    -------
    float or |ndarray|
        Value(s) of the requested parameter. None if the given parameter was
        not found.

        For parameters that exist for both dimensions of 2D spectra, getpar()
        returns an ndarray consisting of (f1_value, f2_value).  Otherwise (for
        1D spectra, or for 2D parameters which only apply to the direct
        dimension), getpar() returns a float.
    """
    p_spec = p_spec or _g.p_spectrum

    # Figure out the number of dimensions.
    ndim = getndim(p_spec=p_spec)
    if ndim == 1:
        # Hardcode DW and AQ as these aren't stored in acqus file. Note that
        # DW is in us and AQ in s, as is conventionally displayed in TopSpin.
        if par.upper() == "DW":
            return 1000000 / (2 * getpar("SW_h", p_spec))
        elif par.upper() == "AQ":
            return getpar("TD", p_spec) / (2 * getpar("SW_h", p_spec))

        acq = _get_acqu_par(par, p_spec.parents[1] / "acqus")
        if acq is not None:
            return acq
        else:
            return _get_proc_par(par, p_spec / "procs")
    elif ndim == 2:
        # Hardcode DW and AQ as these aren't stored in acqus file. Note that
        # DW only refers to the direct dimension. AQ returns a tuple.
        if par.upper() == "DW":
            return 1000000/(2 * getpar("SW_h", p_spec)[1])
        elif par.upper() == "AQ":
            return getpar("TD", p_spec) / (2 * getpar("SW_h", p_spec))
        # Try to get acquisition parameters first.
        acq_f1 = _get_acqu_par(par, p_spec.parents[1] / "acqu2s")
        acq_f2 = _get_acqu_par(par, p_spec.parents[1] / "acqus")
        # If both were found, return them as an nparray
        if acq_f1 is not None and acq_f2 is not None:
            return np.array([acq_f1, acq_f2])
        # If only f2 value was found, return it
        elif acq_f2 is not None:
            return acq_f2
        # If reached here, then means that acquisition parameter was not found.
        # Try to get processing parameters.
        proc_f1 = _get_proc_par(par, p_spec / "proc2s")
        proc_f2 = _get_proc_par(par, p_spec / "procs")
        # If both were found, return them as an nparray
        if proc_f1 is not None and proc_f2 is not None:
            return np.array([proc_f1, proc_f2])
        # If only f2 value was found, return it. In fact, based on the test
        # data, this will never be the case: every parameter inside procs is
        # also found inside proc2s. So this code is technically unreachable.
        elif proc_f2 is not None:
            return proc_f2
        # If reached here, neither were found, so return None.
        return None
    else:
        raise ValueError("getpar() only works for 1D and 2D spectra.")


def getndim(p_spec=None):
    """
    Obtains the dimensionality of the spectrum, i.e. the status value of
    PARMODE, plus one (becaus PARMODE is 0 for 1D spectra, etc.)

    Parameters
    ----------
    p_spec : |Path|, optional
        Path to the procno folder of interest. Defaults to the currently active
        spectrum (i.e. ``_g.p_spectrum``).

    Returns
    -------
    int
        Dimensionality of the spectrum.
    """
    p_spec = p_spec or _g.p_spectrum
    p_acqus = p_spec.parents[1] / "acqus"
    # Note that getpar() itself calls getndim(), so we call _get_acqu_par()
    # here instead of getpar() to avoid an infinite loop.
    bruker_ndim = _get_acqu_par("PARMODE", p_acqus)
    return int(bruker_ndim) + 1


def getnfev():
    """
    Returns the number of NMR spectra evaluated so far. This will be equal to 1
    (not 0) the first time the cost function is called, since the cost function
    is only called after the NMR spectrum has been acquired.
    """
    return _g.nfev


def log(*args):
    """
    Prints something to the poise.log file.

    If this is called from inside a cost function, the text is printed *before*
    the cost function is evaluated, so will appear above the corresponding
    function evaluation.

    Parameters
    ----------
    args
        The arguments that ``log()`` takes are exactly the same as those of
        ``print()``.

    Returns
    -------
    None
    """
    with open(_g.p_optlog, 'a') as fp:
        print(*args, file=fp)
