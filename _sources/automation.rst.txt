POISE under automation
======================

The command-line interface that POISE offers (see `frontend`) allows us to wrap POISE within a larger script.
Here we present some examples of how this can be accomplished: after this, the extension to automation is largely straightforward.
For example, if POISE is used inside an AU programme, then set the the ``AUNM`` parameter in TopSpin appropriately.

Basics
------

To incorporate POISE in an AU programme, you can use the syntax::

    XCMD("sendgui xpy poise <routine_name> [options]")

inside the AU script.

(Optional: To suppress POISE's final popup (telling the user that the optimum has been found), you can add the ``-q`` flag in the options.
The popup won't stop TopSpin from running whatever it was going to run, though, so it's completely safe to show the message.)

Alternatively, you can wrap POISE within a Python script, which is arguably easier to write.
The corresponding syntax for running an optimisation would be::

   XCMD("xpy poise <routine_name> [options]")

As you can see, it is the same except that ``sendgui`` isn't needed.


A simple(ish) example
---------------------

Here's an example of how the ``p1`` optimisation (shown in `routines`) can be incorporated into an AU script (download from `here <https://github.com/foroozandehgroup/nmrpoise/blob/master/nmrpoise/au/poisecal>`_).
This AU script performs a very similar task to the existing ``pulsecal`` script: it finds the best value of ``p1`` and plugs it back into the current experiment.
However, as we wrote in the paper, it tends to provide a much more accurate result.
In practice, we've already used it many times to calibrate ``p1`` before running other experiments.

.. note::
   This AU programme comes installed with POISE. However, you must create the ``p1cal`` routine before you can use this. Please see `routines` for a full walkthrough.

.. literalinclude:: ../nmrpoise/au/poisecal
   :language: c
   :lines: 29-30,48-78

Note that the six lines underneath "set some key params" can be collapsed to one line if an appropriate parameter set is set up beforehand.

Here's the Python equivalent of the AU programme above (download from `here <https://github.com/foroozandehgroup/nmrpoise/blob/master/nmrpoise/py/poisecalpy.py>`_):

.. literalinclude:: ../nmrpoise/py/poisecalpy.py
   :lines: 21-


Terminating scripts which call POISE
------------------------------------

So far we have seen how POISE can be included inside an AU programme or a Python script in TopSpin (a "parent script").
One problem that we haven't dealt with yet is how to kill the parent script when POISE errors out.
In general, if POISE is called via ``XCMD(poise ...)``, then even if POISE fails, the parent script will continue running.

One way to deal with this is to use a trick involving the ``TI`` TopSpin parameter, which can be set to any arbitrary string.
POISE, upon successful termination, will store the value of the cost function in the ``TI`` parameter.
If it doesn't successfully run (for example if a requested routine or cost function is not found, or some other error), then ``TI`` will be left untouched.

In order to detect when POISE fails from the top-level script, we therefore:

1. Set ``TI`` to be equal to some sentinel value, i.e. any string whose exact value is just used as a marker. Note that this should not be a numeric value. You can set it to be blank if you like, but please read the note below.

.. note::
   In an AU or Python programme, to set a parameter to a blank value, you have to set it to be a non-empty string that contains only whitespace. For example, in a Python script::

      PUTPAR("TI", " ")   # this will work
      PUTPAR("TI", "")    # this will NOT work!

   TopSpin mangles empty strings: instead of putting an empty string in, it puts the string ``"0"`` in.
   On the other hand, if the string is not empty but contains whitespace, TopSpin automatically trims it to an empty string after it's been put in.
   I don't know why.
   The same applies to the ``STOREPAR`` macro in AU programmes.

2. Run POISE.

3. Check if ``TI`` is equal to that sentinel value. If it is, then quit unceremoniously with an error message of your choice.

Briefly, here is an example of this strategy in action.
We show a Python script here, but the AU script is essentially the same, just with different function names.

::

    PUTPAR("TI", "poise")  # here "poise" serves as the sentinel value.
    XCMD("poise p1cal -a bobyqa -q")

    # Here POISE should be done. If it succeeded then TI will no longer be "poise".
    if GETPAR("TI") == "poise":
        raise RuntimeError("POISE failed!")

    # After this you can continue with whatever you wanted to do.

