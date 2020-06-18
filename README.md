[![Travis CI Build Status](https://travis-ci.com/yongrenjie/poptpy.svg?branch=master)](https://travis-ci.com/github/yongrenjie/poptpy)

# poptpy

A series of Python scripts for the numerical optimisation of NMR parameters, running in Bruker's TopSpin software.

## Prerequisites

1. **Python 3 installation** (download from https://www.python.org/downloads/, version >= 3.5). Make sure that the directory containing the Python 3 executable (`python3` or `python`) is added to the `$PATH` environment variable.
2. The **numpy** package (version >= 1.17.0). This can be installed using `pip` (or `pip3`).

## Automatic installation

`pip install ts-poptpy` should work out of the box for many systems.

The most probable reason for failure is if the path to the TopSpin installation cannot be uniquely identified. This can happen if TopSpin was installed to a non-standard location, or if multiple versions of TopSpin are installed. To fix this, provide an environment variable `TSDIR` which points to the `/exp/stan/nmr` folder in TopSpin. For example (modify paths as appropriate):

```Shell
TSDIR=/opt/topspinX.Y.Z/exp/stan/nmr pip install ts-poptpy      # Unix / Linux.
```

or

```Powershell
$env:TSDIR = "C:\Bruker\TopSpinX.Y.Z\exp\stan\nmr"              # Windows (Powershell). Please don't use cmd.exe
pip install ts-poptpy
```

should work.

Alternatively (especially for spectrometers which are not directly connected to the Internet), you can download the package (using `git clone` or from a [release](https://github.com/yongrenjie/poptpy/releases)), `cd` inside and run `python3 setup.py install`. If there are still issues with TopSpin directory selection, follow the instructions above to specify the `TSDIR` environment variable.

## Manual installation

1. Download the package (using `git clone` or from a [release](https://github.com/yongrenjie/poptpy/releases)).
2. Specify the path to the Python 3 executable by modifying the `p_python3` variable in `poptpy/poptpy.py`. Warning: if you are on Windows and the path includes backslashes, you will need to either escape the backslashes (`p_python3 = "C:\\path\\to\\python3"`) or use a raw string (`p_python3 = r"C:\path\to\python3"`).
3. Copy `poptpy/poptpy.py`, as well as the `poptpy/poptpy_backend` folder, to TopSpin's `/exp/stan/nmr/py/user` directory.

------------------------------------------------------

## Running an optimisation

### Setting up a cost function

A number of pre-built cost functions have already been created, which can cover many simple use cases. These will be fully documented in due course. If all you need is one of these, then you can skip this section entirely.

However, one of the strengths of `poptpy` is its inherent flexibility: one can construct any cost function using the tools offered by the `numpy` package (as well as some predefined custom functions). To create a new cost function, make a new Python file inside `.../py/user/poptpy/cost_functions` defining the cost function, saving it as `<CF_NAME>.py`. There are further instructions in the script itself, as well as brief documentation of the custom functions available.

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

There is an optimisation log `poptpy.log` that is stored in the same directory as the spectrum EXPNO. This documents how the cost function varies with the parameters and can be useful in troubleshooting optimisations, or for plotting graphs to show the optimisation trajectory.

If the optimisation crashes or is otherwise unresponsive, you can use the TopSpin `kill` function to terminate it. Any errors raised by the backend script will be printed to `.../py/user/poptpy/poptpy_err.log` (technically, `stderr` is redirected to this file). To report a bug, please submit an issue with steps to reproduce it, and attach the the contents of this log file.


------------------------------------------------------

## Developer notes

Most users will not need to read this section (indeed, perhaps nobody but myself needs to). However, if you are interested in contributing to development of `poptpy`, then some of this information may be helpful.

`poptpy` is packaged in a way which makes it installable via `pip`, but it is hardly a conventional Python module. For example, if you type `import poptpy` into the Python REPL, it *works*; but it won't actually give you access to any of the functions. Furthermore, the code is invariably rather messy because of the need to use both TopSpin's subroutines as well as ordinary Python code. (Although I have tried to comment liberally.)

Firstly, the installation is managed by `setuptools`, as with many Python packages. The `install` target in `setup.py` is manually overridden with a call to `install/INSTALL.py`, which detects the operating system and delegates to `install/install.sh` for Unix/Linux systems, and `install/install.ps1` for Windows systems. However, it also calls `super().run()`, which performs the usual task of installing some files to the usual Python `site-packages` directory. So, simply running `python3 setup.py install` essentially installs the programme to two separate directories.

The same is true if one were to run `pip3 install .` from the top-level poptpy directory, except that `pip3` also [purposely silences output](https://github.com/pypa/pip/issues/2732#issuecomment-97119093), unless an error occurs. Therefore, even though the appropriate installation script is ran, the output of those scripts is not printed to the terminal. This behaviour can be changed using `pip3 install -vvv .`. However, even with the `-vvv` flag, the installation will still not accept input. Therefore, if more than one TopSpin directory is detected, the installation will fail (ordinarily it would prompt the user to select one).

For development of `poptpy`, it is recommended to use a virtual environment. Unit tests can be run using `pytest` from the top-level directory. They are ran against the poptpy folder itself, so there is no need to install the package before running unit tests. The `__init__.py` file in `poptpy/` is just there so that `pytest` recognises where the package is stored. However, arguably the most important test is whether it works in TopSpin, and that cannot be done using `pytest`. Changes to the TopSpin interface, or the communication between front- and backend, cannot be tested unless the files are installed to the TopSpin directory. In order to test that you have to install "properly" using `pip3 install .` or `python3 setup.py install`.
