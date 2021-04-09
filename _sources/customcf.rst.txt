Custom cost functions
---------------------

All user-defined cost functions are stored inside the file::

    $TS/exp/stan/nmr/py/user/poise_backend/costfunctions_user.py

where ``$TS`` is your TopSpin installation path.
In order to modify or add cost functions, you will need to edit this file (with your favourite text editor or IDE).

The corresponding file containing builtin cost functions is ``costfunctions.py``.
You *can* edit this file directly: if you add a cost function there, it will work.
However, there are two risks with this.
Firstly, if you ever reinstall POISE, this file will be reset to the default (whereas ``costfunctions_user.py`` will not).
Secondly, any cost functions defined in ``costfunctions_user.py`` will shadow (i.e. take priority over) the cost functions defined in ``costfunctions.py`` if they have the same name.


The rules for cost functions
============================

Cost functions are defined as a standard Python 3 function which takes no parameters and returns a float (the value of the cost function).

1. **Do write a useful docstring if possible**: this docstring will be shown to the user when they type ``poise -l`` into TopSpin (which lists all available cost functions and routines).

2. **The spectrum under optimisation, as well as acquisition parameters, can be accessed via helper functions.** These are described more fully below.

3. **Never print anything inside a cost function directly to stdout**. This will cause the optimisation to stop. If you want to perform debugging, use the `log` function described below.

4. **To terminate the optimisation prematurely and return the best point found so far, raise CostFunctionError().** See below for more information.


Accessing spectra and parameters
================================

The most primitive way of accessing "outside" information is through the class ``_g``, which is imported from ``shared.py`` and contains a series of global variables reflecting the current optimisation.
For example, ``_g.p_spectrum`` is the path to the procno folder: you can read and parse the ``1r`` file inside this to get the real spectrum as a `numpy.ndarray` (for example).

.. currentmodule:: nmrpoise.poise_backend.shared

.. autoclass:: _g

However, this is quite tedious and error-prone, so there are a number of helper methods which use these primitives.
All the existing cost functions (inside ``costfunctions.py``) only use these helper methods.
All of these methods are stored inside ``cfhelpers.py`` and are already imported by default.

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

.. autofunction:: getndim

|v|

.. autofunction:: getnfev

Logging
=======

As noted above, printing anything to ``stdout`` will cause the optimisation to crash.
The reason for this is because ``stdout`` is reserved for communication between the POISE backend (the Python 3 component) and frontend (which runs in TopSpin).
Please use `log()` instead, which will print to the ``poise.log`` file in the expno folder.
It works in exactly the same way as the familiar ``print()``, and accepts the same kind of arguments.

.. autofunction:: log


Premature termination
=====================

In order to terminate an optimisation prematurely, you can raise any exception you like, for example with ``raise ValueError``.
POISE will stop the optimisation, and the error will be displayed in TopSpin.
The drawback of this naive approach is that *no information from the incomplete optimisation will be retained*.
That means that even if you have found a point that is substantially better than the initial point, it will not be saved.

If you want to terminate *and* return the best point found so far, please raise a ``CostFunctionError`` instead of any other exception (such as ``ValueError``).
``CostFunctionError`` takes up to 2 arguments: the number of arguments to supply depends on whether you want to include the final point which caused the error to be raised.

If you want to discard the last point, i.e. just stop the optimisation right away, then raise a ``CostFunctionError`` with just 1 argument. The argument should be the message that you want to display to the user::

    def cost_function():
        cost_fn_value = foo()   # whatever calculation you want here
        if some_bad_condition:
           raise CostFunctionError("Some bad condition occurred!")
        return cost_fn_value

It is possible, and probably advisable, to use this string to show the user helpful information (further steps to take, or the value of the cost function, for example).

Alternatively, you may want the current point (and the corresponding cost function value) to be saved as part of the optimisation.
For example, it may be the case that a certain threshold is "good enough" for the cost function and any value below that is acceptable.
In that situation, you would want to raise CostFunctionError once the cost function goes below that threshold, but *also* save that point as the best value.
To do so, pass the value of the cost function as the *second* parameter when raising CostFunctionError::

    def cost_function():
        cost_fn_value = foo()   # whatever calculation you want here
        if cost_fn_value < threshold:
           raise CostFunctionError("The cost function is below the threshold.",
                                   cost_fn_value)
        # Note that we still need the return statement, because it will be used
        # if cost_fn_value is greater than the threshold.
        return cost_fn_value

The value passed as the second argument can in general be any number.
If you want to make sure that the final point (which raised the CostFunctionError) is *always* chosen to be the optimal point, then you can do this::

    raise CostFunctionError("A message here", -np.inf)

Because ``-np.inf`` is smaller than any other possible number, it will always be picked as the "best" point.


Examples
========

There are a number of cost functions which ship with POISE.
These can all be found inside the ``costfunctions.py`` file referred to above.
This file also contains a number of more specialised cost functions, which were used for the examples in the POISE paper.
(Instead of opening the file, you can also find the `source code on GitHub <https://github.com/foroozandehgroup/nmrpoise/blob/master/nmrpoise/poise_backend/costfunctions.py>`_.)

A number of these are thoroughly commented with detailed explanations; do consider checking these out if you want more guidance on how to write your own cost function.
