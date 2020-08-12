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
    # Set path to Python executable in poise.py
    poise_py = dirname / "nmrpoise" / "poise.py"
    poise_backend = dirname / "nmrpoise" / "poise_backend"
    poise_py_out = dirname / "nmrpoise" / "poise.py.out"
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
    ts_paths = get_topspin_path()
    for ts_path in ts_paths:
        ts_backend_path = ts_path / "poise_backend"
        # Copy files to TopSpin path.
        copy_file(str(poise_py), str(ts_path), verbose=1)
        copy_tree(str(poise_backend), str(ts_backend_path), verbose=1)
    print("topspin_install.py: completed")


def get_topspin_path():
    """
    First searches the environment variable TSDIR and returns that if it is
    a valid path.

    Otherwise, tries to find the path to the most recent TopSpin directory.
    Searches under /opt on Unix/Linux systems, or under C:\\Bruker on Windows.

    Returns a list of Path objects pointing to /exp/stan/nmr/py/user for each
    TopSpin directory found.

    Raises RuntimeError if none are found.
    """
    invalid_envvar_error = ("TopSpin installation directory was specified as "
                            "the environment variable TSDIR, but was not a "
                            "valid path.\n\n"
                            "Please make sure that TSDIR points to the "
                            "../exp/stan/nmr folder in TopSpin.")
    tsdir_notfound_error = ("A valid TopSpin installation directory was not found.\n"
                            "Please set it using the TSDIR environment "
                            "variable:\n\n"
                            "\tTSDIR=/opt/topspinX.Y.Z/exp/stan/nmr pip "
                            "install nmrpoise    # Unix/Linux\n\n"
                            "or\n\n"
                            "\t$env:TSDIR = \"C:\\Bruker\\TopSpinX.Y.Z\\"
                            "exp\\stan\\nmr\"\n")
    if "TSDIR" in os.environ:
        ts = os.environ["TSDIR"]    # KeyError if not provided
        py_user = ts / "py" / "user"
        if not ts.is_dir() and py_user.is_dir():
            raise RuntimeError(invalid_envvar_error)
        ts_paths = [py_user]
    else:
        if unix:
            glob_query = "/opt/topspin*/exp/stan/nmr"
        elif win:
            glob_query = r"C:\Bruker\TopSpin*\exp\stan\nmr"
        dirs = glob(glob_query)

        if len(dirs) == 0:              # No TopSpin folders found
            raise RuntimeError(tsdir_notfound_error)
        else:
            # Convert to pathlib.Path
            dirs = [Path(dir) / "py" / "user" for dir in dirs]
            # Filter out invalid paths
            ts_paths = [dir for dir in dirs if dir.is_dir()]
            # Error out if no valid ones were found
            if ts_paths == []:
                raise RuntimeError(tsdir_notfound_error)

    print("topspin_install.py: found TopSpin paths", ts_paths)
    return ts_paths


if __name__ == "__main__":
    dirname = Path(__file__).parent.resolve()

    osname = platform.system()
    unix = osname in ["Darwin", "Linux"]
    win = osname in ["Windows"]

    if not unix and not win:
        raise OSError("Unsupported operating system. "
                      "Please perform a manual installation.")
    else:
        main()
