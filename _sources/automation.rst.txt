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

.. literalinclude:: ../nmrpoise/au/poisecal
   :language: c
   :lines: 14-

Note that all six lines underneath "set some key params" can be collapsed to one line if an appropriate parameter set is set up beforehand.

Here's the Python equivalent of the AU programme above (download from `here <https://github.com/foroozandehgroup/nmrpoise/blob/master/nmrpoise/py/poisecalpy.py>`_):

.. literalinclude:: ../nmrpoise/py/poisecalpy.py
   :lines: 14-


A helpful trick
---------------

POISE itself is a Python programme which calls an AU programme.
When incorporating POISE inside another script, it can become *very* difficult to terminate the entire thing as there are several nested loops in which scripts are being run.
So, for example, you can kill the top-level script using TopSpin's ``kill`` command.
However, that won't kill POISE itself, and so it will keep acquiring spectra, etc.

(If anybody has a better idea please let us know. As far as we can tell, this is a necessary limitation of the TopSpin ecosystem.)

Anyway, we deal with this using a trick involving the ``TI`` TopSpin parameter, which can be any arbitrary string.
POISE, upon successful function evaluation, will store the value of the cost function in the ``TI`` parameter.
If it doesn't successfully run (for example if a requested routine or cost function is not found, or some other error), then ``TI`` will be left untouched.

In order to detect when POISE fails from the top-level script, we therefore:

1. Set ``TI`` to be blank. Please read the note below.

.. note::
   In an AU or Python programme, you have to set ``TI`` to be a non-empty string that contains only whitespace. For example::

      PUTPAR("TI", " ")   # this will work
      PUTPAR("TI", "")    # this will NOT work!

   TopSpin mangles empty strings: instead of putting an empty string in, it puts the string ``"0"`` in.
   On the other hand, if the string is not empty but contains whitespace, TopSpin automatically trims it to an empty string after it's been put in.
   I don't know why.
   The same applies to the ``STOREPAR`` macro in AU programmes.

2. Run POISE.

3. Check if ``TI`` is an empty string. If it is, then quit unceremoniously with an error message of your choice.

You can see this strategy in action in the first part of the `DOSY optimisation script <https://github.com/foroozandehgroup/nmrpoise/blob/master/nmrpoise/py/dosy_opt.py>`_ (where we optimise the diffusion delay):

.. literalinclude:: ../nmrpoise/py/dosy_opt.py
   :dedent: 4
   :lines: 103-114

You don't actually have to set it to be blank, of course: it can be any sentinel value you like, as long as it cannot be confused with the value of a cost function.
For example, you could set ``TI`` to be the string ``"ILoveTopSpin"`` before the optimisation, then after that check whether it is still ``"ILoveTopSpin"``.
