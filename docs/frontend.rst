Frontend options
----------------

The frontend script (i.e. the script which you run in TopSpin) has a variety of flags which control its behaviour.
These are fully described here.
You can also access short descriptions of these by typing ``poise -h`` in TopSpin.


General options
===============

``--create NAME PARAM MIN MAX INIT TOL CF AU``

    Create a new named routine. This can only handle one-parameter routines; if you want a multiple-parameter routine, please use the GUI. The AU programme must be specified, it can't be left blank like in the GUI. Also, short forms such as ``4u`` for 4 µs are not allowed here.

``--delete DELETE``

    Delete a named routine. For example, run ``poise --delete p1cal`` to delete a routine named ``p1cal``.

    If you want to edit a routine, you can just re-create a new routine with the same name: the old one will be overwritten.

``-h, --help``

    Show a help message then exit.

``--kill``

    Kill POISE backends that may still be running.

    Running ``poise --kill`` should be the first course of action if you find unusual behaviour after terminating a POISE optimisation (e.g. being unable to delete a log file as it is still in use).
    If this does not work (very rare), then you may need to manually kill the Python processes: for example, on Windows PowerShell, run::

        Stop-Process -name python

    or on Unix systems::

        killall -9 python

    (replace ``python`` with ``python3`` as appropriate for your system). If you find that you need to do this, and can reproduce the error, please do `submit a bug report <https://github.com/foroozandehgroup/nmrpoise/issues>`_ or drop us an email.

``-l, --list``

    List all available cost functions, as well as all available routines and their parameters.


Options for running optimisations
=================================

``-a ALG, --algorithm ALG``

    Use the algorithm ALG for the optimisation.
    ALG can be one of ``nm`` (for Nelder–Mead), ``mds`` (for multidirectional search), or ``bobyqa`` (for Py-BOBYQA).
    The default is ``nm``.

``--maxfev MAXFEV``

    Maximum function evaluations to allow (i.e. maximum number of spectra to acquire during the optimisation run).
    If the optimisation reaches the limit, it will terminate, reporting the best value so far as the 'optimum'.

    This is useful for enforcing an upper limit on the time taken to perform an optimisation.
    Since by far the majority of the time is spent on acquiring the NMR spectra, ``MAXFEV`` evaluations will simply take roughly ``MAXFEV * t`` time to run (where ``t`` is the time taken for one spectrum — you can find this out using TopSpin's ``expt`` command).

    If you don't want to have a limit on function evaluations, just don't use this flag, or pass the value of 0.
    Technically, there is always a hard limit on the number of function evaluations (which is 500 times the number of parameters being optimised).
    However, it is probably almost impossible to run into that hard limit.

``-q, --quiet``

    Don't display the final popup at the end of the optimisation informing the user that the optimisation is done.
    This is mostly a matter of taste, as the final popup does not block any subsequent commands from being executed.

``-s, --separate``

    Use a separate expno for each function evaluation.
    Note that if POISE runs into an expno which already exists, it will terminate with an error!
