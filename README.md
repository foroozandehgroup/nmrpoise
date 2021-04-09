# Parameter Optimisation by Iterative Spectral Evaluation

[![GitHub Actions Build Status](https://github.com/foroozandehgroup/nmrpoise/workflows/build/badge.svg)](https://github.com/foroozandehgroup/nmrpoise/actions?query=workflow%3Abuild)
[![GitHub Actions Documentation Status](https://github.com/foroozandehgroup/nmrpoise/workflows/docs/badge.svg)](https://github.com/foroozandehgroup/nmrpoise/actions?query=workflow%3Adocs)
[![PyPI version](https://badge.fury.io/py/nmrpoise.svg)](https://badge.fury.io/py/nmrpoise)
[![License](https://img.shields.io/github/license/foroozandehgroup/nmrpoise)](https://www.gnu.org/licenses/gpl-3.0.en.html)
[![Zenodo DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.4660708.svg)](https://doi.org/10.5281/zenodo.4660708)

Jonathan Yong and Mohammadali Foroozandeh, University of Oxford

---------

### Overview

POISE is a Python package for the numerical optimisation of NMR parameters.
It works by iteratively acquiring NMR spectra with different parameters and using a cost function to determine the optimal point.

The software comprises two parts:

 - the user-facing **frontend**, which runs in Bruker's TopSpin software. It can be executed from the TopSpin command line, or called from an AU or Python script ([the documentation contains more instructions on this](https://foroozandehgroup.github.io/nmrpoise/automation/)).

 - the **backend**, which is hidden from the user; it runs on a system installation of Python 3.6+.

-----------

### Installation

Python 3.6 or later is required. Please download and install that first before proceeding.

POISE can be installed using ``pip``, which will install both components of POISE (if any errors occur, please see [the documentation](https://foroozandehgroup.github.io/nmrpoise/install/), or contact us):

    pip install nmrpoise

-----------

### Documentation

The documentation is hosted at https://foroozandehgroup.github.io/nmrpoise; it contains complete instructions on how to set POISE up and use it.

-----------

### Contact us

Any feedback, questions, or bugs? Please [create a GitHub issue](https://github.com/foroozandehgroup/nmrpoise/issues) or email us: we can be reached at `firstname.lastname@chem.ox.ac.uk`.
