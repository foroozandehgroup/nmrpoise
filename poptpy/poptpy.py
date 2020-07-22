from __future__ import division, with_statement, print_function

import os
import re
import json
import subprocess
from datetime import datetime
from traceback import print_exc
from collections import namedtuple

from de.bruker.nmr.mfw.root.UtilPath import getTopspinHome
from de.bruker.nmr.prsc.dbxml.ParfileLocator import getParfileDirs


tshome = getTopspinHome()  # use tshome to avoid installer overwriting
p_poptpy = os.path.join(tshome, "exp/stan/nmr/py/user/poptpy_backend")
p_backend = os.path.join(p_poptpy, "backend.py")
p_routines = os.path.join(p_poptpy, "routines")
p_costfunctions = os.path.join(p_poptpy, "cost_functions")
p_opterr = os.path.join(p_poptpy, "poptpy_err.log")
p_python3 = "/usr/local/bin/python3"
Routine = namedtuple("Routine", "name pars lb ub init tol cf")

# SETTINGS

# AU programme for acquisition and processing.
# For 2D experiments use e.g. 'ZG\nXFB\nXCMD("apk2d")\nABS2'.
poptpy_au_text = 'ZG\nEFP\nAPBK\nQUIT'
# Optimisation algorithm to use.
# Choose between "nm", "mds", or "bobyqa". Case-insensitive.
optimiser = "nm"
# Create a new expno for each function evaluation if True.
# If False, all function evaluations are run on the same expno (default).
separate_expnos = False


def main():
    """
    Main routine.
    """
    # Make sure user has opened a dataset
    if CURDATA() is None:
        err_exit("Please select a dataset!")

    # Issue a warning if dataset is > 2D
    if GETACQUDIM() > 2:
        MSG("Warning: poptpy is only designed for 1D and 2D data.\n"
            "If you are sure you want to use it on this {}D dataset, press "
            "OK to dismiss this warning.".format(GETACQUDIM()))

    # Make folders if they don't exist
    for folder in [p_poptpy, p_routines, p_costfunctions]:
        if not os.path.isdir(folder):
            os.makedirs(folder)

    # Select optimisation routine
    routine_id = get_routine_id()

    # Create or read the Routine object
    if routine_id is None:  # New routine was requested
        routine = Routine(*get_new_routine_parameters())
        with open(os.path.join(p_routines, routine.name), "wb") as f:
            json.dump(routine._asdict(), f)
        routine_id = routine.name
    else:  # Saved routine was requested
        with open(os.path.join(p_routines, routine_id), "rb") as f:
            routine = Routine(**json.load(f))

    # Check that the Routine object is valid
    check_routine(routine)

    # Make sure that Python 3 executable can be found
    check_python3path()

    # Create the AU programme for acquisition
    create_au_prog()

    # Construct the path to the folder of the current spectrum.
    p_spectrum = make_p_spectrum()

    # Check that the backend script is intact
    if not os.path.isfile(p_backend):
        err_exit("Backend script not found. Please reinstall poptpy.")

    # Open the error log and keep it open throughout.
    # Closing it prematurely before the backend has finished writing to it WILL
    # lead to race conditions!
    with open(p_opterr, "a") as ferr:
        # We need to catch java.lang.Error so that cleanup can be performed
        # if the script is killed from within TopSpin. See #23.
        try:
            backend = subprocess.Popen([p_python3, '-u', p_backend],
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=ferr)
            # Pass key information to the backend script
            print(optimiser, file=backend.stdin)
            print(routine_id, file=backend.stdin)
            print(p_spectrum, file=backend.stdin)
            backend.stdin.flush()

            # Main loop, controlled by the lines printed by the backend.
            first_expno = True
            while True:
                # Read in what the backend has to say.
                line = backend.stdout.readline()
                # This line indicates that the optimisation has converged.
                if line.startswith("optima:"):
                    optima = line.split()[1:]
                    break
                # This line indicates a set of values for which the cost
                # function should be evaluated, i.e. an experiment should
                # be ran.
                elif line.startswith("values:"):
                    # Increment expno if it's not the first time.
                    if separate_expnos:
                        if not first_expno:
                            XCMD("iexpno")
                            RE_IEXPNO()
                        else:
                            first_expno = False
                    # Obtain the values and set them
                    values = line.split()[1:]
                    if len(values) != len(routine.pars):
                        raise RuntimeError("Invalid values passed from "
                                           "backend: '{}'".format(line))
                    for value, par in zip(values, routine.pars):
                        try:
                            float(value)
                        except ValueError:
                            raise RuntimeError("Invalid values passed from "
                                               "backend: '{}'".format(line))
                        else:
                            convert_name_and_putpar(par, value)
                    # Generate WaveMaker shapes if necessary
                    if pulprog_contains_wvm():
                        XCMD("wvm -q")
                    # Run acquisition and processing
                    XCMD("xau poptpy_au")
                    # Check whether acquisition is complete
                    if not acqu_done():
                        raise RuntimeError("Acquisition stopped prematurely. "
                                           "poptpy has been terminated.")
                    # Tell backend script it's done
                    print("done", file=backend.stdin)
                    print(make_p_spectrum(), file=backend.stdin)
                    backend.stdin.flush()
                # Otherwise it would be an error.
                # The entire main() routine in the backend is wrapped by a
                # try/except which catches all exceptions and propagates them
                # to the frontend by printing the traceback.
                elif line.startswith("Backend exception: "):
                    raise RuntimeError(line)
                else:
                    raise RuntimeError("Invalid message from backend: '{}'."
                                       "Please see error log for more "
                                       "information.".format(line))
        except RuntimeError as e:
            # Print the date/time and exception to ferr.
            print("======= From frontend =======", file=ferr)
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), file=ferr)
            print_exc(file=ferr)
            # Wait for the backend to finish before exiting the with block.
            backend.communicate()
            # Tell the error the immediate cause and exit
            err_exit("Error during acquisition loop:\n" + e.message)
        # cleanup code
        except Error:
            # Kill the backend process if it's still running.
            if backend.poll() is None:
                backend.terminate()
            raise

    # Delete the error log if it's empty
    if os.stat(p_opterr).st_size == 0:
        os.remove(p_opterr)

    # Process the optimal values found
    s = ""
    x = CURDATA()
    p_optlog = os.path.join(x[3], x[0], x[1], "poptpy.log")
    for par, optimum in zip(routine.pars, optima):
        s = s + "Optimal value for {}: {}\n".format(par, optimum)
        convert_name_and_putpar(par, optimum)
    s = s + "These values have been set in the current experiment.\n"
    s = s + "Detailed information can be found at: {}".format(p_optlog)
    MSG(s)
    EXIT()


