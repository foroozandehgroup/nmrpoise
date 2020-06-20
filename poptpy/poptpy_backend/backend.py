import sys
import pickle
from traceback import print_exc
from functools import wraps
from datetime import datetime
from pathlib import Path

import numpy as np

# Enable relative imports when invoked directly as __main__ by TopSpin.
# cf. PEP 366 and https://stackoverflow.com/a/54490918
if __name__ == "__main__" and __package__ is None:
    __package__ = "poptpy_backend"
    sys.path.insert(1, str(Path(__file__).parents[1].resolve()))
    __import__(__package__)

from .poptimise import nelder_mead

routine_id = None
p_spectrum = None
p_optlog = None
p_poptpy = Path(__file__).parent.resolve()
tic = datetime.now()
p_routines = p_poptpy / "routines"
p_costfunctions = p_poptpy / "cost_functions"
spec_f1p = None
spec_f2p = None


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
    # Load the routine
    with open(p_routines / routine_id, "rb") as f:
        routine = pickle.load(f)
    # Load the cost function
    cost_function = get_cf_function(routine.cf)

    # Scale the initial values and tolerances
    npars = len(routine.pars)
    x0 = scale(routine.init, routine.lb, routine.ub)
    xtol = np.array(routine.tol) / (np.array(routine.ub) -
                                    np.array(routine.lb))

    # Some logging
    with open(p_optlog, "a") as log:
        print("\n\n\n", file=log)
        print("=" * 40, file=log)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file=log)
        fmt = "{:25s} - {}"
        print(fmt.format("Optimisation parameters", routine.pars), file=log)
        print(fmt.format("Cost function", routine.cf), file=log)
        print(fmt.format("Initial values", routine.init), file=log)
        print("", file=log)
        fmt = "{:^10s}  " * (npars + 1)
        print(fmt.format(*routine.pars, "cf"), file=log)
        print("-" * 12 * (npars + 1), file=log)

    # Get F1P/F2P parameters
    x, y = getpar("F1P"), getpar("F2P")
    if x != 0 and y != 0 and x > y:
        # Need to declare as global because we are assigning to the variable.
        global spec_f1p, spec_f2p
        spec_f1p, spec_f2p = x, y

    # Carry out the optimisation
    optimargs = (cost_function, routine.lb, routine.ub, p_spectrum, p_optlog)
    opt_result = nelder_mead(acquire_nmr, x0, xtol, optimargs, plot=False)

    # Tell frontend script that the optimisation is done
    print("done")
    best_values = unscale(opt_result.xbest, routine.lb, routine.ub)
    print(" ".join([str(i) for i in best_values]))

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


class Routine:
    def __init__(self, name, pars, lb, ub, init, tol, cf):
        self.name = name
        self.pars = pars
        self.lb = lb
        self.ub = ub
        self.init = init
        self.tol = tol
        self.cf = cf


def get_cf_function(cf_name):
    """
    Finds the cost function script and exec's it, returning the function
    defined inside it.
    """
    p_cf = p_costfunctions / (cf_name + ".py")
    ld = {}
    exec(open(p_cf).read(), globals(), ld)
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
    return cost_function


@deco_count
def acquire_nmr(x, cost_function, lb, ub, p_spectrum, p_optlog):
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
    unscaled_val = unscale(x, lb, ub)

    with open(p_optlog, "a") as log:
        # Enforce constraints on optimisation
        if any(x < 0) or any(x > 1):
            cf_val = np.inf
            # Logging
            fmt = "{:^10.4f}  " * (len(x) + 1)
            print(fmt.format(*unscaled_val, cf_val), file=log)
            return cf_val

        # Print unscaled values, prompting frontend script to start acquisition
        send_values(unscaled_val)
        # Wait for acquisition to complete, then calculate cost function
        signal = input()
        if signal == "done":
            cf_val = cost_function()
            # Logging
            fmt = "{:^10.4f}  " * (len(x) + 1)
            print(fmt.format(*unscaled_val, cf_val), file=log)
            return cf_val
        else:
            raise ValueError("Incorrect signal passed from frontend: "
                             "{}".format(signal))


@deco_count
def send_values(unscaled_val):
    """Print a list of unscaled values, which prompts frontend script to
    start acquisition.
    This needs to be a separate function so that we can decorate it.
    """
    print("values: " + " ".join([str(i) for i in unscaled_val]))


def read_routine(routine_name, p_rout=None):
    """
    Reads a routine from the p_routines subdirectory.

    Arguments:
        routine_name (str)   : Name of routine to be read in.
        p_rout (pathlib.Path): Path to the routine folder. Defaults to the
                               global variable p_routines.

    Returns: Routine object.
    """
    p_rout = p_rout or p_routines
    path = p_rout / routine_name
    with open(path, "rb") as f:
        routine = pickle.load(f)
    return routine


