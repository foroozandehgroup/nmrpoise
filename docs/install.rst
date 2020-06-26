Installation
============


Prerequisites
-------------

On top of the existing Python implementation in TopSpin, **poptpy further requires a separate Python 3 installation (at least 3.6).** This can be downloaded from https://www.python.org/downloads/

poptpy also uses the **numpy** package (version >= 1.17.0).

If you would like to use the `BOBYQA algorithm <https://github.com/numericalalgorithmsgroup/pybobyqa>`_ for the optimisation, you additionally need the **scipy**, **pandas**, and **Py-BOBYQA** packages. All can be downloaded via ``pip``.


From PyPI
---------

poptpy can be installed directly using ``pip``::

    pip install ts-poptpy

If you would like to use the BOBYQA optimiser, run::

    pip install ts-poptpy[bobyqa]

The installer attempts to detect your TopSpin installation directory and add the necessary files there.
The most probable reason for failure is if the path to the TopSpin installation cannot be uniquely identified.
This can happen if TopSpin was installed to a non-standard location, or if multiple versions of TopSpin are installed.

To fix this, provide an environment variable ``TSDIR`` which points to the ``/exp/stan/nmr`` folder in TopSpin. On Unix / Linux systems, use the following (modify the path as appropriate):

.. code-block:: bash

    # no spaces around the equals sign
    export TSDIR="/opt/topspinX.Y.Z/exp/stan/nmr"

and on Windows PowerShell:

.. code-block:: powershell

    $env:TSDIR = "C:\Bruker\TopSpinX.Y.Z\exp\stan\nmr"

After this, reinstalling with ``pip`` should work.


From GitHub
-----------

This is especially useful for spectrometers which are not directly connected to the Internet. Download the package (either using ``git clone`` as below, or from a `release <https://github.com/yongrenjie/poptpy/releases>`_), ``cd`` inside, and install using ``pip``:

.. code-block:: bash

    git clone https://github.com/yongrenjie/poptpy
    cd poptpy
    pip install .

If there are issues with TopSpin directory selection, follow the instructions above to specify the ``TSDIR`` environment variable.


Manual installation
-------------------

If installing via ``pip`` does not work, please :doc:`let us know <contact>` before following these steps:

1. Download the package (using ``git clone`` or from a [release](https://github.com/yongrenjie/poptpy/releases)).
2. Specify the path to the Python 3 executable by modifying the ``p_python3`` variable in ``poptpy/poptpy.py``. Warning: if you are on Windows and the path includes backslashes, you will need to either escape the backslashes or use a raw string::

    p_python3 = "C:\\path\\to\\python3"  # escaped backslash
    # or 
    p_python3 = r"C:\path\to\python3"    # raw string (equivalent)

3. Copy ``poptpy/poptpy.py``, as well as the ``poptpy/poptpy_backend`` folder, to TopSpin's ``/exp/stan/nmr/py/user`` directory.

