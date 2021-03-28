"""
poise.py
--------

Parameter Optimisation by Iterative Spectral Evaluation

Frontend Python script that runs in TopSpin. Type `poise -h` into the TopSpin
command line for help, or visit `https://foroozandehgroup.github.io/nmrpoise`
for a more thorough introduction.

SPDX-License-Identifier: GPL-3.0-or-later
"""

from __future__ import division, with_statement, print_function

import os
import re
import json
import subprocess
import argparse
from datetime import datetime
from traceback import print_exc
from collections import namedtuple

from de.bruker.nmr.mfw.root.UtilPath import getTopspinHome
from de.bruker.nmr.prsc.dbxml.ParfileLocator import getParfileDirs

tshome = getTopspinHome()
p_poise = os.path.join(tshome, "exp/stan/nmr/py/user/poise_backend")
p_backend = os.path.join(p_poise, "backend.py")
p_routines = os.path.join(p_poise, "routines")
p_python3 = r"/usr/local/bin/python"
Routine = namedtuple("Routine", "name pars lb ub init tol cf au")


def main(args):
    """
    Main routine.

    Parameters
    ---------
    args (argparse.Namespace)
        Namespace object returned by parser.parse_args().

    Returns
    -------
    None
    """
    # Check that the folders are valid
    for folder in [p_poise, p_routines]:
        if not os.path.isdir(folder):
            os.makedirs(folder)
    # Check that cost functions folder actually has some cost functions
    _cfs = detect_costfunctions()
    if len(_cfs) == 0:
        err_exit("No cost functions were found. Please define a cost function "
                 ", or reinstall poise to obtain the defaults.")

    # Select an optimisation routine.
    saved_routines = list_files(p_routines, ext=".json")
    # If routine was specified on command-line, check that there actually is a
    # routine with that name.
    if args.routine is not None:
        if args.routine in saved_routines:
            routine_id = args.routine
            routine = load_routine(routine_id)
            prompt_run = False
        else:
            err_exit("The routine '{}' was not found. Use 'poise --list' to "
                     "see all available routines.".format(args.routine))
    # If the routine wasn't specified on command-line, prompt the user for one
    else:
        routine_id = get_routine_id()

    # If get_routine_id() returns None, then a new routine was requested.
    if routine_id is None:
        # Prompt the user later whether they want to run it after creating it.
        prompt_run = True
        # Get the Routine object.
        routine = get_new_routine()
        # Store the routine for future usage
        with open(os.path.join(p_routines, routine.name + ".json"), "wb") as f:
            json.dump(routine._asdict(), f)
        routine_id = routine.name
    # Otherwise, load a saved routine.
    else:
        routine = load_routine(routine_id)
        prompt_run = False

    # Prompt the user whether they want to run it now, but only if they created
    # a new routine from scratch. If they entered an existing routine (either
    # via command-line, or in a dialog box), then we assume they want to run it
    # now.
    if prompt_run and not run_now():
        EXIT()

    # If they do want to run it, then we can carry on.
    # Make sure user has opened a dataset
    if CURDATA() is None:
        err_exit("Please select a dataset!")

    # Keep track of the currently active dataset. We want to make sure that
    # it is _the_ active dataset every time the AU programme starts, or
    # else we risk running `zg` on a different dataset --> overwriting
    # other data!!
    current_dataset = CURDATA()

    # Construct the path to the folder of the current spectrum.
    p_spectrum = make_p_spectrum()
    # Generate the path to the log file. The log file belongs to the folder
    # containing the first expno.
    p_optlog = os.path.normpath(os.path.join(current_dataset[3],
                                             current_dataset[0],
                                             current_dataset[1],
                                             "poise.log"))

    # Issue a warning if dataset is > 2D
    if GETACQUDIM() > 2:
        MSG("Warning: poise is only designed for 1D and 2D data.\n"
            "If you are sure you want to use it on this {}D dataset,"
            " please press OK to continue.".format(GETACQUDIM()))

    # Check that the Routine object itself is valid (i.e. has all the correct
    # keys).
    check_routine(routine)
    # Check that the cost function exists
    saved_cfs = detect_costfunctions().keys()
    if routine.cf not in saved_cfs:
        err_exit("The associated cost function {} could not be"
                 " found.".format(routine.cf))
    # If the AU programme is blank, set it to poise_nd.
    if routine.au == "":
        dim = GETACQUDIM()
        if dim == 1:
            # Namedtuples are immutable, so we need the _replace method.
            routine = routine._replace(au="poise_1d")
        elif dim == 2:
            routine = routine._replace(au="poise_2d")
        else:
            err_exit("You must specify an AU programme when using POISE with"
                     " >2D experiments.")
    # Check that the AU programme exists.
    if not au_exists(routine.au):
        err_exit("The AU programme {} was not found.".format(routine.au))

    # Make sure that Python 3 executable can be found
    check_python3path()

    # Check that the backend script is intact
    if not os.path.isfile(p_backend):
        err_exit("Backend script not found. Please reinstall poise.")

    # Make sure that args.algorithm is a valid algorithm.
    if args.algorithm not in ["nm", "mds", "bobyqa"]:
        # Have to use ERRMSG because MSG() is modal
        ERRMSG("Optimisation algorithm '{}' not found; "
               "using Nelder-Mead instead".format(args.algorithm))
        args.algorithm = "nm"

    # Before we start the main loop, we need to kill off any other backend
    # processes that are still alive. (We don't do it too early, otherwise we
    # could accidentally terminate a POISE run by running something innocuous
    # like poise -l.)
    kill_remaining_backends()

    # We need to catch java.lang.Error throughout the main loop so that cleanup
    # can be performed if the script is killed from within TopSpin. See #23.
    try:
        backend = subprocess.Popen([p_python3, '-u', p_backend],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE)
        # Pass key information to the backend script
        print(args.algorithm, file=backend.stdin)
        print(routine_id, file=backend.stdin)
        print(p_spectrum, file=backend.stdin)
        print(args.maxfev, file=backend.stdin)
        backend.stdin.flush()

        # Main loop, controlled by the lines printed by the backend.
        first_expno = True
        while True:
            # Read in what the backend has to say.
            line = backend.stdout.readline()

            # CASE 1 -- Optimisation has converged (or terminated with
            #           CostFunctionError)
            if line.startswith("optima:"):
                optima = line.split()[1:]
                # Get the optimiser message as well.
                opt_message = backend.stdout.readline()
                break

            # CASE 2 -- Values to put in an experiment
            elif line.startswith("values:"):
                # Increment expno if it's not the first time.
                if args.separate:
                    if not first_expno:
                        # Before doing anything, check first whether a dataset
                        # already exists, so that we don't overwrite
                        # anything...!
                        if next_expno_exists():
                            raise RuntimeError("Existing dataset found at "
                                               "next expno! poise has been "
                                               "terminated.")
                        else:
                            XCMD("iexpno")
                            RE(current_dataset)
                            RE_IEXPNO()
                            current_dataset = CURDATA()
                            XCMD("browse_update_tree")
                    else:
                        first_expno = False
                # Make sure we're at the correct dataset.
                RE(current_dataset)
                # Obtain the values and set them
                values = line.split()[1:]
                if len(values) != len(routine.pars):
                    raise RuntimeError("Invalid values passed from backend: "
                                       "'{}'".format(line))
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
                # Make sure we're at the correct dataset (again).
                RE(current_dataset)
                # Run acquisition and processing
                XCMD("xau {}".format(routine.au))
                # Check whether acquisition is complete
                if not acqu_done():
                    raise RuntimeError("Acquisition stopped prematurely. "
                                       "poise has been terminated.")
                # Tell backend script it's done
                print("done", file=backend.stdin)
                print(make_p_spectrum(), file=backend.stdin)
                backend.stdin.flush()

            # CASE 3 - Value of cost function at current spectrum
            # We take this value and put it inside the parameter TI.
            elif line.startswith("cf:"):
                cf_val = line.split()[1]
                PUTPAR("TI", cf_val)

            # CASE 4 - Traceback for backend error
            # The entire main() routine in the backend is wrapped by a
            # try/except which catches all exceptions and propagates them to
            # the frontend by printing the traceback.
            elif line.startswith("Backend exception: "):
                raise RuntimeError(line)

            # CASE 5 - Everything else
            else:
                raise RuntimeError("Invalid message from backend: '{}'."
                                   "Please see error log for more "
                                   "information.".format(line))
    # Cleanup code if anything goes wrong.
    except (Error, RuntimeError) as e:
        # Reset TI to empty string
        PUTPAR("TI", " ")
        # For some really silly reason, I can't just call
        # kill_remaining_backends() here, or else if the *original* POISE is
        # killed (using TopSpin's `kill`), it throws a
        # java.nio.BufferOverflowException. On Windows 10, this *does*
        # terminate the backend process, but it doesn't delete the .pidXXX
        # file. In principle there's nothing *wrong* with that because the
        # .pidXXX file will be cleaned up on the next run, but this just works
        # more cleanly.
        XCMD("xpy poise --kill")
        # BTW, err_exit() only gets called if it's RuntimeError. I don't know
        # why. If it's killed via TopSpin, then it just shows
        # java.lang.ThreadDeath as usual.
        err_exit("Error during acquisition loop:\n{}".format(e.message),
                 log=True)

    # Optimisation successfully ended, or prematurely ended?
    opt_success = opt_message == "Optimisation terminated successfully."

    # Store the optima in the (final) dataset, and show a message to the user
    # if not in quiet mode.
    RE(current_dataset)
    s = opt_message + "\n"
    for par, optimum in zip(routine.pars, optima):
        so_far = "" if opt_success else " (so far)"
        s = s + "Optimal value for {}{}: {}\n".format(par, so_far, optimum)
        if not args.separate:
            convert_name_and_putpar(par, optimum)
    if not args.separate:
        s = s + "These values have been set in the current experiment.\n"
    s = s + "Detailed information can be found at: {}".format(p_optlog)
    if not args.quiet:
        MSG_nonmodal(s, "POISE optimisation complete")
    EXIT()


