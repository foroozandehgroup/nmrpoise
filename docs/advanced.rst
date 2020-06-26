Advanced usage
==============


Selecting a optimisation algorithm
----------------------------------

The default algorithm used in ``poptpy`` is the Nelder–Mead algorithm (Nelder, J. A.; Mead, R. *The Computer Journal* **1965,** *7* (4), 308–313 `(link) <https://doi.org/10.1093/comjnl/7.4.308>`_).

There are two other algorithms which can be used:

 - The multidirectional search method (Dennis, J. E.; Torczon, V. *SIAM J. Optim.* **1991,** *1* (4), 448–474 `(link) <https://doi.org/10.1137/0801027>`_).

 - The BOBYQA algorithm (Cartis, C.; Fiala, J.; Marteau, B.; Roberts, L. *ACM Transactions on Mathematical Software* **2019,** *45* (3), 32:1–32:41 `(link) <https://doi.org/10.1145/3338517>`_).

.. note::
   In order to use the BOBYQA algorithm, you should ensure that you have the extra package dependencies **scipy**, **pandas**, and **Py-BOBYQA**. This can be done by installing ``poptpy`` as::

      pip install ts-poptpy[bobyqa]

The choice of optimiser is made by editing the ``backend.py`` file (found in ``$TS/py/user/poptpy_backend``). Near the top of the file, the ``optimiser`` variable can be set to one of three strings: ``"nm"``, ``"mds"``, or ``"bobyqa"``. Simply change this to the desired value to use a different optimiser.


Changing the AU programme
-------------------------

To be written.


.. _own_cf:

Writing your own cost functions
-------------------------------

To be written.
