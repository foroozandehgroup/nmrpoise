Installation
============

POISE comprises a *frontend* script, which is accessible from within TopSpin itself, as well as a *backend* script, which has to be run using Python 3 (i.e. not TopSpin's native Python interpreter).

This means that Python 3 must be installed separately first.
In particular, POISE requires a minimum version of **Python 3.6.**
For Windows, your best bet is to download an installer from `the Python website <https://www.python.org/downloads/>`_.
For Unix machines, we suggest using a package manager to do so (such as Homebrew for macOS or ``apt``/``yum`` & their equivalents on Linux), although the installers are also fine.

Once that's done, you can install POISE using ``pip`` (replace ``python`` with ``python3`` if necessary)::

    python -m pip install nmrpoise

The package requirements are ``numpy``, ``scipy``, ``pandas``, and ``Py-BOBYQA``; these will be automatically downloaded if necessary.

``pip`` tries to take care of installing the scripts to your TopSpin directory.
To do so, it checks for TopSpin installations in standard directories (``/opt`` on Unix and ``C:\Bruker`` on Windows).
If ``pip`` exits without errors, this should have succeeded; you can test it by typing ``poise -h`` into TopSpin's command-line, which should spawn a popup.
If that is the case, congratulations — you can move on to the next chapter, `routines`.


Updating POISE
--------------

Simply use::

    python -m pip install --upgrade nmrpoise --no-cache-dir

(again replacing ``python`` with ``python3`` if necessary). All other steps (including troubleshooting, if necessary) are the same.


Troubleshooting
---------------

If you are reinstalling POISE (either using the ``--upgrade`` flag, or after uninstalling it), make sure to add the ``--no-cache-dir`` flag to ``pip install``.
In other words, run ``python -m pip install nmrpoise --no-cache-dir``.
(The reason for this is because if ``pip`` uses a pre-built wheel to install POISE, the TopSpin files will not be installed.
When POISE is installed for the first time, ``pip`` will create a wheel, and subsequent installations will use the wheel and fail to install the TopSpin files, *unless* the ``-no-cache-dir`` flag is passed.
There is a `possible workaround <https://stackoverflow.com/q/58289062/7115316>`_ for this to prevent wheels from ever being built, but even though this allows installation to complete successfully, it shows the user some scary red text in the process, which I'd rather not.)

Apart from this, the installation can occasionally fail if TopSpin is installed to a non-standard location.
To solve this issue, you can specify the TopSpin installation directory as an environment variable ``TSDIR`` before installing POISE.
The way to do this depends on what operating system (and shell) you use.

On Windows PowerShell, run the following command:

.. code-block:: powershell

    $env:TSDIR = "C:\Bruker\TopSpinX.Y.Z\exp\stan\nmr"

replacing the part in quotes with your actual TopSpin installation directory (it must point to the ``exp/stan/nmr`` folder).

On old-school Windows ``cmd``, use:

.. code-block:: batch

    set TSDIR="C:\Bruker\TopSpinX.Y.Z\exp\stan\nmr"

On Unix systems, use:

.. code-block:: bash

    export TSDIR="/opt/topspinX.Y.Z/exp/stan/nmr"

(Unless you're using ``csh`` or the like, in which case you use ``setenv``, although you probably didn't need to be told that!)

After running the appropriate command for your operating system, ``pip install nmrpoise`` should be able to detect the ``TSDIR`` environment variable and install the scripts accordingly.

From source
-----------

If you obtained the source code (e.g. from ``git clone`` or a `GitHub release <https://github.com/foroozandehgroup/nmrpoise/releases>`_) and want to install from there, simply ``cd`` into the top-level ``nmrpoise`` directory and run::

   pip install .

or equivalently::

   python setup.py install

The installation to the TopSpin directory is subject to the same considerations as above.


Without an internet connection
------------------------------

If your spectrometer does not have an Internet connection, then the installation becomes a bit more protracted.
On a computer that *does* have an Internet connection:

1. Make a new folder.
2. Download the CPython installer for the spectrometer operating system. Place it in that folder.
3. ``cd`` to the folder and run these commands::

      pip download Py-BOBYQA nmrpoise --no-deps --no-binary=:all:
      pip download numpy pandas scipy --only-binary=:all: --python-version <3.X> --platform <PLATFORM>

   where ``<3.X>`` is the version of Python to be installed on the spectrometer, and ``<PLATFORM>`` is one of ``win32``, ``win_amd64``, ``macosx_10_9_x86_64``, or ``manylinux1_x86_64`` depending on the spectrometer operating system. (n.b. These options are not well-documented; I have figured them out by trawling Stack Overflow. Any additions are welcome.)

4. Copy the whole folder over to your spectrometer. It should contain a bunch of ``.whl`` files and two ``.tar.gz`` files.

Now, on the spectrometer:

1. Install CPython with the installer.
2. ``cd`` to the folder and run ::
    
      pip install ./nmrpoise-<VERSION>.tar.gz --no-index --find-links .

   (replace ``<VERSION>`` with whichever version you downloaded).

It should then install properly, unless your TopSpin installation location is non-standard: in that case, set the ``$TSDIR`` environment variable (described above) before retrying Step 2.