def scale(val, lb, ub):
    """
    Scales a set of values to between 0 and 1 (which are the lower and upper
    optimisation bounds respectively). Returns None if any of the values are
    outside the bounds.

    Arguments:
        val: list/array of float - the values to be scaled
        lb : list/array of float - the lower bounds
        ub : list/array of float - the upper bounds

    Returns:
        np.ndarray of float - the scaled values
    """
    val = np.array(val)
    lb = np.array(lb)
    ub = np.array(ub)
    scaled_val = (val - lb)/(ub - lb)
    if np.any(scaled_val < 0) or np.any(scaled_val > 1):
        return None
    return scaled_val


def unscale(scaled_val, lb, ub):
    """
    Unscales a set of scaled values to their original values.

    Arguments:
        scaled_val: list/array of float - the values to be unscaled
        lb        : list/array of float - the lower bounds
        ub        : list/array of float - the upper bounds

    Returns:
        np.ndarray of float - the unscaled values
    """
    scaled_val = np.array(scaled_val)
    lb = np.array(lb)
    ub = np.array(ub)
    return lb + scaled_val*(ub - lb)

# ----------------------------------------
# Helper functions used in cost functions.
# ----------------------------------------


def ppm_to_point(shift, p_spec=None):
    """
    Round a specific chemical shift to the nearest point in the spectrum.

    For unknown reasons, this does not correlate perfectly to the "index" that
    is displayed in TopSpin. However, the difference between the indices
    calculated here and the index in TopSpin is on the order of 1e-4 to 1e-3
    ppm. (More precisely, it's ca. 0.25 * SW / SI.)

    Arguments:
        shift (float)         : desired chemical shift.
        p_spec (pathlib.Path) : Path to the folder of the desired spectrum.
                                Defaults to the spectrum being optimised, i.e.
                                the global variable p_spectrum.

    Returns:
        (int): the desired point. None if the chemical shift lies outside the
               spectral window.
    """
    p_spec = p_spec or p_spectrum
    si = get_proc_par("SI", p_spec)
    o1p = get_acqu_par("O1", p_spec) / get_acqu_par("SFO1", p_spec)
    sw = get_acqu_par("SW", p_spec)

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


def get_real_spectrum(left=None, right=None, epno=None, p_spec=None):
    """
    Get the real spectrum. This function accounts for TopSpin's NC_PROC
    variable, scaling the spectrum intensity accordingly.

    Arguments:
        left (float)          : chemical shift corresponding to beginning of
                                the desired section. Defaults to the maximum
                                of the spectrum.
        right (float)         : chemical shift corresponding to end of the
                                desired section. Defaults to the minimum of the
                                spectrum.
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
            p_spec = p_spec.parents[2] / str(epno[0]) / "pdata" / str(epno[1])
        else:
            raise ValueError("Please provide a valid [expno, procno] "
                             "combination.")

    p_spec = p_spec or p_spectrum
    p_1r = p_spec / "1r"
    real_spec = np.fromfile(p_1r, dtype=np.int32)
    nc_proc = int(get_proc_par("NC_proc", p_spec))
    real_spec = real_spec * (2 ** nc_proc)

    if left is None and right is None:  # bounds not specified
        if spec_f1p is None and spec_f2p is None:  # DPL not used
            return real_spec
        else:
            left, right = spec_f1p, spec_f2p

    # Swap both bounds if they were both specified, but not in the right order
    if left is not None and right is not None and left < right:
        left, right = right, left

    # Get default bounds
    si = int(get_proc_par("SI", p_spec))
    left_point, right_point = 0, si - 1
    # Then replace them if necessary
    if left is not None:
        left_point = ppm_to_point(left, p_spec)
    if right is not None:
        right_point = ppm_to_point(right, p_spec)

    return real_spec[left_point:right_point + 1]


def get_imag_spectrum(left=None, right=None, epno=None, p_spec=None):
    """
    Get the imaginary spectrum. This function accounts for TopSpin's NC_PROC
    variable, scaling the spectrum intensity accordingly.

    Arguments:
        left (float)          : chemical shift corresponding to beginning of
                                the desired section. Defaults to the maximum
                                of the spectrum.
        right (float)         : chemical shift corresponding to end of the
                                desired section. Defaults to the minimum of the
                                spectrum.
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
            p_spec = p_spec.parents[2] / str(epno[0]) / "pdata" / str(epno[1])
        else:
            raise ValueError("Please provide a valid [expno, procno] "
                             "combination.")

    p_spec = p_spec or p_spectrum
    p_1i = p_spec / "1i"
    imag_spec = np.fromfile(p_1i, dtype=np.int32)
    nc_proc = int(get_proc_par("NC_proc", p_spec))
    imag_spec = imag_spec * (2 ** nc_proc)

    if left is None and right is None:  # bounds not specified
        if spec_f1p is None and spec_f2p is None:  # DPL not used
            return imag_spec
        else:
            left, right = spec_f1p, spec_f2p

    # Swap both bounds if they were both specified, but not in the right order
    if left is not None and right is not None and left < right:
        left, right = right, left

    # Get default bounds
    si = int(get_proc_par("SI", p_spec))
    left_point, right_point = 0, si - 1
    # Then replace them if necessary
    if left is not None:
        left_point = ppm_to_point(left, p_spec)
    if right is not None:
        right_point = ppm_to_point(right, p_spec)

    return imag_spec[left_point:right_point + 1]


