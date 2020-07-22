import sys
import json
from traceback import print_exc
from functools import wraps
from datetime import datetime
from pathlib import Path
from collections import namedtuple

import numpy as np

# Enable relative imports when invoked directly as __main__ by TopSpin.
# cf. PEP 366 and https://stackoverflow.com/a/54490918
if __name__ == "__main__" and __package__ is None:
    __package__ = "poptpy_backend"
    sys.path.insert(1, str(Path(__file__).parents[1].resolve()))
    __import__(__package__)

from .poptimise import nelder_mead, multid_search, pybobyqa_interface

optimiser = None  # Set this in frontend script ('edpy poptpy' in TopSpin)
routine_id = None
p_spectrum = None
p_optlog = None
p_poptpy = Path(__file__).parent.resolve()
tic = datetime.now()
spec_f1p = None
spec_f2p = None
Routine = namedtuple("Routine", "name pars lb ub init tol cf")


def deco_count(fn):
    """Function counter decorator."""
    @wraps(fn)
    def counter(*args, **kwargs):
        counter.calls += 1
        return fn(*args, **kwargs)
    counter.calls = 0
    return counter


def main():
    """
    Main routine.
    """
    # Load the routine and cost function.
    routine, cost_function = get_routine_cf(routine_id)

    # Check that the optimiser is set to a legitimate value.
    global optimiser
    # Choose the optimisation function. poptimise implements a PyBOBYQA
    # interface so that the returned result has the same attributes as our
    # other optimisers.
    optimfndict = {"nm": nelder_mead,
                   "mds": multid_search,
                   "bobyqa": pybobyqa_interface
                   }
    try:
        optimfn = optimfndict[optimiser.lower()]
    except KeyError:
        raise ValueError(f"Invalid optimiser {optimiser} specified.")

    # Scale the initial values and tolerances
    npars = len(routine.pars)
    scaleby = "bounds" if optimiser in ["nm", "mds"] else "tols"
    x0, _, _, xtol = scale(routine.init, routine.lb,
                           routine.ub, routine.tol, scaleby=scaleby)

    # Some logging
    with open(p_optlog, "a") as log:
        print("\n\n\n", file=log)
        print("=" * 40, file=log)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file=log)
        fmt = "{:25s} - {}"
        print(fmt.format("Routine name", routine.name), file=log)
        print(fmt.format("Optimisation parameters", routine.pars), file=log)
        print(fmt.format("Cost function", routine.cf), file=log)
        print(fmt.format("Initial values", routine.init), file=log)
        print(fmt.format("Lower bounds", routine.lb), file=log)
        print(fmt.format("Upper bounds", routine.ub), file=log)
        print(fmt.format("Tolerances", routine.tol), file=log)
        print(fmt.format("Optimisation algorithm", optimiser), file=log)
        print("", file=log)
        fmt = "{:^10s}  " * (npars + 1)
        print(fmt.format(*routine.pars, "cf"), file=log)
        print("-" * 12 * (npars + 1), file=log)

    # Get F1P/F2P parameters
    global spec_f1p, spec_f2p
    x, y = getpar("F1P"), getpar("F2P")
    if isinstance(x, float) and isinstance(y, float):  # 1D
        if x != 0 and y != 0:
            spec_f1p, spec_f2p = x, y
    elif isinstance(x, np.ndarray) and isinstance(y, np.ndarray):  # 2D
        if not np.array_equal(x, [0, 0]) and not np.array_equal(y, [0, 0]):
            spec_f1p, spec_f2p = x, y

    # Set up optimisation arguments
    optimargs = (cost_function, routine)
    # Carry out the optimisation
    opt_result = optimfn(acquire_nmr, x0, xtol, optimargs, plot=False)

    # Tell frontend script that the optimisation is done
    scaleby = "bounds" if optimiser in ["nm", "mds"] else "tols"
    best_values = unscale(opt_result.xbest, routine.lb,
                          routine.ub, routine.tol, scaleby=scaleby)
    print("optima: " + " ".join([str(i) for i in best_values]))

    # More logging
    toc = datetime.now()
    time_taken = str(toc - tic).split(".")[0]  # remove microseconds
    with open(p_optlog, "a") as log:
        print("", file=log)
        fmt = "{:27s} - {}"
        print(fmt.format("Best values found", best_values), file=log)
        print(fmt.format("Cost function at minimum", opt_result.fbest),
              file=log)
        print(fmt.format("Number of fevals", acquire_nmr.calls), file=log)
        print(fmt.format("Number of spectra ran", send_values.calls),
              file=log)
        print(fmt.format("Total time taken", time_taken), file=log)


