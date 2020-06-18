import os
import sys
from distutils.dir_util import copy_tree
from distutils.file_util import copy_file
import platform
from pathlib import Path
from glob import glob


def main():
    """
    Attempts to install poptpy to TopSpin directory.
    """
    # Set path to Python executable in poptpy.py
    poptpy_py = dirname / "poptpy/poptpy.py"
    poptpy_backend = dirname / "poptpy/poptpy_backend"
    poptpy_py_out = dirname / "poptpy/poptpy.py.out"
    # Iterate over lines in poptpy.py and print them to poptpy.py.out
    # Essentially this is sed -i behaviour.
    # open() only takes Path objects in >= 3.6
    with open(str(poptpy_py), "r") as infile, \
            open(str(poptpy_py_out), "w") as outfile:
        for line in infile:
            if line.startswith("p_python3 = "):
                line = "p_python3 = r\"{}\"".format(Path(sys.executable))
            # Use rstrip() to remove extra newlines since print() already
            # includes one for us.
            print(line.rstrip(), file=outfile)
    # Replace the old file with the new file.
    # We need str() to support Python 3.5
    copy_file(str(poptpy_py_out), str(poptpy_py))

    # Find TopSpin installation path.
    ts_path = get_topspin_path()
    ts_backend_path = ts_path / "poptpy_backend"
    # Copy files to TopSpin path.
    copy_file(str(poptpy_py), str(ts_path))
    copy_tree(str(poptpy_backend), str(ts_backend_path))


def get_topspin_path():
    """
    First searches the environment variable TSDIR and returns that if it is
    a valid path.

    Otherwise, tries to find the path to the most recent TopSpin directory.
    Searches under /opt on Unix/Linux systems, or under C:\\Bruker on Windows.

    Returns the Path object pointing to /exp/stan/nmr/py/user.
    Raises RuntimeError if it's not found.
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
                            "install ts-poptpy    # Unix/Linux\n\n"
                            "or\n\n"
                            "\t$env:TSDIR = \"C:\\Bruker\\TopSpinX.Y.Z\\"
                            "exp\\stan\\nmr\"\n")
    if "TSDIR" in os.environ:
        ts = os.environ["TSDIR"]    # KeyError if not provided
        py_user = ts / "py" / "user"
        if not ts.is_dir() and py_user.is_dir():
            raise RuntimeError(invalid_envvar_error)
    else:
        if unix:
            glob_query = "/opt/topspin*/exp/stan/nmr"
        elif win:
            glob_query = r"C:\Bruker\TopSpin*\exp\stan\nmr"
        dirs = glob(glob_query)

        if len(dirs) == 0:              # No TopSpin folders found
            raise RuntimeError(tsdir_notfound_error)
        else:
            if len(dirs) > 1:
                print("Multiple TopSpin directories found. "
                      "Choosing the most recent version.\n")
            ts = Path(sorted(dirs)[-1])
            py_user = ts / "py" / "user"
            if not py_user.is_dir():
                raise RuntimeError(tsdir_notfound_error)

    return py_user


if __name__ == "__main__":
    dirname = Path(__file__).parent.resolve()
    poptpy_dirname = dirname / "poptpy"

    osname = platform.system()
    unix = osname in ["Darwin", "Linux"]
    win = osname in ["Windows"]

    if not unix and not win:
        raise OSError("Unsupported operating system. "
                      "Please perform a manual installation.")
    else:
        main()
