Developer notes
===============

Most users will not need to read this section (indeed, perhaps nobody but myself needs to).
However, if you are interested in contributing to development of ``poptpy``, then some of this information may be helpful.

Details about installation
--------------------------

The installation is managed by ``setuptools``, as with many Python packages.
The ``install`` target in ``setup.py`` is manually overridden with a call to ``topspin_install.py``, which attempts to locate the TopSpin directory and copy the necessary files.
Note that ``pip`` also `purposely silences output <ttps://github.com/pypa/pip/issues/2732#issuecomment-97119093>`_, unless an error occurs.
In order to see everything that is happening, use the ``-vvv`` flag with ``pip``.


Testing
-------

For development of ``poptpy``, it is recommended to use a virtual environment.
Further dependencies for testing are: ``pytest``, ``pytest-cov``, and ``pycodestyle``.
(The ``__init__.py`` file in ``poptpy/`` is just there so that ``pytest`` recognises where the package is stored.)

Tests can be run using ``tox``. By default, ``tox`` is set up to use Python 3.6, 3.7, and 3.8, so you will need all of these on your system.
They are ran against the poptpy folder itself, so there is no need to install the package before running unit tests.

However, arguably the most important test is whether it works in TopSpin, and that cannot be done using ``pytest``.
Changes to the TopSpin interface, or the communication between front- and backend, cannot be tested unless the files are installed to the TopSpin directory.


Documentation
-------------

The documentation is written using Sphinx. To build, run ``tox -e docs``.