def get_acqu_par(par, p_spec=None):
    """
    Obtains the value of an acquisition parameter.

    Note that pulse powers in dB (PLdB / SPdB) cannot be obtained using this
    function, as they are not stored in the acqus file.

    Arguments:
        par (str)             : Name of the acquisition parameter.
        p_spec (pathlib.Path) : Path to the folder of the desired spectrum.
                                Defaults to the spectrum being optimised, i.e.
                                the global variable p_spectrum.

    Returns:
        (float) value of the acquisition parameter. None if the value is not a
                number, or if the parameter doesn't exist.
    """
    p_spec = p_spec or p_spectrum

    # Construct path to acqus file
    p_acqus = p_spec.parents[1] / "acqus"

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
                if line.upper().startswith("##${}=".format(parl)):
                    break
            # Grab the values and put them in a list
            s = ""
            line = file.readline()
            while not line.startswith("##"):  # read until the next parameter
                s = s + line + " "
                line = file.readline()
            # Pick out the desired value and return it if it's a float
            values = s.split()
            try:
                value = float(values[int(parr)])
                return value
            except ValueError:
                return None
    else:                                             # e.g. sfo1 or rga
        with open(p_acqus, "r") as file:
            for line in file:
                if line.upper().startswith("##${}=".format(par)):
                    try:
                        value = float(line.split()[-1].strip())
                        return value
                    except ValueError:
                        return None


def get_proc_par(par, p_spec=None):
    """
    Obtains the value of a processing parameter.

    Arguments:
        par (str)             : Name of the processing parameter.
        p_spec (pathlib.Path) : Path to the folder of the desired spectrum.
                                Defaults to the spectrum being optimised, i.e.
                                the global variable p_spectrum.

    Returns:
        (float) value of the processing parameter. None if the value is not a
                number, or if the parameter doesn't exist.
    """
    p_spec = p_spec or p_spectrum

    # Construct path to procs file
    p_acqus = p_spec / "procs"

    # Capitalise and remove any spaces from par
    par = par.upper()
    if len(par.split()) > 1:
        par = "".join(par.split())

    # Get the value (for processing parameters there aren't any lists like
    # CNST/D/P)
    with open(p_acqus, "r") as file:
        for line in file:
            if line.upper().startswith("##${}=".format(par)):
                try:
                    value = float(line.split()[-1].strip())
                    return value
                except ValueError:
                    return None


def getpar(par, p_spec=None):
    """
    Obtains the value of an (acquisition or processing) parameter.
    Tries to search for an acquisition parameter first, then processing.

    Arguments:
        par (str)             : Name of the parameter.
        p_spec (pathlib.Path) : Path to the folder of the desired spectrum.
                                Defaults to the spectrum being optimised, i.e.
                                the global variable p_spectrum.

    Returns:
        (float) value of the parameter. None if the value is not a number,
                or if the parameter doesn't exist.
    """
    # The docstring is 14 lines. The code is 2 lines. *rolls eyes*
    p_spec = p_spec or p_spectrum
    return get_acqu_par(par, p_spec) or get_proc_par(par, p_spec)


if __name__ == "__main__":
    # All errors in main() must be propagated back to the frontend so that
    # timely feedback can be provided to the user. The frontend is responsible
    # for the error logging.
    try:
        # Set global variables by reading in input from frontend.
        routine_id = input()
        p_spectrum = Path(input())
        p_optlog = p_spectrum.parents[1] / "poptpy.log"
        # Run main routine.
        main()
    except Exception as e:
        # Because the frontend is only reading one line at a time, there's
        # no point in printing the entire traceback. Thus we just print a
        # very short summary line.
        print("Backend exception: {}({!r})".format(type(e).__name__,
                                                   e.args))
        raise  # Prints the full traceback to errlog.
