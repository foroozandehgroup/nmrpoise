# Check if this is being called from TopSpin try:
    ERRMSG("poptpy_be.py: Please run this script outside TopSpin!")
    EXIT()
except NameError:
    pass

import os
import sys
import pickle
import dill
import numpy as np
from scipy import optimize
from datetime import datetime

# TODO Determine minimum version of Python 3 on which this runs.
#      I have used os.path over pathlib, but if we switch to pathlib, then
#      this is >=3.4 at least.

# Obtain key information from frontend script
routine_id = input()
p_spectrum = input()
p_poptpy = input()

p_optlog = os.path.join(p_poptpy, "poptpy.log")
p_routines = os.path.join(p_poptpy, "routines")
p_costfunctions = os.path.join(p_poptpy, "cost_functions")


def main():
    """
    Main routine.
    """
    # Load the routine and cost function
    with open(os.path.join(p_routines, routine_id), "rb") as f:
        routine = pickle.load(f)
    with open(os.path.join(p_costfunctions, routine.cf), "rb") as f:
        cf = dill.load(f)
    # (possible) TODO: May want to check that the Routine and Cost_Function
    #                  objects are valid

    # Scale the initial values and tolerances
    x0 = scale(routine.init, routine.lb, routine.ub)
    xtol = np.array(routine.tol) / (np.array(routine.ub) -
                                    np.array(routine.lb))
    xatol_gm = np.prod(xtol)**(1/np.size(xtol))
    # TODO: Scipy's optimisers don't allow for an xatol vector -- there is no
    #       way to differentiate between different tolerances for different
    #       parameters. For now I have opted to use the geometric mean of the
    #       (scaled) xtol vector as the input to xatol. In order to change this
    #       behaviour we would need to change the actual optimiser, i.e. move
    #       away from scipy.

    # Some logging
    with open(p_optlog, "a") as log:
        now = datetime.now().strftime("%Y-%M-%D %H:%M:%S")
        print("\n\n", file=log)
        print(now, file=log)
        print("Starting optimisation of the following "
              "parameters: {}".format(routine.pars), file=log)
        print("Cost function used: {}".format(cf.name), file=log)
        print("Initial values used: {}".format(routine.init), file=log)
        print("xatol used: {}".format(xatol_gm), file=log)

    # Carry out the optimisation
    # TODO: allow user to select optimiser??? Or at least me?
    optimargs = [cf, routine.lb, routine.ub, p_spectrum, p_optlog]
    opt_result = optimize.minimize(acquire_nmr,
                                   x0,
                                   args=optimargs,
                                   method="Nelder-Mead",
                                   options={'xatol': xatol_gm,
                                            'fatol': np.inf,
                                            'disp': False})

    # Tell frontend script that the optimisation is done
    print("done")
    best_values = unscale(opt_result.x, routine.lb, routine.ub)
    print(" ".join([str(i) for i in best_values]))

    # More logging
    with open(p_optlog, "a") as log:
        print(opt_result, file=log)
        print("", file=log)
        print("Best values found: {}\n\n".format(best_values), file=log)


class Routine:
    def __init__(self, name, pars, lb, ub, init, tol, cf):
        self.name = name
        self.pars = pars
        self.lb = lb
        self.ub = ub
        self.init = init
        self.tol = tol
        self.cf = cf


class Cost_Function:
    def __init__(self, name, function):
        self.name = name
        self.function = function


def acquire_nmr(x, optimargs):
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
    # Unpack optimisation arguments
    cf, lb, ub, p_spectrum, p_optlog = optimargs
    unscaled_val = unscale(x, lb, ub)

    with open(p_optlog, "a") as log:
        # Log the values
        print("Evaluating cost function at: {}".format(unscaled_val), file=log)
        # Enforce constraints on optimisation
        if any(x < 0) or any(x > 1):
            print("Parameters out of bounds -- returning +inf", file=log)
            return np.inf

        # Print unscaled values, prompting frontend script to start acquisition
        print(" ".join([str(i) for i in unscaled_val]))

        # Wait for acquisition to complete, then calculate cost function
        signal = input()
        if signal == "done":
            cf_val = cf.function()
            print("    Value of cost function: {}".format(cf_val), file=log)
            return cf_val


def read_routine(routine_name):
    """
    Reads a routine from the p_routines subdirectory.

    Arguments:
        routine_name (str): Name of routine to be read in.

    Returns: Routine object.
    """
    path = os.path.join(p_routines, routine_name)
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


def ppm_to_point(shift):
    """
    Round a specific chemical shift to the nearest point in the spectrum.
    Needs the global variable p_spectrum to be set.

    Arguments:
        shift (float) : desired chemical shift.

    Returns:
        (int): the desired point. None if the chemical shift lies outside the
               spectral window.
    """
    si = get_proc_par("SI")
    o1p = get_acqu_par("O1") / get_acqu_par("SFO1")
    sw = get_acqu_par("SW")

    # Make sure it's within range
    highest_shift = o1p + 0.5*sw
    lowest_shift = o1p - 0.5*sw
    if shift > highest_shift or shift < lowest_shift:
        return None

    # Calculate the value
    spacing = (highest_shift - lowest_shift)/si
    x = round((shift - lowest_shift)/spacing)
    return int(si - x)


