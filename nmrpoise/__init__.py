"""
SPDX-License-Identifier: GPL-3.0-or-later
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


def parse_log(fname="."):
    """
    Parse a poise.log file.

    Parameters
    ----------
    fname : |Path| or str or int, optional
        Path to poise.log file, or the folder containing it (this would be the
        TopSpin EXPNO folder). If an int is passed, it is interpreted as the
        string "./<fname>" (i.e.  expno X in the current working directory). If
        not specified, defaults to the current working directory.

    Returns
    -------
    log_df : :class:`DataFrame <pandas.DataFrame>`
        DataFrame with rows corresponding to optimisations which successfully
        terminated. The time taken is given in seconds.
    """
    # Handle the int case
    if isinstance(fname, int):
        fname = f"./{fname}"
    # Check if the file exists
    fname = Path(fname).resolve()
    if fname.is_dir():
        fname = fname / "poise.log"
    if not fname.exists():
        raise FileNotFoundError(f"The log file '{fname}' was not found.")

    empty_run = {"routine": None, "init": None, "cf": None, "algo": None,
                 "au": None, "lb": None, "ub": None, "tol": None,
                 "xbest": None, "feval": None, "elapsed": None,
                 }
    current_run = dict(empty_run)  # make a copy
    all_runs = []   # List of all successful optimisation runs

    def parse_list_params(line):
        """
        Extracts init, lb, ub, tol from the line.
        """
        # Get the second half of the line
        rhs = line.split("-", maxsplit=1)[1].strip()
        # Convert '[4.]' to '[4]', otherwise json.loads() trips up
        rhs = re.sub(r"\.([^\d])", r"\1", rhs)
        # Evaluate the string and remove the list if it's a singleton
        rhs = json.loads(rhs)
        return rhs[0] if len(rhs) == 1 else rhs

    with open(fname, "r") as fp:
        for line in fp:
            # Check if there is a completed optimisation stored.
            # If so, add it to all_runs then reset the current run.
            if current_run["elapsed"] is not None:
                all_runs.append(current_run)
                current_run = dict(empty_run)
            # Start of a new optimisation, reset all values
            if "===================" in line:
                current_run = dict(empty_run)
            # Parse lines
            elif line.startswith("Routine name"):
                current_run["routine"] = line.split("-", maxsplit=1)[1].strip()
            elif line.startswith("Optimisation parameters"):
                p = line.split("-", maxsplit=1)[1].strip().replace("'", '"')
                current_run["param"] = json.loads(p)
            elif line.startswith("Initial values"):
                current_run["init"] = parse_list_params(line)
            elif line.startswith("Lower bounds"):
                current_run["lb"] = parse_list_params(line)
            elif line.startswith("Upper bounds"):
                current_run["ub"] = parse_list_params(line)
            elif line.startswith("Tolerances"):
                current_run["tol"] = parse_list_params(line)
            elif line.startswith("Cost function  "):
                current_run["cf"] = line.split("-", maxsplit=1)[1].strip()
            elif line.startswith("AU programme"):
                current_run["au"] = line.split("-", maxsplit=1)[1].strip()
            elif line.startswith("Optimisation algorithm"):
                current_run["algo"] = line.split("-", maxsplit=1)[1].strip()
            elif line.startswith("Best values found"):
                current_run["xbest"] = parse_list_params(line)
            elif line.startswith("Cost function at"):
                fbest = line.split("-", maxsplit=1)[1].strip()
                current_run["fbest"] = float(fbest)
            elif line.startswith("Number of spectra ran"):
                feval = line.split("-", maxsplit=1)[1].strip()
                current_run["feval"] = int(feval)
            elif line.startswith("Total time taken"):
                elapsed = line.split("-", maxsplit=1)[1].strip()
                elapsed = [int(i) for i in elapsed.split(":")]
                current_run["elapsed"] = (3600*elapsed[0]
                                          + 60*elapsed[1]
                                          + elapsed[2])

    # Check one more time at the end of the file to make sure that the
    # last entry is recorded.
    if current_run["elapsed"] is not None:
        all_runs.append(current_run)
        current_run = dict(empty_run)

    # Construct dataframe and return.
    data = {}
    data["routine"] = [run["routine"] for run in all_runs]
    data["initial"] = [run["init"] for run in all_runs]
    data["param"] = [run["param"] for run in all_runs]
    data["lb"] = [run["lb"] for run in all_runs]
    data["ub"] = [run["ub"] for run in all_runs]
    data["tol"] = [run["tol"] for run in all_runs]
    data["algorithm"] = [run["algo"] for run in all_runs]
    data["costfn"] = [run["cf"] for run in all_runs]
    data["auprog"] = [run["au"] for run in all_runs]
    data["optimum"] = [run["xbest"] for run in all_runs]
    data["fbest"] = [run["fbest"] for run in all_runs]
    data["nfev"] = [run["feval"] for run in all_runs]
    data["time"] = [run["elapsed"] for run in all_runs]
    return pd.DataFrame(data=data)


def xmean(series):
    """
    An aggregator function that allows you to average lists in DataFrame
    columns. This is useful for analysing optimisation runs with multiple
    parameters.

    For example:

    >>> df = parse_log(logfile)
    >>> # works for 1D, but not for nD optimisations
    >>> df.groupby("algorithm").mean()
    >>> # works for all dimensions.
    >>> df.groupby("algorithm").agg(xmean)
    """
    return np.mean(np.array(series.to_list()), axis=0).tolist()
