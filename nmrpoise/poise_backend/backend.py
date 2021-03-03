"""
backend.py
----------

Backend POISE script which carries out the optimisation, passing values to the
frontend to trigger acquisition.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import os
import sys
import json
from traceback import print_exc
from datetime import datetime
from pathlib import Path
from collections import namedtuple
from contextlib import contextmanager

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
from .shared import _g
from .cfhelpers import *
from . import costfunctions
from . import costfunctions_user

Routine = namedtuple("Routine", "name pars lb ub init tol cf au")


@contextmanager
def pidfile():
    """
    Context manager that creates a '.pid<PID>' file inside the poise_backend
    directory. Deletes the file once the backend exits.
    """
    pid = os.getpid()
    pid_fname = Path(__file__).resolve().expanduser().parent / f".pid{pid}"
    pid_fname.touch()
    try:
        yield
    finally:
        if pid_fname.exists():
            pid_fname.unlink()


def main_wrapper():
    """
    Wrapper for main(). This performs several tasks:
      1. Reads in the global variables printed by the frontend.
      2. Implements a context manager to print the backend PID to a file
         ($ts/py/user/poise_backend/pid.log), deleting the file after the
         backend completes.
      3. Catches all exceptions, propagates them to the frontend by printing to
         stdout, and prints the full traceback to the backend error log.
    """
    with pidfile() as _:
        try:
            from .shared import _g
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
    opt_result = optimfn(acquire_nmr, scaled_x0, scaled_xtol,
                         scaled_lb, scaled_ub,
                         args=optimargs, maxfev=_g.maxfev)

    # Tell frontend script that the optimisation is done
    best_values = unscale(opt_result.xbest, routine.lb,
                          routine.ub, routine.tol, scaleby="tols")
    print(f"optima: {' '.join([str(i) for i in best_values])}")
    # Strip newlines from the opt result message, just in case (because the
    # frontend only expects one line of text here, feeding it more than one
    # line of text will confuse it)
    print(opt_result.message.replace("\n", " ").replace("\r", " "))

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


def get_routine_cf(routine_id, p_routine_dir=None):
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
    """
    # Load the routine.
    p_routine_dir = p_routine_dir or (_g.p_poise / "routines")
    with open(p_routine_dir / (routine_id + ".json"), "rb") as f:
        routine = Routine(**json.load(f))

    # Load the cost function. Try to get from user first.
    cost_function = getattr(costfunctions_user, routine.cf, None)
    # If it failed, get from system.
    if cost_function is None:
        cost_function = getattr(costfunctions, routine.cf, None)
    # If that failed too, then error out.
    if cost_function is None:
        raise AttributeError(f"No such cost function {routine.cf}.")
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

    with open(_g.p_optlog, "a") as logf:
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
            print(fstr.format(*unscaled_val, cf_val), file=logf)
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
            _g.nfev += 1
            fstr = "{:^10.4f}  " * (len(x) + 1)
            try:
                cf_val = cost_function()
            except CostFunctionError as e:
                # Log the point and cost function
                if isinstance(e.cf_val, (int, float)):
                    print(fstr.format(*unscaled_val, e.cf_val), file=logf)
                else:
                    fstr2 = "{:^10.4f}  " * len(x)
                    print(fstr2.format(*unscaled_val), file=logf)
                # Log the exception and return control to optimiser.
                print(e.message, file=logf)
                raise
            else:
                print(fstr.format(*unscaled_val, cf_val), file=logf)
                print(f"cf: {cf_val}")  # send back to frontend
                return cf_val    # return control to optimiser
        else:
            # This really shouldn't happen.
            raise ValueError(f"Invalid signal passed from frontend: {signal}")


if __name__ == "__main__":
    main_wrapper()