class cst:
    """
    Constants used throughout the programme.
    """
    # TopSpin's internal codes for keypresses
    ENTER = -10
    ESCAPE = -27
    # List-type parameters. These parameters are accessed in the TopSpin
    # command line using "cnst1" (for example), but TopSpin's GETPAR() and
    # PUTPAR() Python functions need a space between the name and number, i.e.
    # "CNST 1".
    params_with_space = ["CNST", "D", "P", "PLW", "PLDB", "PCPD",
                         "GPX", "GPY", "GPZ", "SPW", "SPDB", "SPOFFS",
                         "SPOAL", "L", "IN", "INP", "PHCOR"]


def MSG_nonmodal(msg, title=""):
    """
    Non-modal version of MSG().

    For some reason TopSpin forces MSG() to be modal and if you want a
    non-modal message you have to use ERRMSG(), which has a scary-looking error
    sign, not exactly what I want people to see when they finish an
    optimisation!

    Well, it turns out you can reverse engineer their source code quite easily
    using inspect.getsource(), so this was born...

    Parameters
    ----------
    msg : str
        Message to be displayed.
    title : str, optional
        Title of the dialog box.
    """
    dialog = mfw.BInfo()
    dialog.setMessage(msg)
    dialog.setTitle(title)
    dialog.setBlocking(0)  # in ordinary MSG() this is 1
    dialog.show()