def get_routine_cf(routine_id, p_routine_dir=None, p_cf_dir=None):
    """
    First finds the routine file and instantiates a Routine. Then finds the
    associated cost function script and exec's it.

    Arguments:
        routine_id (str)            : Name of the routine being used.
        p_routine_dir (pathlib.Path): Path to the folder containing the
                                      routines. Defaults to the "routines"
                                      directory in p_poptpy.
        p_cf_dir (pathlib.Path)     : Path to the folder containing the
                                      cost functions. Defaults to the
                                      "cost_functions" directory in p_poptpy.

    Returns:
        Tuple of (Routine, function).
    """
    # Load the routine.
    p_routine_dir = p_routine_dir or (p_poptpy / "routines")
    with open(p_routine_dir / routine_id, "rb") as f:
        routine = Routine(**json.load(f))

    # Load the cost function
    p_cf_dir = p_cf_dir or (p_poptpy / "cost_functions")
    cf_name = routine.cf
    p_cf_file = p_cf_dir / (cf_name + ".py")
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
    Evaluation of cost function for optimisation.
    Sends a signal to the frontend script to run an NMR acquisition using the
    scaled parameter values contained in x. Then, waits for the spectrum to be
    acquired and processed; and then calculates the cost function associated
    with the spectrum.
    If any of the values in x are out-of-bounds, this simply returns np.inf as
    the cost function.

    Arguments:
        x (ndarray of floats): values to be used in evaluation of cost
                               function, scaled to be between 0 and 1.
        optimargs (tuple)    : contains various parameters needed for other
                               tasks, like communication with frontend.

    Returns:
        float : value of the cost function.
    """
    scaleby = "bounds" if optimiser in ["nm", "mds"] else "tols"
    unscaled_val = unscale(x, routine.lb, routine.ub,
                           routine.tol, scaleby=scaleby)

    with open(p_optlog, "a") as log:
        # Enforce constraints on optimisation
        if np.any(unscaled_val < routine.lb) or \
                np.any(unscaled_val > routine.ub):
            cf_val = np.inf
            # Logging
            fmt = "{:^10.4f}  " * (len(x) + 1)
            print(fmt.format(*unscaled_val, cf_val), file=log)
            return cf_val

        # Print unscaled values, prompting frontend script to start acquisition
        send_values(unscaled_val)
        # Wait for acquisition to complete, then calculate cost function
        signal = input()      # frontend prints "done" here
        global p_spectrum
        p_spectrum = Path(input())  # path to the active spectrum
        if signal == "done":
            cf_val = cost_function()
            # Logging
            fmt = "{:^10.4f}  " * (len(x) + 1)
            print(fmt.format(*unscaled_val, cf_val), file=log)
            return cf_val
        else:
            raise ValueError(f"Invalid signal passed from frontend: {signal}")


@deco_count
def send_values(unscaled_val):
    """Print a list of unscaled values, which prompts frontend script to
    start acquisition.
    This needs to be a separate function so that we can decorate it.
    """
    print("values: " + " ".join([str(i) for i in unscaled_val]))


def scale(val, lb, ub, tol, scaleby="bounds"):
    """
    For scaleby="bounds", scales a set of values such that the lower and upper
    bounds for all variables are 0 and 1 respectively).

    For scaleby="tols", scales a set of values such that the tolerances for all
    variables are 0.03.

    Returns None if any of the values are outside the bounds.

    Arguments:
        val: list/array of float - the values to be scaled
        lb : list/array of float - the lower bounds
        ub : list/array of float - the upper bounds
        tol: list/array of float - the tolerances
        scaleby: string - Method to scale by. Either "bounds" or "tols".

    Returns:
        scaled_val: np.ndarray of float - the scaled values
        scaled_lb : np.ndarray of float - the scaled lower bounds
        scaled_ub : np.ndarray of float - the scaled upper bounds
        scaled_tol: np.ndarray of float - the scaled tolerances
    """
    if scaleby not in ["bounds", "tols"]:
        raise ValueError(f"Invalid argument scaleby={scaleby} given.")
    # Convert to ndarray
    val, lb, ub, tol = (np.array(i) for i in (val, lb, ub, tol))
    # Check if any are outside bounds
    if np.any(val < lb) or np.any(val > ub):
        return None
    # Scale them
    if scaleby == "bounds":
        scaled_val = (val - lb)/(ub - lb)
        scaled_lb = (lb - lb)/(ub - lb)  # all 0's
        scaled_ub = (ub - lb)/(ub - lb)  # all 1's
        scaled_tol = tol/(ub - lb)
    elif scaleby == "tols":
        scaled_val = (val - lb) * 0.03 / tol
        scaled_lb = (lb - lb) * 0.03 / tol   # all 0's
        scaled_ub = (ub - lb) * 0.03 / tol
        scaled_tol = tol * 0.03 / tol        # all 0.03's
    return scaled_val, scaled_lb, scaled_ub, scaled_tol


def unscale(scaled_val, orig_lb, orig_ub, orig_tol, scaleby="bounds"):
    """
    Unscales a set of scaled values to their original values.

    Arguments:
        scaled_val: list/array of float - the values to be unscaled
        orig_lb   : list/array of float - the original lower bounds
        orig_ub   : list/array of float - the original upper bounds
        orig_tol  : list/array of float - the original tolerances
        scaleby   : string - Method to scale by. Either "bounds" or "tols".

    Returns:
        np.ndarray of float - the unscaled values
    """
    if scaleby not in ["bounds", "tols"]:
        raise ValueError(f"Invalid argument scaleby={scaleby} given.")
    scaled_val, orig_lb, orig_ub, orig_tol = (np.array(i) for i in (scaled_val,
                                                                    orig_lb,
                                                                    orig_ub,
                                                                    orig_tol))
    if scaleby == "bounds":
        return orig_lb + (scaled_val * (orig_ub - orig_lb))
    elif scaleby == "tols":
        return (scaled_val * orig_tol / 0.03) + orig_lb

# ----------------------------------------
# Helper functions used in cost functions.
# ----------------------------------------


def _parse_bounds_string(b):
    """
    Parses the bounds strings "xf..yf", returning (xf, yf) as a tuple. If
    either xf or yf are not specified, returns None in their place.
    """
    try:
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
    except ValueError:
        raise ValueError(f"Invalid value {b} provided for bounds.")


def _ppm_to_point(shift, axis=None, p_spec=None):
    """
    Round a specific chemical shift to the nearest point in the spectrum.
    Note that this only works for 1D spectra!

    For unknown reasons, this does not correlate perfectly to the "index" that
    is displayed in TopSpin. However, the difference between the indices
    calculated here and the index in TopSpin is on the order of 1e-4 to 1e-3
    ppm. (More precisely, it's ca. 0.25 * SW / SI.)

    Arguments:
        shift (float)         : desired chemical shift.
        axis (int)            : axis along which to calculate this. For 1D
                                spectra this should be left as None. For 2D
                                spectra, axis=0 and axis=1 correspond to the
                                f1 and f2 dimensions respectively.
        p_spec (pathlib.Path) : Path to the folder of the desired spectrum.
                                Defaults to the spectrum being optimised, i.e.
                                the global variable p_spectrum.

    Returns:
        (int): the desired point. None if the chemical shift lies outside the
               spectral window.
    """
    p_spec = p_spec or p_spectrum
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


def get_fid(p_spec=None):
    """
    Returns the FID as a (complex) np.ndarray.
    Needs the global variable p_spectrum to be set.

    Note that this does *not* deal with the "group delay" at the beginning
    of the FID.

    Arguments:
        p_spec (pathlib.Path) : Path to the spectrum being optimised.

    Returns:
        (np.ndarray) Array containing the FID.
    """
    p_spec = p_spec or p_spectrum
    p_fid = p_spec.parents[1] / "fid"
    fid = np.fromfile(p_fid, dtype=np.int32)
    td = fid.size
    fid = fid.reshape(int(td/2), 2)
    fid = np.transpose(fid)
    # so now fid[0] is the real part, fid[1] the imaginary
    return fid[0] + (1j * fid[1])


def get_real_spectrum(bounds="", epno=None, p_spec=None):
    """
    Get the real spectrum. This function accounts for TopSpin's NC_PROC
    variable, scaling the spectrum intensity accordingly.

    Note that this function only works for 1D spectra. It does NOT work for 1D
    projections of 2D spectra. If you want to work with projections, you can
    use get_2d_spectrum() to get the full 2D spectrum, then manipulate it using
    numpy functions as appropriate. Examples can be found in the docs.

    The bounds parameter may be specified in the following formats:
       - between 5 and 8 ppm:   bounds="5..8"
       - greater than 9.3 ppm:  bounds="9.3.."
       - less than -2 ppm:      bounds="..-2"

    Arguments:
        bounds (str)          : String describing the region of interest. See
                                above for examples. If no bounds are provided,
                                uses the spectral bounds specified via 'dpl';
                                if these are not specified, defaults to the
                                whole spectrum.
        epno (list)           : [expno, procno] of spectrum of interest.
                                Defaults to the spectrum being optimised. Other
                                expnos/procnos are calculated relative to the
                                spectrum being optimised.
        p_spec (pathlib.Path) : Path to the spectrum being optimised.

    Returns:
        (np.ndarray) Array containing the spectrum or the desired section.
    """
    # Check whether user has specified epno
    if epno is not None:
        if len(epno) == 2:
            p_spec = p_spec or p_spectrum
            p_spec = p_spec.parents[2] / str(epno[0]) / "pdata" / str(epno[1])
        else:
            raise ValueError("Please provide a valid [expno, procno] "
                             "combination.")

    p_spec = p_spec or p_spectrum
    p_1r = p_spec / "1r"
    real_spec = np.fromfile(p_1r, dtype=np.int32)
    nc_proc = int(getpar("NC_proc", p_spec))
    real_spec = real_spec * (2 ** nc_proc)

    if bounds == "":
        if spec_f1p is None and spec_f2p is None:  # DPL not used
            return real_spec
        else:
            left, right = spec_f1p, spec_f2p
    else:
        right, left = _parse_bounds_string(bounds)

    # Get default bounds
    si = int(getpar("SI", p_spec))
    left_point, right_point = 0, si - 1
    # Then replace them if necessary
    if left is not None:
        left_point = _ppm_to_point(left, p_spec=p_spec)
    if right is not None:
        right_point = _ppm_to_point(right, p_spec=p_spec)

    return real_spec[left_point:right_point + 1]


def get_imag_spectrum(bounds="", epno=None, p_spec=None):
    """
    Get the imaginary spectrum. This function accounts for TopSpin's NC_PROC
    variable, scaling the spectrum intensity accordingly.

    Note that this function only works for 1D spectra. It does NOT work for 1D
    projections of 2D spectra. If you want to work with projections, you can
    use get_2d_spectrum() to get the full 2D spectrum, then manipulate it using
    numpy functions as appropriate. Examples can be found in the docs.

    The bounds parameter may be specified in the following formats:
       - between 5 and 8 ppm:   bounds="5..8"
       - greater than 9.3 ppm:  bounds="9.3.."
       - less than -2 ppm:      bounds="..-2"

    Arguments:
        bounds (str)          : String describing the region of interest. See
                                above for examples. If no bounds are provided,
                                uses the spectral bounds specified via 'dpl';
                                if these are not specified, defaults to the
                                whole spectrum.
        epno (list)           : [expno, procno] of spectrum of interest.
                                Defaults to the spectrum being optimised. Other
                                expnos/procnos are calculated relative to the
                                spectrum being optimised.
        p_spec (pathlib.Path) : Path to the spectrum being optimised.

    Returns:
        (np.ndarray) Array containing the spectrum or the desired section.
    """
    # Check whether user has specified epno
    if epno is not None:
        if len(epno) == 2:
            p_spec = p_spec or p_spectrum
            p_spec = p_spec.parents[2] / str(epno[0]) / "pdata" / str(epno[1])
        else:
            raise ValueError("Please provide a valid [expno, procno] "
                             "combination.")

    p_spec = p_spec or p_spectrum
    p_1i = p_spec / "1i"
    imag_spec = np.fromfile(p_1i, dtype=np.int32)
    nc_proc = int(getpar("NC_proc", p_spec))
    imag_spec = imag_spec * (2 ** nc_proc)

    if bounds == "":
        if spec_f1p is None and spec_f2p is None:  # DPL not used
            return imag_spec
        else:
            left, right = spec_f1p, spec_f2p
    else:
        right, left = _parse_bounds_string(bounds)

    # Get default bounds
    si = int(getpar("SI", p_spec))
    left_point, right_point = 0, si - 1
    # Then replace them if necessary
    if left is not None:
        left_point = _ppm_to_point(left, p_spec=p_spec)
    if right is not None:
        right_point = _ppm_to_point(right, p_spec=p_spec)

    return imag_spec[left_point:right_point + 1]


def get_2d_spectrum(f1_bounds="", f2_bounds="", epno=None, p_spec=None):
    """
    Get the doubly real part of a 2D spectrum. This function takes into account
    the NC_proc value in TopSpin's processing parameters.

    The f1_bounds and f2_bounds parameters may be specified in the following
    formats:
       - between 5 and 8 ppm:   bounds="5..8"
       - greater than 9.3 ppm:  bounds="9.3.."
       - less than -2 ppm:      bounds="..-2"

    Arguments:
        f1_bounds (str)       : String indicating f1 region of interest.
        f2_bounds (str)       : String indicating f2 region of interest.
        epno (list)           : [expno, procno] of spectrum of interest.
                                Defaults to the spectrum being optimised. Other
                                expnos/procnos are calculated relative to the
                                spectrum being optimised.
        p_spec (pathlib.Path) : Path to the spectrum being optimised.

    Returns:
        (np.ndarray) 2D array containing the spectrum or the desired section.
    """
    # Check whether user has specified epno
    if epno is not None:
        if len(epno) == 2:
            p_spec = p_spec or p_spectrum
            p_spec = p_spec.parents[2] / str(epno[0]) / "pdata" / str(epno[1])
        else:
            raise ValueError("Please provide a valid [expno, procno] "
                             "combination.")

    p_spec = p_spec or p_spectrum
    p_rr = p_spec / "2rr"

    # Check data type (TopSpin 3 int vs TopSpin 4 float)
    dtypp = getpar("dtypp", p_spec)
    if dtypp[0] == 0 and dtypp[1] == 0:  # TS3 data
        dt = "<" if np.all(getpar("bytordp", p_spec) == 0) else ">"
        dt += "i4"
    else:
        raise NotImplementedError("get_2d_spectrum(): "
                                  "float data not yet accepted")
    sp = np.fromfile(p_rr, dtype=np.dtype(dt))
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
        if spec_f1p is not None and spec_f2p is not None:  # DPL was used
            # f2p is lower than f1p.
            f1_bounds = f"{spec_f2p[0]}..{spec_f1p[0]}"
    if f2_bounds == "":
        if spec_f1p is not None and spec_f2p is not None:  # DPL was used
            f2_bounds = f"{spec_f2p[1]}..{spec_f1p[1]}"
    f1_lower, f1_upper = _parse_bounds_string(f1_bounds)
    f2_lower, f2_upper = _parse_bounds_string(f2_bounds)
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


def _get_acqu_par(par, p_acqus):
    """
    Obtains the value of an acquisition parameter.

    Note that pulse powers in dB (PLdB / SPdB) cannot be obtained using this
    function, as they are not stored in the acqus file.

    Arguments:
        par (str)              : Name of the acquisition parameter.
        p_acqus (pathlib.Path) : Path to the status acquisition file (this is
                                 'acqus' for 1D spectra and direct dimension of
                                 2D spectra, or 'acqu2s' for indirect dimension
                                 of 2D spectra).

    Returns:
        (float) Value of the acquisition parameter. None if the value is not a
                number, or if the parameter doesn't exist.
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

    Arguments:
        par (str)              : Name of the processing parameter.
        p_procs (pathlib.Path) : Path to the status processing file (this is
                                 'procs' for 1D spectra and direct dimension of
                                 2D spectra, or 'proc2s' for indirect dimension
                                 of 2D spectra).

    Returns:
        (float) value of the processing parameter. None if the value is not a
                number, or if the parameter doesn't exist.
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
    Obtains the value of an (acquisition or processing) parameter.
    Tries to search for an acquisition parameter first, then processing.

    Works on both 1D and 2D spectra. For parameters that are applicable to
    both dimensions of 2D spectra, getpar() returns a np.ndarray consisting of
    (f1_value, f2_value). Otherwise (for 1D spectra, or for 2D parameters which
    only apply to the direct dimension), getpar() returns a float.

    Arguments:
        par (str)             : Name of the parameter.
        p_spec (pathlib.Path) : Path to the folder of the desired spectrum.
                                Defaults to the spectrum being optimised, i.e.
                                the global variable p_spectrum.

    Returns:
        (float or np.ndarray) Value(s) of the requested parameter. None if the
            given parameter was not found.
    """
    p_spec = p_spec or p_spectrum

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
        optimiser = input()
        routine_id = input()
        p_spectrum = Path(input())
        p_optlog = p_spectrum.parents[1] / "poptpy.log"
        # Run main routine.
        main()
    except Exception as e:
        # Because the frontend is only reading one line at a time, there's
        # no point in printing the entire traceback. Thus we just print a
        # very short summary line.
        print(f"Backend exception: {type(e).__name__}({repr(e.args)})")
        # Then print it to the errlog.
        print("======= From backend =======", file=sys.stderr)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file=sys.stderr)
        raise  # This prints the full traceback to errlog.
