# poptpy

[![Documentation Status](https://readthedocs.org/projects/poptpy/badge/?version=latest)](https://poptpy.readthedocs.io/en/latest/?badge=latest)
[![Travis CI Build Status](https://travis-ci.com/yongrenjie/poptpy.svg?branch=master)](https://travis-ci.com/github/yongrenjie/poptpy)

A series of Python scripts for the numerical optimisation of NMR parameters, running in Bruker's TopSpin software.

Documentation is hosted at https://poptpy.readthedocs.io/.


## Installation

poptpy can be installed using ``pip`` (please see [the documentation](https://poptpy.readthedocs.io/en/latest/install/) for other options):

    pip install ts-poptpy

If ``pip`` does not work out of the box, chances are that it is because you have multiple TopSpin installations, or a non-standard installation directory. To get round this, set the environment variable `TSDIR` to point to TopSpin's `exp/stan/nmr` folder:

    export TSDIR="/opt/topspinX.Y.Z/exp/stan/nmr"        # Unix / Linux
    $env:TSDIR = "C:\Bruker\TopSpinX.Y.Z\exp\stan\nmr"   # Windows PowerShell