class cst:
    """
    Constants used throughout the programme.
    """
    # TopSpin's internal codes for keypresses
    ENTER = -10
    ESCAPE = -27


def err_exit(error):
    """
    Shows an error message in TopSpin, then quits the Python script.

    Arguments:
        error (string): Error message to be displayed.

    Returns: None.
    """
    ERRMSG(title="poptpy", message=error)
    EXIT()


def list_files(path, ext=""):
    """
    Lists all files found in a directory, if it exists.

    Arguments:
        path (string) : Directory to be searched in.
        ext (string)  : Extension of files to be searched for.

    Returns:
        List containing filenames.
    """
    if os.path.isdir(path):
        if ext == "":
            return [i for i in os.listdir(path)
                    if os.path.isfile(os.path.join(path, i))]
        else:
            return [os.path.splitext(i)[0] for i in os.listdir(path)
                    if i.endswith(ext)
                    and os.path.isfile(os.path.join(path, i))]
    else:
        return []


def get_routine_id():
    """
    Interactively prompts the user to choose a routine.

    Arguments: None.

    Returns:
        None if a new routine is desired.
        string containing routine name if a saved routine is chosen.
    """
    # Check for existing saved routines
    saved_routines = list_files(p_routines)

    if saved_routines != []:  # Saved routines were found...
        # Check for existing routine passed as argument
        if len(sys.argv) > 1:
            if sys.argv[1] in saved_routines:
                return sys.argv[1]
            else:
                MSG("The saved routine {} was not found.".format(sys.argv[1]))

        x = SELECT(title="poptpy",
                   message="Do you want to use a saved routine?",
                   buttons=["Yes", "No"])

        if x in [0, cst.ENTER]:  # user pressed Yes or Enter
            s = ", ".join(saved_routines)
            y = INPUT_DIALOG(title="poptpy: available routines",
                             header="Available routines: " + s,
                             items=["Routine:"])

            if y is None:  # user closed the dialog
                EXIT()
            elif y[0] in saved_routines:
                return y[0]
            else:  # user wrote something, but it wasn't correct
                if y[0] != "":
                    MSG("The saved routine {} was not found. "
                        "Starting a new routine...".format(y[0]))
                return None
        elif x == 1:  # user pressed No
            return None
        else:  # user did something else, like Escape or close button
            EXIT()
    else:  # Saved routines were not found
        return None


