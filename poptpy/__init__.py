import json
import re

import pandas as pd


def _parse_poptpy_log(fname, logtype="new"):
    """
    Parse a poptpy.log file.

    Arguments:
        fname (str or pathlib.Path) : Path to poptpy.log file, or the folder
                                      containing it (this would be the TopSpin
                                      EXPNO folder).
        logtype (str)               : "old" or "new". Old log files don't
                                      contain information about the lower and
                                      upper bounds, as well as tolerances.
                                      WARNING: This will be deprecated in
                                      future. It mainly exists because I need
                                      it to analyse some of my own data which
                                      did not have this information in the
                                      log files.

    Returns:
        pandas DataFrame object. Rows correspond to optimisations which
        successfully terminated. The time taken is given in seconds.
    """
    empty_run = {"routine": None, "init": None, "cf": None, "algo": None,
                 "lb": None, "ub": None, "tol": None,
                 "best": None, "feval": None, "elapsed": None,
                 }
    current_run = dict(empty_run)  # make a copy
    all_runs = []   # List of all successful optimisation runs

    if logtype not in ["new", "old"]:
        raise ValueError("logtype can only be 'new' or 'old'.")

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
            if logtype == "new" and not any(i is None
                                            for i in current_run.values()):
                all_runs.append(current_run)
                current_run = dict(empty_run)
            elif logtype == "old" and not \
                any(i is None for i in [current_run["init"],
                                        current_run["cf"],
                                        current_run["algo"],
                                        current_run["best"],
                                        current_run["feval"],
                                        current_run["elapsed"]]):
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
            elif line.startswith("Optimisation algorithm"):
                current_run["algo"] = line.split("-", maxsplit=1)[1].strip()
            elif line.startswith("Best values found"):
                current_run["best"] = parse_list_params(line)
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
    if logtype == "new" and not any(i is None
                                    for i in current_run.values()):
        all_runs.append(current_run)
        current_run = dict(empty_run)
    elif logtype == "old" and not \
        any(i is None for i in [current_run["init"],
                                current_run["cf"],
                                current_run["algo"],
                                current_run["best"],
                                current_run["feval"],
                                current_run["elapsed"]]):
        all_runs.append(current_run)

    # Construct dataframe and return.
    data = {}
    if logtype == "new":
        data["routine"] = [run["routine"] for run in all_runs]
    data["initial"] = [run["init"] for run in all_runs]
    if logtype == "new":
        data["param"] = [run["param"] for run in all_runs]
        data["lb"] = [run["lb"] for run in all_runs]
        data["ub"] = [run["ub"] for run in all_runs]
        data["tol"] = [run["tol"] for run in all_runs]
    data["algorithm"] = [run["algo"] for run in all_runs]
    data["costfn"] = [run["cf"] for run in all_runs]
    data["optimum"] = [run["best"] for run in all_runs]
    data["nfev"] = [run["feval"] for run in all_runs]
    data["time"] = [run["elapsed"] for run in all_runs]
    return pd.DataFrame(data=data)


def parse_poptpy_log(fname):
    """
    Interface to the private function, because nobody should really have to use
    the 'logtype' parameter except me.
    """
    return _parse_poptpy_log(fname=fname, logtype="new")
