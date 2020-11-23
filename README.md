# Parameter Optimisation by Iterative Spectral Evaluation

[![GitHub Actions Build Status](https://github.com/foroozandehgroup/nmrpoise/workflows/build/badge.svg)](https://github.com/foroozandehgroup/nmrpoise/actions?query=workflow%3Abuild)
[![GitHub Actions Documentation Status](https://github.com/foroozandehgroup/nmrpoise/workflows/docs/badge.svg)](https://github.com/foroozandehgroup/nmrpoise/actions?query=workflow%3Adocs)
[![PyPI version](https://badge.fury.io/py/nmrpoise.svg)](https://badge.fury.io/py/nmrpoise)

Jonathan Yong and Mohammadali Foroozandeh, University of Oxford

---------

POISE is a Python package for the numerical optimisation of NMR parameters.
It works by iteratively acquiring NMR spectra with different parameters and using a cost function to determine the optimal point.

The frontend runs in Bruker's TopSpin software, and is connected to a Python 3 backend.
You will need a system installation of Python 3.6 or later.
With that, POISE can be installed using ``pip``:

    pip install nmrpoise

The documentation (far more thorough than this humble README) is hosted at https://foroozandehgroup.github.io/nmrpoise.
It contains complete instructions on how to set POISE up and use it.