def get_new_routine_parameters():
    """
    Prompts user for all the details needed for an optimisation.

    Arguments: None.

    Returns:
        A list of objects, consisting of (in order):
         - name          : string containing name of routine
         - pars          : list of experimental parameters to be optimised
         - lb            : list of lower bounds
         - ub            : list of upper bounds
         - init          : list of initial values
         - tol           : list of tolerances
         - cf            : string containing name of cost function
    """
    # Prompt for routine name.
    name = INPUT_DIALOG(title="poptpy: choose a name...",
                        header="Please choose a name to save this routine as:",
                        items=["Name:"])
    if name is None or name[0].strip() == "":
        EXIT()
    name = name[0].replace(".py", "").strip()

    # Prompt for parameters to be optimised.
    opt_pars = INPUT_DIALOG(title="poptpy: choose parameters...",
                            header=("Please select experimental parameters "
                                    "to be optimised (separated by commas or "
                                    "spaces):"),
                            items=["Parameters:"])
    # Quit if nothing is given
    if opt_pars is None or opt_pars[0].strip() == "":
        EXIT()
    opt_pars = opt_pars[0].replace(",", " ").split()
    opt_pars = [i for i in opt_pars if i]  # remove empty strings

    # Prompt for minimum, maximum, initial values, and tolerances..
    lbs = []
    ubs = []
    inits = []
    tols = []
    for i in opt_pars:
        settings = INPUT_DIALOG(title="poptpy: settings for {}".format(i),
                                header="Please choose the minimum value, "
                                       "maximum value, initial value, and "
                                       "tolerance for {}:".format(i),
                                items=["Minimum:", "Maximum:",
                                       "Initial value:", "Tolerance:"])
        if settings is None:
            EXIT()
        else:
            lbs.append(process_values(i, settings[0]))
            ubs.append(process_values(i, settings[1]))
            inits.append(process_values(i, settings[2]))
            tols.append(process_values(i, settings[3]))

    # Check if the values are sensible
    s = ""
    for par, lb, ub, init, tol in zip(opt_pars, lbs, ubs, inits, tols):
        if lb > ub:
            s = s + ("Please set the maximum value of {} to be larger "
                     "than the minimum value. "
                     "[Current values: min={}, max={}]\n").format(par, lb, ub)
        else:
            if init < lb or init > ub:
                s = s + ("Please set the initial value of {} to a value "
                         "to be between {} and {}. "
                         "[Current value: {}]\n").format(par, lb, ub, init)
            if tol > (ub - lb) or tol <= 0:
                s = s + ("Please set the tolerance of {} to a positive value "
                         "smaller than {}. "
                         "[Current value: {}]\n").format(par, (ub - lb), tol)
    if s:
        err_exit(s)

    # Prompt for cost function.
    # Search for existing cost functions
    saved_cfs = list_files(p_costfunctions, ext=".py")

    if saved_cfs == []:
        err_exit("No cost functions have been defined!\n"
                 "Please reinstall poptpy to get a default set, or define "
                 "your own cost function based on the documentation.")
    else:
        s = ", ".join(saved_cfs)
        x = INPUT_DIALOG(title="poptpy: choose a cost function...",
                         header="Available cost functions: " + s,
                         items=["Cost function:"])
        if x is None:  # user closed the dialog
            EXIT()
        elif x[0] in saved_cfs:
            cf = x[0]
        else:
            err_exit("Cost function {} was not found. Exiting...".format(x[0]))

    return [name, opt_pars, lbs, ubs, inits, tols, cf]


def check_routine(routine):
    """
    Checks that a Routine object is valid. Exits the programme if it isn't.

    Arguments:
        routine (Routine): the routine to be checked.

    Returns: None.
    """
    try:
        routine.name, routine.pars, routine.lb, routine.ub
        routine.init, routine.tol, routine.cf
    except AttributeError:
        err_exit("The routine file is invalid.\n"
                 "Please delete it and recreate it from within poptpy.")


def check_python3path():
    """
    Checks that the global variable p_python3 is set to a valid python3
    executable. Exits the programme if it isn't.

    Arguments: None.

    Returns: None.
    """
    try:
        subprocess.check_call([p_python3, "--version"])
    except subprocess.CalledProcessError:
        err_exit("The python3 executable was not found.\n"
                 "Please specify p_python3 in poptpy.py.")


def convert_name_and_getpar(name):
    """
    Obtains the value of an acquisition parameter. The parameter name is
    first converted into a format suitable for TopSpin's GETPAR() function.

    Arguments:
        name (str): input name, like "cnst2" or "pldb1".

    Returns:
        float: value of the input parameter.
    """
    # GETPAR() accepts: CNST 1, P 1, D 1, PLW 1, PLdB 1 (note small d), GPZ 1
    #                   SPW 1, SPdB 1, SPOFFS 1, SPOAL 1,
    #               but O1, O1P, SFO1 (note no space)
    params_with_space = ["CNST", "D", "P", "PLW", "PLDB", "PCPD",
                         "GPX", "GPY", "GPZ", "SPW", "SPDB", "SPOFFS",
                         "SPOAL", "L", "IN", "INP", "PHCOR"]
    ts_name = name.upper()
    ts_namel = ts_name.rstrip("1234567890")   # the word
    ts_namer = ts_name[len(ts_namel):]           # the number
    # Add a space if needed
    if ts_namel in params_with_space:
        ts_name = ts_namel + " " + ts_namer
    # Convert DB back to dB
    ts_name = ts_name.replace("PLDB", "PLdB").replace("SPDB", "SPdB")
    # Get the value and check that it's a float
    val = GETPAR(ts_name)
    try:
        val = float(val)
        return val
    except ValueError:
        err_exit("The acquisition parameter {} could not be found, "
                 "or does not have a numerical value.".format(name))