def err_exit(error, log=False):
    """
    Shows an error message in TopSpin, optionally logs it to the frontend error
    log, then quits the Python script.

    Parameters
    ----------
    error : str
        Error message to be displayed.
    log : bool, optional
        Whether to log the message to the frontend error log.

    Returns
    -------
    None
    """
    ERRMSG(title="poise", message=error)
    if log:
        current_dataset = CURDATA()
        p_front_err = os.path.normpath(os.path.join(current_dataset[3],
                                                    current_dataset[0],
                                                    current_dataset[1],
                                                    "poise_err_frontend.log"))
        with open(p_front_err, "a") as ferr:
            ferr.write("======= From frontend =======\n")
            ferr.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
            ferr.write(error + "\n\n")
    EXIT()


def list_files(path, ext="", with_ext=False):
    """
    Lists all files with a given extension found in a directory, if the
    directory exists.

    Parameters
    ---------
    path : str
        Directory to be searched in.
    ext : str, optional
        Extension of files to be searched for. Should include the dot, i.e. to
        search for Python files, use ext=".py".
    with_ext : bool, optional
        Whether to return filenames with the extension, or without it (i.e.
        with the extension stripped).

    Returns
    -------
    fnames : list of str
        A list of the filenames as strings.
    """
    if os.path.isdir(path):
        if ext == "":
            return [i for i in os.listdir(path)
                    if os.path.isfile(os.path.join(path, i))]
        else:
            if with_ext:
                return [i for i in os.listdir(path)
                        if i.endswith(ext)
                        and os.path.isfile(os.path.join(path, i))]
            else:
                return [os.path.splitext(i)[0] for i in os.listdir(path)
                        if i.endswith(ext)
                        and os.path.isfile(os.path.join(path, i))]
    else:
        return []


