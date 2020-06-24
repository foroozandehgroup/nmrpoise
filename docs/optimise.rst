Optimisations
=============

*This page is slated to be rewritten, with lots of screenshots and examples.*


Setting up a cost function
--------------------------

A number of pre-built cost functions have already been created, which can cover many simple use cases. These will be fully documented in due course. If all you need is one of these, then you can skip this section entirely.

However, one of the strengths of ``poptpy`` is its inherent flexibility: one can construct any cost function using the tools offered by the ``numpy`` package (as well as some predefined custom functions). To create a new cost function, make a new Python file inside ``.../py/user/poptpy/cost_functions`` defining the cost function, saving it as ``<CF_NAME>.py``. There are further instructions in the script itself, as well as brief documentation of the custom functions available.


Running an optimisation
-----------------------

In order to carry out an optimisation, you must specify several pieces of information, namely:

1. The **parameters** to be optimised (e.g. ``p1``).
2. The **lower and upper bounds** (e.g. approximately ``35`` and ``45``, if one is calibrating the length of a 360-degree pulse).
3. The **initial values** (this should be your best guess at the final answer).
4. The **tolerances** (how much of a difference from the "true" answer you are willing to accept).
5. The **cost function** (what function you will use to evaluate the "goodness" of a spectrum. Since this quantity is *minimised*, the lower this is, the better the spectrum is: so technically it measures the "badness" of a spectrum).

In this programme, a collection of these five items is referred to as a **routine**. Routines can be stored and ran multiple times (e.g. on different samples). On top of the five items listed, each routine is also associated with a name.

``poptpy`` should be run from within TopSpin (simply type ``poptpy`` into the TopSpin command line). The first time you run ``poptpy``, it will prompt you to create a new routine. Once a routine has been created, however, it is stored (technically ``pickle``'d) in the directory ``.../py/user/poptpy/routines``, and can be selected for reuse in future runs (``poptpy`` will recognise the presence of a stored routine).

*[Tip: when entering minimum and maximum values for parameters you can use (e.g.) 2m to denote 2 milliseconds, just like in TopSpin. You cannot, however, perform any arithmetic, because that would necessitate ``eval`` (or a complicated expression parsing routine) and we would prefer to avoid that.]*

Once a routine has been specified or created, the optimisation will take place, largely in the background. **We strongly recommend turning on TopSpin's "unsafe ZG" option (TopSpin preferences > Acquisition), at least while running the optimisation:** otherwise, on *every* function evaluation, TopSpin will ask for confirmation as to whether you really want to acquire a new spectrum.


Getting the results
-------------------

When the optimisation is complete, the best values found will be displayed and also stored in TopSpin's parameter lists (usually ``ased``, for most acquisition parameters) for future retrieval.

There is an optimisation log ``poptpy.log`` that is stored in the same directory as the spectrum EXPNO. This documents how the cost function varies with the parameters and can be useful in troubleshooting optimisations, or for plotting graphs to show the optimisation trajectory.

If the optimisation crashes or is otherwise unresponsive, you can use the TopSpin ``kill`` function to terminate it. Any errors raised by the backend script will be printed to ``.../py/user/poptpy/poptpy_err.log`` (technically, ``stderr`` is redirected to this file). To report a bug, please submit an issue with steps to reproduce it, and attach the the contents of this log file.
