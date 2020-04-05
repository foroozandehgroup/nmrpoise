from __future__ import division, with_statement, print_function
import os
import pickle
import de.bruker.nmr.mfw.root.UtilPath as up
import subprocess

tshome = up.getTopspinHome()  # use tshome to avoid installer overwriting
p_poptpy = os.path.join(tshome, "exp/stan/nmr/py/user/poptpy")
p_backend = os.path.join(p_poptpy, "poptpy_be.py")
p_routines = os.path.join(p_poptpy, "routines")
p_costfunctions = os.path.join(p_poptpy, "cost_functions")
p_optlog = os.path.join(p_poptpy, "poptpy.log")
p_opterr = os.path.join(p_poptpy, "poptpy_err.log")
p_python3 = "/usr/local/bin/python3"


def main():
    """
    Main routine.
    """
    # Set verbosity of programme
    global logging_level
    logging_level = cst.DEBUG

    # Make sure user has opened a dataset
    if CURDATA() is None:
        echo("no dataset found", cst.CRITICAL)
        err_exit("Please select a dataset!")

    # Check that dataset is 1D
    if GETACQUDIM() != 1:
        echo("{}D dataset found -- only works for 1D".format(GETACQUDIM()),
             cst.CRITICAL)
        err_exit("Please select a 1D dataset!\n"
                 "Currently poptpy does not work with "
                 "multidimensional experiments.")

    # Make folders if they don't exist
    for folder in [p_poptpy, p_routines, p_costfunctions]:
        if not os.path.isdir(folder):
            os.makedirs(folder)

    # Select optimisation routine
    routine_id = get_routine_id()

    # Create or read the Routine object
    if routine_id is None:  # New routine was requested
        echo("new routine selected", cst.DEBUG)
        routine = Routine(*get_new_routine_parameters())
        with open(os.path.join(p_routines, routine.name), "wb") as f:
            pickle.dump(routine, f)
        routine_id = routine.name
    else:  # Saved routine was requested
        echo("routine {} selected".format(routine_id), cst.DEBUG)
        with open(os.path.join(p_routines, routine_id), "rb") as f:
            routine = pickle.load(f)

    # Check that the Routine object is valid
    check_routine(routine)

    # Make sure that Python 3 executable can be found
    check_python3path()

    # Create the AU programme for acquisition
    create_au_prog()

    # Construct the path to the folder of the current spectrum.
    x = CURDATA()
    p_spectrum = os.path.join(x[3], x[0], x[1], "pdata", x[2])

    # Run the backend script
    if not os.path.isfile(p_backend):
        err_exit("Backend script not found. Please reinstall poptpy.")
    echo("Loading backend script...", cst.INFO)
    ferr = open(p_opterr, "a")
    backend = subprocess.Popen([p_python3, '-u', p_backend],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=ferr)
    # Pass key information to the backend script
    print(routine_id, file=backend.stdin)
    print(p_spectrum, file=backend.stdin)
    print(p_optlog, file=backend.stdin)
    backend.stdin.flush()

    # Enter a loop where: 1) backend script passes values of acquisition params
    #                        to frontend script
    #                     2) frontend script runs acquisition
    #                     3) frontend script passes "done" to backend script
    #                        to indicate that it's done
    # The loop is broken when the backend script passes "done" to the frontend
    # script instead of a new set of values (in step 1).
    while True:
        line = backend.stdout.readline()
        if line.strip() == "done":
            break
        else:
            # Obtain the values and set them
            values = line.split()
            echo("Setting parameters to: {}".format(values), cst.INFO)
            if len(values) != len(routine.pars):
                err_exit("Number of values found not equal to"
                         "number of parameters.")
            for i in range(len(routine.pars)):
                try:
                    float(values[i])
                except ValueError:
                    err_exit("Invalid parameter value"
                             "{} found.".format(values[i]))
                convert_name_and_putpar(routine.pars[i], values[i])
            # Run acquisition and processing
            XCMD("xau poptpy_au")
            # Tell backend script it's done
            print("done", file=backend.stdin)
            backend.stdin.flush()

    # If it reaches here, the optimisation should be done
    # Close error output file, delete it if it is empty
    ferr.close()
    if os.stat(p_opterr).st_size == 0:
        os.remove(p_opterr)
    # Read in optimal values, notify user, and set parameters
    line = backend.stdout.readline()
    optima = line.split()
    s = ""
    for i in range(len(routine.pars)):
        s = s + "Optimal value for {}: {}\n".format(routine.pars[i], optima[i])
        convert_name_and_putpar(routine.pars[i], optima[i])
    s = s + "These values have been set in the current experiment.\n"
    s = s + "Detailed information can be found at: {}".format(p_optlog)
    MSG(s)
    # TODO: Prompt user to save optima found (can overwrite the routine file)
    EXIT()