def run_now():
    """
    Asks the user whether they want to run an optimisation now, or just set up
    a new routine.

    Parameters
    ----------
    None

    Returns
    -------
    bool : True if user wants to run an optimisation now.
    """
    x = SELECT(title="poise",
               message=("Do you want to run the optimisation now?"),
               buttons=["Yes", "No"])
    return x in [0, cst.ENTER]


def get_routine_id():
    """
    Interactively prompts the user to choose a routine, using dialog boxes in
    TopSpin.

    Parameters
    ---------
    None

    Returns
    -------
    routine_id : str or None
        If a saved routine is chosen, the routine name is returned as a string
        (the corresponding routine .json file should be found as
        <routine_name>.json in .../py/user/poise_backend/routines).

        Returns None if the user requests a new routine.
    """
    # Check for existing saved routines
    saved_routines = list_files(p_routines, ext=".json")

    # Return immediately if there are no saved routines
    if saved_routines == []:
        return None
    # Otherwise, show the user a dialog box.
    else:
        x = SELECT(title="poise",
                   message=("Do you want to use a saved routine, or create a "
                            "new routine?"),
                   buttons=["Saved routine", "New routine"])

        # User pressed 'Saved routine', or Enter
        if x in [0, cst.ENTER]:
            s = "\n".join(saved_routines)
            # Prompt the user to choose one
            y = INPUT_DIALOG(title="poise: available routines",
                             header="Available routines:\n" + s,
                             items=["Routine:"])
            if y is None:  # User closed the dialog
                EXIT()
            elif y[0] in saved_routines:  # User gave a correct routine name
                return y[0]
            else:  # User wrote something, but it wasn't correct
                if y[0] != "":
                    err_exit("The routine '{}' was not found.".format(y[0]))
        # User pressed 'New routine'.
        elif x == 1:
            return None
        # User did something else, like Escape or close button.
        else:
            EXIT()


