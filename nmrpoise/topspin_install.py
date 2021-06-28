"""
topspin_install.py
------------------

Script which carries out installation of POISE files to TopSpin directories.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import os
import sys
from shutil import copy2 as cp
import platform
from pathlib import Path
from glob import glob


# AU scripts to be automatically installed with POISE.
CORE_AU_SCRIPTS = ["poise_1d", "poise_2d", "poise_1d_noapk", "poisecal"]


def cp_r(src, dest):
    """
    Recursively copies src to dest.

    This is a reimplementation of shutil.copytree(dirs_exist_ok=True), because
    the dirs_exist_ok keyword argument is not available in Python <=3.7. The
    ignore pattern is hardcoded.

    Modified from https://stackoverflow.com/a/15824216/7115316.
    """
    if os.path.isdir(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        files = os.listdir(src)
        for f in files:
            if f not in ["costfunctions_user.py"]:
                cp_r(os.path.join(src, f), os.path.join(dest, f))
    else:
        cp(src, dest)


def get_ostype():
    """
    Attempts to find out the operating system that it's running on. This
    influences the glob pattern used when searching for the TopSpin directory,
    as well as the error message that is shown.

    Parameters
    ----------
    None

    Returns
    -------
    ostype: str
        "unix" or "win".
    """
    osname = platform.system()
    if osname in ["Darwin", "Linux"]:
        return "unix"
    elif osname in ["Windows"]:
        return "win"
    else:
        raise OSError("Unsupported operating system. "
                      "Please perform a manual installation.")


def main():
    """
    Attempts to install poise's core scripts (frontend and beckend) to TopSpin
    directory. This function also makes sure to replace p_python3 (the path to
    the Python 3 executable) in the frontend script.

    Also installs the poisecal AU script, for good measure. It's a pretty
    useful part of the package and showcases POISE's capabilities well.

    Parameters
    ----------
    None

    Returns
    -------
    None
    """
    dirname = Path(__file__).parent.resolve()
    ostype = get_ostype()
    ts_paths = get_topspin_path(ostype)

    # Set path to Python executable in poise.py
    poise_py = dirname / "poise.py"
    poise_backend = dirname / "poise_backend"
    poise_py_out = dirname / "poise.py.out"
    # Iterate over lines in poise.py and print them to poise.py.out
    # Essentially this is sed -i behaviour.
    with open(poise_py, "r") as infile, open(poise_py_out, "w") as outfile:
        for line in infile:
            if line.startswith("p_python3 = "):
                line = f"p_python3 = r\"{Path(sys.executable)}\""
            # Use rstrip() to remove extra newlines since print() already
            # includes one for us.
            print(line.rstrip(), file=outfile)
    # Copy the new file over the old file.
    cp(poise_py_out, poise_py)

    # Copy the files to TopSpin's directories.
    for ts_path in ts_paths:
        ts_user_path = ts_path / "py" / "user"
        ts_backend_path = ts_path / "py" / "user" / "poise_backend"
        # Copy poise.py and poise_backend/ to TopSpin path, except for
        # costfunctions_user.py (which is hardcoded as an exception in cp_r()).
        cp(poise_py, ts_user_path)
        cp_r(poise_backend, ts_backend_path)
        # Copy costfunctions_user.py but only if it's not found.
        cf_user_path = poise_backend / "costfunctions_user.py"
        ts_cf_user_path = ts_backend_path / "costfunctions_user.py"
        if not ts_cf_user_path.exists():
            cp(cf_user_path, ts_cf_user_path)
        # Copy core AU scripts over. The others can be installed with
        # poise_addons.
        ts_au_user_path = ts_path / "au" / "src" / "user"
        for auscript in CORE_AU_SCRIPTS:
            src = dirname / "au" / auscript
            dest = ts_au_user_path / auscript
            cp(str(src), str(dest))
    print("topspin_install.py: completed")


def get_topspin_path(ostype):
    """
    Searches for the path to the TopSpin /exp/stan/nmr folder(s).

    First searches the environment variable TSDIR and returns that if it is a
    valid path. Otherwise, tries to find the path to the most recent TopSpin
    directory.  Searches under /opt on Unix/Linux systems, or under C:\\Bruker
    on Windows.

    Parameters
    ----------
    ostype : str
        "unix" or "win". The string returned by get_ostype().

    Returns
    -------
    tsdirs : list of pathlib.Path
        Every /exp/stan/nmr directory found. This can be more than one if there
        is more than one version of TopSpin installed.

    Raises
    ------
    RuntimeError
        If no paths were found. We need to throw an error so that the pip
        installation fails.
    """
    INVALID_ENVVAR_ERROR = (
        "The TopSpin installation directory was specified as the environment "
        "variable TSDIR, but it was not a valid path.\n\n"
        "Please make sure that TSDIR points to the ../exp/stan/nmr folder in "
        "TopSpin."
    )
    NO_TSDIR_UNIX_ERROR = (
        "A valid TopSpin installation directory was not found.\n"
        "Please set it using the TSDIR environment variable:\n\n"
        "\texport TSDIR=/opt/topspinX.Y.Z/exp/stan/nmr\n"
    )
    NO_TSDIR_WIN_ERROR = (
        "A valid TopSpin installation directory was not found.\n"
        "Please set it using the TSDIR environment variable:\n\n"
        "\t$env:TSDIR = \"C:\\Bruker\\TopSpinX.Y.Z\\exp\\stan\\nmr\"\n"
    )
    if "TSDIR" in os.environ:
        ts = os.environ["TSDIR"]    # KeyError if not provided
        py_user = ts / "py" / "user"
        if not ts.is_dir() and py_user.is_dir():
            raise RuntimeError(INVALID_ENVVAR_ERROR)
        dirs = [ts]
    else:
        if ostype == "unix":
            glob_query = "/opt/topspin*/exp/stan/nmr"
        elif ostype == "win":
            glob_query = r"C:\Bruker\TopSpin*\exp\stan\nmr"
        dirs = glob(glob_query)

        if len(dirs) == 0:              # No TopSpin folders found
            if ostype == "unix":
                raise RuntimeError(NO_TSDIR_UNIX_ERROR)
            if ostype == "win":
                raise RuntimeError(NO_TSDIR_WIN_ERROR)
        else:
            # Convert to pathlib.Path and filter out invalid entries
            dirs = [Path(dir) for dir in dirs
                    if (Path(dir) / "py" / "user").is_dir()]
            # Error out if no valid ones were found
            if dirs == []:
                if ostype == "unix":
                    raise RuntimeError(NO_TSDIR_UNIX_ERROR)
                if ostype == "win":
                    raise RuntimeError(NO_TSDIR_WIN_ERROR)

    print("topspin_install.py: found TopSpin paths", dirs)
    return dirs


if __name__ == "__main__":
    main()
