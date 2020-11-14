Builtin AU programmes
---------------------

POISE is bundled with two basic AU programmes for 1D and 2D spectra respectively.
These are mostly self-explanatory, so the text is just given below.
Of course, you can write your own AU programmes to be used with POISE routines.

These are the "default" AU programmes that POISE uses (for 1D and 2D spectra respectively) if an AU programme is not specified with the routine.


poise_1d
========

::

    ZG
    EFP
    APBK
    QUIT

The ``APBK`` command on older versions of TopSpin falls back to ``APK`` then ``ABS``, so can be safely used.


poise_2d
========

::

    ZG
    XFB
    XCMD("apk2d")
    ABS2
    QUIT