def get_fid():
    """
    Returns the FID as a (complex) np.ndarray.
    Needs the global variable p_spectrum to be set.

    Note that this does *not* deal with the "group delay" at the beginning
    of the FID.
    """
    p_fid = os.path.join(p_spectrum, "fid")
    fid = np.fromfile(p_fid, dtype=np.int32)
    td = fid.size
    fid = fid.reshape(int(td/2), 2)
    fid = np.transpose(fid)
    # so now fid[0] is the real part, fid[1] the imaginary
    return fid[0] + (1j * fid[1])


def get_real_spectrum(left=None, right=None):
    """
    Get the real spectrum. Needs the global variable p_spectrum to be set.
    Note that this function removes the effects of TopSpin's NC_PROC variable.

    Arguments:
        (optional) left (float) : chemical shift corresponding to beginning of
                                  the desired section
        (optional) right (float): chemical shift corresponding to end of
                                  the desired section
        If the argument left (or right) is not passed, then the array returned
        will stretch to the left (or right) end of the spectrum.

    Returns:
        (np.ndarray) Array containing the spectrum or the desired section.
    """
    p_1r = os.path.join(p_spectrum, "1r")
    real_spec = np.fromfile(p_1r, dtype=np.int32)
    nc_proc = int(get_proc_par("NC_proc"))
    real_spec = real_spec * (2 ** nc_proc)

    if left is None and right is None:  # bounds not specified
        return real_spec

    # Swap both bounds if they were both specified, but not in the right order
    if left is not None and right is not None and left < right:
        temp = right
        right = left
        left = temp

    # Get default bounds
    si = int(get_proc_par("SI"))
    leftn = 0
    rightn = si - 1
    # Then replace them if necessary
    if left is not None:
        leftn = ppm_to_point(left)
    if right is not None:
        rightn = ppm_to_point(right)

    return real_spec[leftn:rightn + 1]


def get_imag_spectrum(left=None, right=None):
    """
    Get the imaginary spectrum. Needs the global variable p_spectrum to be set.
    Note that this function removes the effects of TopSpin's NC_PROC variable.

    Arguments:
        (optional) left (float) : chemical shift corresponding to beginning of
                                  the desired section
        (optional) right (float): chemical shift corresponding to end of
                                  the desired section
        If the argument left (or right) is not passed, then the array returned
        will stretch to the left (or right) end of the spectrum.

    Returns:
        (np.ndarray) Array containing the spectrum or the desired section.
    """
    p_1i = os.path.join(p_spectrum, "1i")
    imag_spec = np.fromfile(p_1i, dtype=np.int32)
    nc_proc = int(get_proc_par("NC_proc"))
    imag_spec = imag_spec * (2 ** nc_proc)

    if left is None and right is None:  # bounds not specified
        return imag_spec

    # Swap both bounds if they were both specified, but not in the right order
    if left is not None and right is not None and left < right:
        temp = right
        right = left
        left = temp

    # Get default bounds
    si = int(get_proc_par("SI"))
    leftn = 0
    rightn = si - 1
    # Then replace them if necessary
    if left is not None:
        leftn = ppm_to_point(left)
    if right is not None:
        rightn = ppm_to_point(right)

    return imag_spec[leftn:rightn + 1]


def get_acqu_par(par):
    """
    Obtains the value of an acquisition parameter.
    Needs the global variable p_spectrum to be set.

    Arguments:
        par (str): Name of the acquisition parameter.

    Returns:
        (float) value of the acquisition parameter. None if the value is not a
                number, or if the parameter doesn't exist.
    """
    # Construct path to acqus file
    p_acqus = os.path.abspath(os.path.join(p_spectrum, "..", "..", "acqus"))

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


def get_proc_par(par):
    """
    Obtains the value of a processing parameter.
    Needs the global variable p_spectrum to be set.

    Arguments:
        par (str): Name of the processing parameter.

    Returns:
        (float) value of the processing parameter. None if the value is not a
                number, or if the parameter doesn't exist.
    """
    # Construct path to acqus file
    p_acqus = os.path.abspath(os.path.join(p_spectrum, "procs"))

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


def getpar(par):
    """
    Obtains the value of an (acquisition or processing) parameter.
    Tries to search for an acquisition parameter first, then processing.

    Arguments:
        par (str): Name of the parameter.

    Returns:
        (float) value of the parameter. None if the value is not a number,
                or if the parameter doesn't exist.
    """
    value = get_acqu_par(par)
    if value is None:
        value = get_proc_par(par)
    return value


if __name__ == "__main__":
    main()
