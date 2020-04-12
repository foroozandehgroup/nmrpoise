# poptpy

A series of Python scripts for the numerical optimisation of NMR parameters, running in Bruker's TopSpin software.

## Prerequisites

1. **Python 3 installation** (download from https://www.python.org/downloads/). Ideally, the Python 3 executable (`python3` or `python`) should be placed in the `$PATH` environment variable.
2. The **numpy, scipy and dill** packages. These can all be installed using `pip3` or `pip`.

## Installation (MacOS / Linux)

1. Clone this repository: `git clone https://github.com/yongrenjie/poptpy`
2. `cd` inside and run `./install.sh`
3. The script will try to automatically detect the path to your Python 3 executable (using `which`), as well as the TopSpin installation directory (it searches inside `/opt`). If either of these are not in the typical location, you can set the environment variables `$PY3PATH` and `$TOPSPINDIR` when running the installer. For example:

       PY3PATH="/path/to/python3" TOPSPINDIR="/path/to/exp/stan/nmr" ./install.sh

   Note that `$TOPSPINDIR` should point to the `.../exp/stan/nmr` folder in TopSpin.

## Installation (manual)

1. Clone this repository: `git clone https://github.com/yongrenjie/poptpy`
2. Specify the path to the Python 3 executable by modifying the `p_python3` variable in the Python scripts. This occurs near the top of both `poptpy.py` and `poptpy_makecf.py`.
3. Specify the path to the TopSpin directory (this is the `p_tshome` variable). This occurs near the top of `poptpy_makecf.py` only.
4. Copy `poptpy.py` and `poptpy_makecf.py` to TopSpin's `/exp/stan/nmr/py/user` directory, and copy `poptpy_be.py` to `/exp/stan/nmr/py/user/poptpy` (you will need to make the folder first).

------------------------------------------------------

## Running an optimisation

### Setting up a cost function

A number of pre-built cost functions have already been created, which can cover many simple use cases. These will be fully documented in due course. If all you need is one of these, then you can skip this section entirely.

However, one of the strengths of `poptpy` is its inherent flexibility: one can construct any cost function using the tools offered by the `numpy` package (as well as some custom functions). To create a new cost function, edit the file `.../py/user/poptpy_makecf.py`, either in TopSpin (`edpy poptpy_makecf`) or with a text editor of choice. There are further instructions in the script itself, as well as brief documentation of the custom functions available. Essentially:

- the name of the cost function must be specified (the `cf_name` variable);
- the function returning the cost (`f()`) must be written.

Once this is done, run the script (either from within TopSpin, or with external Python 3). A cost function object will be created in the directory `.../py/user/cost_functions` with the specified name.

More precisely, the script instantiates a `Cost_Function` object and then serialises it using the `dill` package (an extension of Python's built-in `pickle`). This object can later be read by the backend script.

### Performing an optimisation

In order to carry out an optimisation, you must specify several pieces of information, namely:

1. The **parameters** to be optimised (e.g. `p1`).
2. The **lower and upper bounds** (e.g. approximately `35` and `45`, if one is calibrating the length of a 360-degree pulse).
3. The **initial values** (this should be your best guess at the final answer).
4. The **tolerances** (how much of a difference from the "true" answer you are willing to accept).
5. The **cost function** (what function you will use to evaluate the "goodness" of a spectrum. Since this quantity is *minimised*, the lower this is, the better the spectrum is: so technically it measures the "badness" of a spectrum).

In this programme, a collection of these five items is referred to as a **routine**. Routines can be stored and ran multiple times (e.g. on different samples). On top of the five items listed, each routine is also associated with a name.

`poptpy` should be run from within TopSpin (simply type `poptpy` into the TopSpin command line). The first time you run `poptpy`, it will prompt you to create a new routine. Once a routine has been created, however, it is stored (technically `pickle`'d) in the directory `.../py/user/poptpy/routines`, and can be selected for reuse in future runs (`poptpy` will recognise the presence of a stored routine).

*[Tip: when entering minimum and maximum values for parameters you can use (e.g.) 2m to denote 2 milliseconds, just like in TopSpin. You cannot, however, perform any arithmetic, because that would necessitate `eval` (or a complicated expression parsing routine) and we would prefer to avoid that.]*

Once a routine has been specified or created, the optimisation will take place, largely in the background. **We strongly recommend turning on TopSpin's "unsafe ZG" option (TopSpin preferences > Acquisition), at least while running the optimisation:** otherwise, on *every* function evaluation, TopSpin will ask for confirmation as to whether you really want to acquire a new spectrum.

When the optimisation is complete, the best values found will be displayed and also stored in TopSpin's parameter lists (usually `ased`, for most acquisition parameters) for future retrieval.

There is an optimisation log that is kept at `.../py/user/poptpy/poptpy.log`. This documents how the cost function varies with the parameters and can be useful in troubleshooting optimisations, or for plotting graphs to show the optimisation trajectory.

If the optimisation crashes or is otherwise unresponsive, you can use the TopSpin `kill` function to terminate it. Any errors raised by the backend script will be printed to `.../py/user/poptpy/poptpy_err.log` (technically, `stderr` is redirected to this file). To report a bug, please submit an issue with steps to reproduce it, and attach the the contents of this log file.

