Custom cost functions
---------------------

All cost functions are stored inside the file::

    $TS/exp/stan/nmr/py/user/poise_backend/costfunctions.py

where ``$TS`` is your TopSpin installation path.
In order to modify or add cost functions, you will need to edit this file (with your favourite text editor or IDE).

.. note::
   Reinstalling POISE with ``pip`` will restore this file to the default.
   If you have cost functions that are very complicated, it's a good idea to back this up before reinstalling.


The rules for cost functions
============================

Cost functions are defined as a standard Python 3 function which takes no parameters and returns a float (the value of the cost function).

Also, you should *never* print anything inside a cost function directly to ``stdout``.
That will cause the optimisation to stop.
If you want to do some debugging, read on — there's a function for that.

That's it!

Of course, it's quite useless saying that without telling you how to (for example) access the spectrum that's being optimised.
The way this is done is by using several variables inside the class ``_g``, which is imported from ``shared.py``.
These global variables provide information about the current optimisation.
For example, using ``_g.p_spectrum`` you can find the path of the real spectrum, then parse the file to get the spectrum as a `numpy.ndarray` (for example).

.. currentmodule:: nmrpoise.poise_backend.shared

.. autoclass:: _g


Helper methods
==============

If you've looked inside the ``costfunctions.py`` file, you've probably realised that none of them actually use these variables directly.
Instead, we have a bunch of helper methods that use these to get more useful information directly.
All of these methods are stored inside ``cfhelpers.py`` and are already imported.

The ones you are likely to use are the following:

.. currentmodule:: nmrpoise.poise_backend.cfhelpers

.. autofunction:: make_p_spec

|v|

.. autofunction:: get1d_fid

|v|

.. autofunction:: get1d_real

|v|

.. autofunction:: get1d_imag

|v|

.. autofunction:: get2d_rr

|v|

.. autofunction:: get2d_ri

|v|

.. autofunction:: get2d_ir

|v|

.. autofunction:: get2d_ii

|v|

.. autofunction:: getpar

|v|

.. autofunction:: log