class Routine:
    def __init__(self, name, pars, lb, ub, init, tol, cf):
        self.name = name
        self.pars = pars
        self.lb = lb
        self.ub = ub
        self.init = init
        self.tol = tol
        self.cf = cf


class cst:
    """
    Constants used throughout the programme.
    """
    # logging levels
    DEBUG = 0
    INFO = 1
    WARNING = 2
    CRITICAL = 3
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


def echo(message_str, level):
    """
    Prints text to TopSpin status bar if its importance is above a certain
    threshold (logging_level).

    Set logging_level = cst.DEBUG to get debugging info, cst.INFO for general
    info, cst.WARNING for warnings and errors only, cst.CRITICAL for critical
    errors only.

    Arguments:
        message_str (string): Message to be displayed.
        level (int)         : Level of severity (cst.DEBUG, cst.INFO,
                               cst.WARNING, cst.CRITICAL).

    Returns: None.
    """
    if level >= logging_level:
        SHOW_STATUS("poptpy: {}".format(message_str))


def list_files(path):
    """
    Lists all files found in a directory, if it exists.

    Arguments:
        path (string) : Directory to be searched in.

    Returns:
        List containing filenames.
    """
    if os.path.isdir(path):
        # return [i for i in os.listdir(path) if os.path.isfile(i)]
        return [i for i in os.listdir(path)]
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
        echo("returned value {}".format(str(x)), cst.DEBUG)

        if x == 0 or x == cst.ENTER:  # user pressed Yes or Enter
            s = ", ".join(saved_routines)
            y = INPUT_DIALOG(title="Available routines",
                             header="Available routines: " + s,
                             items=["Routine:"])
            echo("returned value {}".format(str(y)), cst.DEBUG)

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
        A list of objects [params, min_values, max_values, cf, cf_parameters]
         - name          : string containing name of routine
         - params        : list of experimental values to be optimised
         - min_values    : list of minimum bounds
         - max_values    : list of maximum bounds
         - cf            : string containing name of cost function
    """
    # Prompt for routine name.
    name = INPUT_DIALOG(title="Choose a name...",
                        header="Please choose a name to save this routine as:",
                        items=["Name:"])
    if name is None or name[0].strip() == "":
        echo("no name provided!", cst.CRITICAL)
        EXIT()
    name = name[0].replace(".py", "").strip()

    # Prompt for parameters to be optimised.
    opt_pars = INPUT_DIALOG(title="Choose parameters...",
                            header=("Please select experimental parameters "
                                    "to be optimised (separated by commas or "
                                    "spaces):"),
                            items=["Parameters:"])
    # Quit if nothing is given
    if opt_pars is None or opt_pars[0].strip() == "":
        echo("no parameters provided!", cst.CRITICAL)
        EXIT()
    opt_pars = opt_pars[0].replace(",", " ").split()
    opt_pars = [i for i in opt_pars if i]  # remove empty strings

    # Prompt for minimum, maximum, initial values, and tolerances..
    lb = []
    ub = []
    init = []
    tol = []
    for i in opt_pars:
        settings = INPUT_DIALOG(title="Settings for {}".format(i),
                                header="Please choose the minimum value, "
                                       "maximum value, initial value, and "
                                       "tolerance for {}:".format(i),
                                items=["Minimum:", "Maximum:",
                                       "Initial value:", "Tolerance:"])
        if settings is None:
            EXIT()
        else:
            lb.append(process_values(i, settings[0]))
            ub.append(process_values(i, settings[1]))
            init.append(process_values(i, settings[2]))
            tol.append(process_values(i, settings[3]))

    # Check if the values are sensible
    s = ""
    for i in range(len(opt_pars)):
        if (lb[i] >= ub[i]):
            s = s + ("Please set the maximum value of {} to be larger "
                     "than the minimum value. "
                     "[Current values: min={}, max={}]\n").format(opt_pars[i],
                                                                  lb[i],
                                                                  ub[i])
        else:
            if ((init[i] < lb[i]) or (init[i] > ub[i])):
                s = s + ("Please set the initial value of {} to a value "
                         "to be between {} and {}. "
                         "[Current value: {}]\n").format(opt_pars[i], lb[i],
                                                         ub[i], init[i])
            if ((tol[i] > ub[i] - lb[i]) or (tol[i] <= 0)):
                s = s + ("Please set the tolerance of {} to a positive value "
                         "smaller than {}. "
                         "[Current value: {}]\n").format(opt_pars[i],
                                                         ub[i] - lb[i],
                                                         tol[i])
    if s:
        err_exit(s)

    # Prompt for cost function.
    # Search for existing cost functions
    saved_cfs = list_files(p_costfunctions)

    if saved_cfs == []:
        echo("no cost functions found", cst.CRITICAL)
        err_exit("No cost functions have been defined!\n"
                 "Please reinstall poptpy to get a default set, or define "
                 "your own cost function based on the documentation.")
    else:
        s = ", ".join(saved_cfs)
        x = INPUT_DIALOG(title="Choose a cost function...",
                         header="Available cost functions: " + s,
                         items=["Cost function:"])
        echo("returned value {}".format(str(x)), cst.DEBUG)
        if x is None:  # user closed the dialog
            EXIT()
        elif x[0] in saved_cfs:
            cf = x[0]
        else:
            echo("unknown cost function specified", cst.CRITICAL)
            err_exit("Cost function {} was not found. Exiting...".format(x[0]))

    return [name, opt_pars, lb, ub, init, tol, cf]


def check_routine(routine):
    """
    Checks that a Routine object is valid. Exits the programme if it isn't.

    Arguments:
        routine (Routine): the routine to be checked.

    Returns: None.
    """
    try:
        echo("routine.name = {}".format(routine.name), cst.DEBUG)
        echo("routine.pars = {}".format(routine.pars), cst.DEBUG)
        echo("routine.lb = {}".format(routine.lb), cst.DEBUG)
        echo("routine.ub = {}".format(routine.ub), cst.DEBUG)
        echo("routine.init = {}".format(routine.init), cst.DEBUG)
        echo("routine.tol = {}".format(routine.tol), cst.DEBUG)
        echo("routine.cf = {}".format(routine.cf), cst.DEBUG)
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
        check_call([p_python3, "--version"])
    except CalledProcessError:
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


def create_au_prog():
    """
    Creates an AU programme for acquisition and processing in TopSpin's
    default directory, if it doesn't already exist.
    """
    poptpy_au_text = "ZG\nEFP\nAPBK\nQUIT"  # Change this if desired
    p_acqau = os.path.join(tshome, "exp/stan/nmr/au/src/user/poptpy_au")
    f = open(p_acqau, "w")
    f.write(poptpy_au_text)
    f.close()


if __name__ == "__main__":
    main()