def get_new_routine():
    """
    Prompts the user for all the details required to make a new routine, using
    TopSpin dialog boxes.

    Doesn't serialise the routine!

    Parameters
    ---------
    None

    Returns
    -------
    Routine
        The Routine object created from the given parameters.
    """
    # Prompt for routine name.
    name = INPUT_DIALOG(title="poise: choose a name...",
                        header="Please choose a name to save this routine as:",
                        items=["Name:"])
    if name is None or name[0].strip() == "":
        EXIT()
    name = name[0].replace(".py", "").strip()

    # Prompt for parameters to be optimised.
    opt_pars = INPUT_DIALOG(title="poise: choose parameters...",
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
        settings = INPUT_DIALOG(title="poise: settings for {}".format(i),
                                header=("Please choose the minimum value, "
                                        "maximum value, initial value, and "
                                        "tolerance for {}:".format(i)),
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
    saved_cfs = detect_costfunctions().keys()

    if saved_cfs == []:
        err_exit("No cost functions have been defined!\n"
                 "Please reinstall poise to get a default set, or define "
                 "your own cost function based on the documentation.")
    else:
        s = ", ".join(saved_cfs)
        x = INPUT_DIALOG(title=("poise: choose a cost function and"
                                " (optionally) an AU programme..."),
                         header="Available cost functions: " + s,
                         items=["Cost function:", "AU programme (optional):"])
        if x is None:  # user closed the dialog
            EXIT()
        elif x[0] in saved_cfs:
            cf, au = x[0], x[1]
        else:
            err_exit("Cost function {} was not found. Exiting...".format(x[0]))

    return Routine(name, opt_pars, lbs, ubs, inits, tols, cf, au)


def load_routine(routine_name):
    """
    Reads in a Routine serialised as JSON inside the p_routines directory.

    Parameters
    ----------
    routine_name : str
        The name of the routine. The routine is read from the
        p_routines/<routine_name>.json file.

    Returns
    -------
    Routine
        The Routine object.
    """
    with open(os.path.join(p_routines, routine_name + ".json"), "rb") as f:
        routine = Routine(**json.load(f))
    return routine


def check_routine(routine):
    """
    Checks that a Routine object is valid. Exits the programme if it isn't.

    Parameters
    ----------
    routine : Routine
        The Routine object to be checked.

    Returns
    -------
    None
    """
    try:
        (routine.name, routine.pars, routine.lb, routine.ub,
         routine.init, routine.tol, routine.cf, routine.au)
    except AttributeError:
        err_exit("The routine file is invalid.\n"
                 "Please delete it and recreate it from within poise.")


def routine_to_str(routine):
    """
    Generates a paragraph of text that summarises the parameters of a Routine.

    Parameters
    ----------
    routine : Routine
        The Routine to be described.

    Returns
    -------
    str
        The various parameters of the Routine in human-readable form.
    """
    d = routine._asdict()
    s = routine.name

    for key in sorted(list(d.keys())):
        s += "\n\t{:5}: {}".format(key, str(d[key]))
    return s


def list_routines_cfs():
    """
    Shows the user a list of cost functions and their docstrings, then routines
    and their parameters. Invoked via ``poise -l``.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    # Get cost functions
    cfs = detect_costfunctions()
    text = "Available cost functions (and their descriptions)\n"
    text += "-------------------------------------------------\n"
    cf_strings = [" * {}\n    {}".format(function_name, docstring)
                  for function_name, docstring in cfs.items()]
    text += "\n\n".join(cf_strings)
    # Get routines
    text += "\n"
    text += "\nAvailable routines\n-------------------\n"
    routine_names = sorted(list_files(p_routines, ext=".json"))
    routine_strings = [routine_to_str(load_routine(routine_name))
                       for routine_name in routine_names]
    text += "\n\n".join(routine_strings)
    VIEWTEXT(title="Available poise cost functions and routines", text=text)
    EXIT()


def detect_costfunctions():
    """
    Gets poise_backend/get_cfs.py to parse the costfunctions.py file (using the
    ast module) and pass a dictionary of defined cost functions and their
    docstrings back to the frontend.

    Parameters
    ----------
    None

    Returns
    -------
    available_cfs : dict
        Dictionary where keys are the names of the cost function and values are
        their docstrings.
    """
    p_get_cfs = os.path.join(p_poise, "get_cfs.py")
    p = subprocess.Popen([p_python3, p_get_cfs], stdout=subprocess.PIPE)
    fdict_as_str, _ = p.communicate()
    return json.loads(fdict_as_str)


def check_python3path():
    """
    Checks that the global variable p_python3 is set to a valid file. Exits the
    programme if it isn't.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    if not os.path.isfile(p_python3):
        err_exit("The python3 executable was not found.\n"
                 "Please specify p_python3 in poise.py.")


def convert_name(name):
    """
    Converts the name of a parameter from the command-line accessible version
    (e.g. "cnst1") to the version that is suitable for the TopSpin GETPAR() and
    PUTPAR() functions (e.g. "CNST 1").

    Parameters
    ----------
    name : str
        Name of the parameter.

    Returns
    -------
    ts_name : str
        Name of the parameter that can be used with GETPAR() and PUTPAR().
    """
    # GETPAR() accepts: CNST 1, P 1, D 1, PLW 1, PLdB 1 (note small d), GPZ 1
    #                   SPW 1, SPdB 1, SPOFFS 1, SPOAL 1,
    #               but O1, O1P, SFO1 (note no space)
    ts_name = name.upper()
    ts_namel = ts_name.rstrip("1234567890")   # the word
    ts_namer = ts_name[len(ts_namel):]        # the number
    # Add a space if needed
    if ts_namel in cst.params_with_space:
        ts_name = ts_namel + " " + ts_namer
    # Convert DB back to dB
    ts_name = ts_name.replace("PLDB", "PLdB").replace("SPDB", "SPdB")
    return ts_name


def convert_name_and_getpar(name):
    """
    Obtains the value of an acquisition parameter. The parameter name is
    first converted into a format suitable for TopSpin's GETPAR() function.
    Returns the value as a float. Exits with an error if the value can't be
    converted to a float.

    Parameters
    ----------
    name : str
        Name of the parameter to be looked up, e.g. "cnst1" or "d10".

    Returns
    -------
    val : float
        Value of the input parameter.
    """
    # Get the value.
    val = GETPAR(convert_name(name))
    # Check that it's a float.
    try:
        val = float(val)
        return val
    except ValueError:
        err_exit("The acquisition parameter {} could not be found, "
                 "or does not have a numerical value.".format(name))


def convert_name_and_putpar(name, val):
    """
    Obtains the value of an acquisition parameter. The parameter name is
    first converted into a format suitable for TopSpin's GETPAR() function.
    Exits with an error if the value isn't a float.

    Parameters
    ----------
    name : str
        Name of the parameter to be looked up, e.g. "cnst1" or "d10".
    val : float
        The value to be set.

    Returns
    -------
    None
    """
    try:
        val = float(val)
        PUTPAR(convert_name(name), str(val))
    except ValueError:
        err_exit("The value {} for parameter {} "
                 "was invalid.".format(val, name))


def process_values(parname, input_string):
    """
    Does some processing on user input to allow familiar hacks, like
    entering 2m for a duration or 2k for 2048.

    Parameters
    ----------
    parname : str
        String containing the parameter name (either "p1" or "P 1" works).
    input_string : str
        The string entered by the user into the dialog box.

    Returns
    -------
    float
        The processed value, as a float.
    """
    # We need to determine whether the parameter is a pulse (for which the
    # default units are us), or a delay (for which the default units are
    # seconds).
    pulse = 1e6 if parname.upper().rstrip("1234567890").strip() == "P" else 1
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

    Parameters
    ----------
    None

    Returns
    -------
    str
        The absolute path to the procno folder.
    """
    x = CURDATA()
    p = os.path.join(x[3], x[0], x[1], "pdata", x[2])
    return p


def next_expno_exists():
    """
    Checks whether the expno folder with expno 1 greater than the current
    experiment exists.

    Parameters
    ---------
    None

    Returns
    -------
    bool
        True if it does. False if not.
    """
    x = CURDATA()
    next_expno = str(int(x[1]) + 1)
    p = os.path.join(x[3], x[0], next_expno)
    return os.path.isdir(p)


def acqu_done():
    """
    Checks whether the spectrum was completely acquired. Useful for stopping
    poise if acquisition is prematurely terminated (e.g. by ``stop``).

    Parameters
    ----------
    None

    Returns
    -------
    bool
        True if the acquisition was successfully completed. False otherwise.
    """
    # Check NS
    if GETPAR("NS") != GETPARSTAT("NS"):
        return False
    # Check TD (see #25)
    if GETPAR("TD") != GETPARSTAT("TD"):
        return False
    # Check indirect dimension TD for 2Ds
    if GETACQUDIM() > 1:
        if GETPAR("TD", axis=1) != GETPARSTAT("TD", axis=1):
            return False
    # OK, looks like the acquisition did complete
    return True


def au_exists(au):
    """
    Checks for the existence of a named AU programme.

    Parameters
    ----------
    au : str
        Name of the AU programme.

    Returns
    -------
    bool : Whether the AU programme exists.
    """
    # Undocumented TopSpin function. Fun.
    au_folders = getParfileDirs(2)
    # Just check whether it exists in each of the folders.
    for folder in au_folders:
        if os.path.exists(os.path.join(folder, au)):
            return True
    return False


def pulprog_contains_wvm():
    """
    Parses the text of the current pulse programme to see whether WaveMaker
    directives are used.

    Parameters
    ----------
    None

    Returns
    -------
    bool
        True if the pulse programme does contain WaveMaker directives. False
        otherwise.
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


def kill_remaining_backends():
    """
    Checks the poise_backend folder for any .pidXXXX files (which represent
    backends that have not exited), then kills all the associated PIDs and
    deletes the files.
    """
    for file in os.listdir(p_poise):
        if file.startswith(".pid"):
            try:
                pid = int(file[4:])
            except ValueError:  # not an int
                pass
            else:
                kill_pid(file[4:])
                os.remove(os.path.join(p_poise, file))


def kill_pid(pid):
    """
    Kills a process with PID pid.

    Parameters
    ----------
    pid : int or str
        The process ID.

    Returns
    -------
    None
    """
    from java.lang.System import getProperty
    # Windows
    if "wind" in getProperty("os.name").lower():
        subprocess.call(["taskkill", "/f", "/pid", str(pid)])
    # *nix
    else:
        subprocess.call(["kill", "-9", str(pid)])


def create_routine(cli_args):
    """
    Creates a .json file for a one-parameter routine.

    Parameters
    ----------
    cli_args : list of str
        This list should contain 8 strings, namely: name, parameter, minimum
        value, maximum value, initial value, tolerance, cost function, and AU
        programme.

    Returns
    -------
    None
    """
    name, param, minval, maxval, init, tol, cf, au = cli_args
    try:
        minval = float(minval)
        maxval = float(maxval)
        init = float(init)
        tol = float(tol)
    except ValueError:
        err_exit("poise --create: invalid input")
    if (minval > init) or (init > maxval) or (tol > (maxval - minval)):
        err_exit("poise --create: invalid input")
    # If we got here, the input is probably OK.
    routine = Routine(name, [param], [minval], [maxval], [init], [tol], cf, au)
    with open(os.path.join(p_routines, routine.name + ".json"), "wb") as f:
        json.dump(routine._asdict(), f)
    EXIT()


def delete_routine(name):
    """
    Deletes a routine .json file.

    Parameters
    ----------
    name : str
        Name of the routine to be deleted.

    Returns
    -------
    None
    """
    # Check whether said routine really exists
    saved_routines = list_files(p_routines, ext=".json")
    if name not in saved_routines:
        err_exit("The routine {} was not found.".format(name))
    else:
        os.remove(os.path.join(p_routines, name + ".json"))
        MSG_nonmodal("Routine {} deleted.".format(name))
        EXIT()


class TSArgumentParser(argparse.ArgumentParser):
    """
    Custom ArgumentParser class which shows a TopSpin dialog box with errors
    instead of printing to stderr.
    """
    def print_usage(self, file=None):
        VIEWTEXT(title="poise usage", text=self.format_usage())
        EXIT()

    def print_help(self, file=None):
        VIEWTEXT(title="poise help", text=self.format_help())
        EXIT()

    def error(self, message):
        ERRMSG(title="poise", message=message)
        EXIT()


if __name__ == "__main__":
    # Parse arguments.
    parser = TSArgumentParser(
        prog="poise",
        description=("Python script for optimisation of acquisition "
                     "parameters in TopSpin. Requires a separate Python 3 "
                     "backend (run `pip install nmrpoise` to download the "
                     "backend). Full documentation can be found at "
                     "https://foroozandehgroup.github.io/nmrpoise.")
    )
    # Commands that don't actually do any optimisations; they just run one
    # function and exit. These are mutually exclusive (since in general the
    # user should only be doing one of these at a time).
    me_group = parser.add_mutually_exclusive_group()
    parser.add_argument(
        "routine",
        nargs="?",
        help=("The name of the routine to use (use 'poise --list' to see "
              "available routines).")
    )
    parser.add_argument(
        "-a",
        "--algorithm",
        default="nm",
        choices=["nm", "mds", "bobyqa"],
        help="Optimisation algorithm to use. (default: 'nm')"
    )
    me_group.add_argument(
        "--create",
        type=str,
        nargs=8,
        metavar=("NAME", "PARAM", "MINVAL", "MAXVAL", "INIT", "TOLS", "CF",
                 "AU"),
        help=("Create a new POISE routine for optimisation of one parameter."
              " For multiple parameter optimisations, please use the GUI."
              " Note that unlike in the GUI, the AU programme must be"
              " specified here. Also, shorthand notation such as 'u' or 'm'"
              " for units are not allowed here.")
    )
    me_group.add_argument(
        "--delete",
        type=str,
        help=("Delete an existing POISE routine.")
    )
    me_group.add_argument(
        "--kill",
        action="store_true",
        help=("Kill POISE backends that may still be running.")
    )
    me_group.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all available routines and exit."
    )
    parser.add_argument(
        "--maxfev",
        type=int,
        default=0,
        help=("Maximum function evaluations to allow. Use 0 to not enforce "
              "any limit (technically there is a hard limit, which is 500 "
              "times the number of parameters being optimised). (default: 0)")
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help=("Don't display any messages at the end of the optimisation. "
              "Using this flag is necessary if POISE is to be run under "
              "automation. (default: off)")
    )
    parser.add_argument(
        "-s",
        "--separate",
        action="store_true",
        help=("Use separate expnos for each function evaluation. (default: "
              "off)")
    )
    args = parser.parse_args()

    # List
    if args.create:
        create_routine(args.create)
    if args.delete:
        delete_routine(args.delete)
    elif args.list:
        list_routines_cfs()
    elif args.kill:
        kill_remaining_backends()
    else:
        main(args)