def convert_name_and_putpar(name, val):
    """
    Stores the value of an acquisition parameter. The parameter name is
    first converted into a format suitable for TopSpin's PUTPAR() function.

    Arguments:
        name (str): input name, like "cnst2" or "pldb1".
        val (int or float): value to be set.

    Returns: None.
    """
    # PUTPAR() accepts: CNST 1, P 1, D 1, PLW 1, PLdB 1 (note small d), GPZ 1
    #                   SPW 1, SPdB 1, SPOFFS 1, SPOAL 1,
    #               but O1, O1P, SFO1 (note no space)
    params_with_space = ["CNST", "D", "P", "PLW", "PLDB", "PCPD",
                         "GPX", "GPY", "GPZ", "SPW", "SPDB", "SPOFFS",
                         "SPOAL", "L", "IN", "INP", "PHCOR"]
    ts_name = name.upper()
    ts_namel = ts_name.rstrip("1234567890")   # the word
    ts_namer = ts_name[len(ts_namel):]           # the number
    # Add a space if needed
    if ts_namel in params_with_space:
        ts_name = ts_namel + " " + ts_namer
    # Convert DB back to dB
    ts_name = ts_name.replace("PLDB", "PLdB").replace("SPDB", "SPdB")
    # Convert the value to a float
    try:
        val = float(val)
        PUTPAR(ts_name, str(val))
    except ValueError:
        raise
        err_exit("The value {} for parameter {} "
                 "was invalid.".format(val, name))


def process_values(parname, input_string):
    """
    Does some processing on user input to allow familiar hacks, like
    entering 2m for a duration or 2k for 2048. Unfortunately for pulses
    2m = 2000 and for delays 2m = 0.002, so we also need to parse the
    parameter name.

    Arguments:
        parname (str): String containing the parameter name.
        input_string (str): The string entered by the user into the dialog box.

    Returns:
        float: The processed value, as a float.
    """
    pulse = 1e6 if parname.upper().rstrip("1234567890") == "P" else 1
    try:
        if input_string.endswith("k"):
            f = int(input_string[:-1])  # int only, can't have "2.5k"
            return 1024*f
        elif input_string.endswith("s"):
            f = float(input_string[:-1])
            return f*pulse
        elif input_string.endswith("m"):
            f = float(input_string[:-1])
            return f*1e-3*pulse
        elif input_string.endswith("u"):
            f = float(input_string[:-1])
            return f*1e-6*pulse
        else:
            f = float(input_string)
            return f
    except ValueError:
        err_exit("'{}' was not a valid input for {}. "
                 "Please try again.".format(input_string, parname))


def make_p_spectrum():
    """
    Constructs the path to the procno folder of the active spectrum.
    """
    x = CURDATA()
    p = os.path.join(x[3], x[0], x[1], "pdata", x[2])
    return p


def acqu_done():
    """
    Checks whether the current acquisition has been completed and returns
    True/False accordingly. Useful for stopping poptpy if acquisition is
    prematurely terminated (e.g. by 'stop').
    """
    # Check NS
    if GETPAR("NS") != GETPARSTAT("NS"):
        return False
    # Check indirect dimension TD for 2Ds
    if GETACQUDIM() > 1:
        if GETPAR("TD", axis=1) != GETPARSTAT("TD", axis=1):
            return False
    return True


def pulprog_contains_wvm():
    """
    Checks if the currently active pulse programme uses WaveMaker pulses.

    Returns: True if it does, False if it doesn't.
    """
    ppname = GETPAR("PULPROG")

    # Get path to the pulse programme text
    ppdirs = getParfileDirs(0)
    for ppdir in ppdirs:
        if ppname in os.listdir(ppdir):
            fname = os.path.join(ppdir, ppname)
            break

    # Search for lines containing WaveMaker directives
    wvm_rgx = re.compile(r"^\s*;[A-Za-z0-9]+:wvm:")
    with open(fname, "r") as file:
        for line in file:
            if re.search(wvm_rgx, line):
                return True
    return False


def create_au_prog():
    """
    Creates an AU programme for acquisition and processing in TopSpin's
    default directory, if it doesn't already exist.
    """
    p_acqau = os.path.join(tshome, "exp/stan/nmr/au/src/user/poptpy_au")
    f = open(p_acqau, "w")
    f.write(poptpy_au_text)
    f.close()


if __name__ == "__main__":
    main()
