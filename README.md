# pypopt

A series of Python scripts for the numerical optimisation of NMR parameters, running in Bruker's TopSpin software.

## Prerequisites

1. **Python 3 installation** (download from https://www.python.org/downloads/). Ideally, the Python 3 executable (`python3` or `python`) should be placed in the `$PATH` environment variable.
2. The **numpy, scipy and dill** packages. These can all be installed using `pip3` or `pip`.

## Installation (MacOS / Linux)

1. Clone this repository: `git clone https://github.com/yongrenjie/pypopt`
2. `cd` inside and run `./install.sh`
3. The script will try to automatically detect the path to your Python 3 executable (using `which`), as well as the TopSpin installation directory (it searches inside `/opt`). If either of these are not in the typical location, you can set the environment variables `$PY3PATH` and `$TOPSPINDIR` before running the installer. Note that `$TOPSPINDIR` should point to the `.../exp/stan/nmr` folder in TopSpin.

## Installation (manual)

1. Clone this repository: `git clone https://github.com/yongrenjie/pypopt`
2. Specify the path to the Python 3 executable by modifying the `p_python3` variable in the Python scripts. This occurs near the top of both `pypopt.py` and `pypopt-makecf.py`.
3. Specify the path to the TopSpin directory (this is the `p_tshome` variable). This occurs near the top of both `pypopt-be.py` and `pypopt-makecf.py`.
4. Copy `pypopt.py` and `pypopt-makecf.py` to TopSpin's `/exp/stan/nmr/py/user` directory, and copy `pypopt-be.py` to `/exp/stan/nmr/py/user/pypopt` (you will need to make the folder first).

## Running

To be written...
