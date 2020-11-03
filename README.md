# Parameter Optimisation by Iterative Spectral Evaluation

[![Documentation Status](https://readthedocs.org/projects/nmrpoise/badge/?version=latest)](https://nmrpoise.readthedocs.io/en/latest/?badge=latest)
[![Travis CI Build Status](https://travis-ci.com/foroozandehgroup/nmrpoise.svg?branch=master)](https://travis-ci.com/github/foroozandehgroup/nmrpoise)
[![PyPI version](https://badge.fury.io/py/nmrpoise.svg)](https://badge.fury.io/py/nmrpoise)

Jonathan Yong and Mohammadali Foroozandeh, University of Oxford

---------

POISE is a Python package for the numerical optimisation of NMR parameters.
It works by iteratively acquiring NMR spectra with different parameters and using a cost function to determine the optimal point.

The frontend runs in Bruker's TopSpin software, and is connected to a Python 3 backend.
You will need a system installation of Python 3.6 or later.
With that, POISE can be installed using ``pip``:

    pip install nmrpoise

The documentation (far more thorough than this humble README) is hosted at https://nmrpoise.readthedocs.io/.
It contains complete instructions on how to set POISE up and use it.
