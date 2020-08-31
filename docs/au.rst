Builtin AU programmes
---------------------

POISE is bundled with two basic AU programmes for 1D and 2D spectra respectively.
Of course, you can write your own AU programme to be used with POISE.


poise_1d
========

::

    ZG
    EFP
    APBK
    QUIT

Acquires the spectrum, then does a Fourier transform with exponential apodisation, phase correction, and baseline correction.
The ``APBK`` command on older versions of TopSpin falls back to ``APK`` then ``ABS``, so can be safely used.


poise_2d
========

::

    ZG
    XFB
    XCMD("apk2d")
    ABS2
    QUIT

Acquires the spectrum, performs 2D Fourier transform, phase correction, and baseline correction in F2 dimension.
