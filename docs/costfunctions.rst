Builtin cost functions
----------------------

POISE comes with a few, very basic, builtin cost functions.
These largely mirror those that are in TopSpin's native ``popt`` screen.

.. note::
   Just like in ``popt``, it is possible to use the ``dpl`` command in TopSpin to select a *portion* of the spectrum to be optimised.
   This stores the left and right region of the currently active view to the parameters ``F1P`` and ``F2P`` respectively.
   This works for all the builtin cost functions except for ``noe_1d``.

   More generally, any cost function that uses any of the ``get1d`` or ``get2d`` functions will respect the bounds placed in ``F1P`` and ``F2P``.
   See `customcf` for a more in-depth explanation.
 
-----------------

minabsint
=========

Seeks to minimise the intensity of the magnitude-mode spectrum.
Equivalent to ``MAGMIN`` in ``popt``.


maxabsint
=========

Seeks to maximise the intensity of the magnitude-mode spectrum (equivalent to ``MAGMAX``).


minrealint
==========

Seeks to minimise the intensity of the real spectrum (equivalent to ``NEGMAX``).

Note that this does *not* behave in the same way as ``minabsint``.
Because the real spectrum can have negative peaks, this essentially tries to maximise the intensity of negative peaks.


maxrealint
==========

Seeks to maximise the intensity of the real spectrum (equivalent to ``POSMAX``).


zerorealint
===========

Seeks to make the intensity of the real spectrum as close as possible to zero (equivalent to ``ZERO``).


noe_1d
======

Seeks to minimise the intensity of the spectrum, *except* for a region of 50 Hz centred on the parameter ``SPOFFS2`` (which corresponds to the frequency of the selective pulse).

Since NOE crosspeaks are typically negative (and ``apk`` typically phases them to be so), this essentially seeks to maximise the intensity of the crosspeaks.
