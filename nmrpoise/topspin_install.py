import os
import sys
from distutils.dir_util import copy_tree
from distutils.file_util import copy_file
import platform
from pathlib import Path
from glob import glob


def main():
    """
    Attempts to install poise to TopSpin directory.
    """
    dirname = Path(__file__).parent.resolve()

    osname = platform.system()
    if osname in ["Darwin", "Linux"]:
        ostype = "unix"
    elif osname in ["Windows"]:
        ostype = "win"
    else:
        raise OSError("Unsupported operating system. "
                      "Please perform a manual installation.")

    # Set path to Python executable in poise.py
    poise_py = dirname / "poise.py"
    poise_backend = dirname / "poise_backend"
    poise_py_out = dirname / "poise.py.out"
    # Iterate over lines in poise.py and print them to poise.py.out
    # Essentially this is sed -i behaviour.
    # open() only takes Path objects in >= 3.6
    with open(str(poise_py), "r") as infile, \
            open(str(poise_py_out), "w") as outfile:
        for line in infile:
            if line.startswith("p_python3 = "):
                line = f"p_python3 = r\"{Path(sys.executable)}\""
            # Use rstrip() to remove extra newlines since print() already
            # includes one for us.
            print(line.rstrip(), file=outfile)
    # Replace the old file with the new file.
    copy_file(str(poise_py_out), str(poise_py), verbose=1)

    # Find TopSpin installation path(s).
    ts_paths = get_topspin_path(ostype)
    for ts_path in ts_paths:
        ts_backend_path = ts_path / "poise_backend"
        # Copy files to TopSpin path.
        copy_file(str(poise_py), str(ts_path), verbose=1)
        copy_tree(str(poise_backend), str(ts_backend_path), verbose=1)
    print("topspin_install.py: completed")


def get_topspin_path(ostype):
    """
    First searches the environment variable TSDIR and returns that if it is
    a valid path.

    Otherwise, tries to find the path to the most recent TopSpin directory.
    Searches under /opt on Unix/Linux systems, or under C:\\Bruker on Windows.

    Returns a list of Path objects pointing to /exp/stan/nmr/py/user for each
    TopSpin directory found.

    Raises RuntimeError if none are found.
    """
    invalid_envvar_error = (
        "The TopSpin installation directory was specified as the environment "
        "variable TSDIR, but it was not a valid path.\n\n"
        "Please make sure that TSDIR points to the ../exp/stan/nmr folder in "
        "TopSpin."
    )
    no_tsdir_unix_error = (
        "A valid TopSpin installation directory was not found.\n"
        "Please set it using the TSDIR environment variable:\n\n"
        "\texport TSDIR=/opt/topspinX.Y.Z/exp/stan/nmr\n"
    )
    no_tsdir_win_error = (
        "A valid TopSpin installation directory was not found.\n"
        "Please set it using the TSDIR environment variable:\n\n"
        "\t$env:TSDIR = \"C:\\Bruker\\TopSpinX.Y.Z\\exp\\stan\\nmr\"\n"
    )
    if "TSDIR" in os.environ:
        ts = os.environ["TSDIR"]    # KeyError if not provided
        py_user = ts / "py" / "user"
        if not ts.is_dir() and py_user.is_dir():
            raise RuntimeError(invalid_envvar_error)
        ts_paths = [py_user]
    else:
        if ostype == "unix":
            glob_query = "/opt/topspin*/exp/stan/nmr"
        elif ostype == "win":
            glob_query = r"C:\Bruker\TopSpin*\exp\stan\nmr"
        dirs = glob(glob_query)

        if len(dirs) == 0:              # No TopSpin folders found
            if ostype == "unix":
                raise RuntimeError(no_tsdir_unix_error)
            if ostype == "win":
                raise RuntimeError(no_tsdir_win_error)
        else:
            # Convert to pathlib.Path
            dirs = [Path(dir) / "py" / "user" for dir in dirs]
            # Filter out invalid paths
            ts_paths = [dir for dir in dirs if dir.is_dir()]
            # Error out if no valid ones were found
            if ts_paths == []:
                if ostype == "unix":
                    raise RuntimeError(no_tsdir_unix_error)
                if ostype == "win":
                    raise RuntimeError(no_tsdir_win_error)

    print("topspin_install.py: found TopSpin paths", ts_paths)
    return ts_paths


if __name__ == "__main__":
    main()
