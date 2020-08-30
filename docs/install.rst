Installation
============

POISE comprises a *frontend* script, which is accessible from within TopSpin itself, as well as a *backend* script, which has to be run using Python 3 (i.e. not TopSpin's native Python interpreter).

This means that Python 3 must be installed separately first.
In particular, POISE requires a minimum version of **Python 3.6.**
For Windows, your best bet is to download an installer from `the Python website <https://www.python.org/downloads/>`_.
For Unix machines, we suggest using a package manager to do so (such as Homebrew for macOS), although the installers will also work. 

Once that's done, you can install POISE using ``pip``::

    pip install nmrpoise

The package requirements are ``numpy``, ``scipy``, ``pandas``, and ``Py-BOBYQA``; these will be automatically downloaded if necessary.

``pip`` tries to take care of installing the scripts to your TopSpin directory. If ``pip`` exits without errors, this should have succeeded; you can test it by typing ``poise -h`` into TopSpin's command-line, which should spawn a popup.

-----

However, this can occasionally fail if TopSpin is installed to a non-standard location.
To solve this issue, you can specify the TopSpin installation directory as an environment variable ``TSDIR`` before installing POISE.
The way to do this depends on what operating system (and shell) you use.

On Windows PowerShell, run the following command::

    $env:TSDIR = "C:\Bruker\TopSpinX.Y.Z\exp\stan\nmr"

replacing the part in quotes with your actual TopSpin installation directory (it must point to the ``exp/stan/nmr`` folder).

On old-school Windows ``cmd``, use::

    set TSDIR="C:\Bruker\TopSpinX.Y.Z\exp\stan\nmr"

On Unix systems, use::

    export TSDIR="/opt/topspinX.Y.Z/exp/stan/nmr"

After running the appropriate command for your operating system, ``pip install nmrpoise`` should be able to detect the ``TSDIR`` environment variable and install the scripts accordingly.
