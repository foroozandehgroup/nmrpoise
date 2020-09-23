POISE under automation
======================

The command-line interface that POISE offers (see `frontend`) allows us to wrap POISE within a larger script.
Here we present some examples of how this can be accomplished: after this, the extension to automation is largely straightforward.
For example, if POISE is used inside an AU programme, then set the the ``AUNM`` parameter in TopSpin appropriately.

To incorporate POISE in an AU programme, you can use the syntax::

    XCMD("sendgui xpy poise <routine_name> [options]")

inside the AU script.

Here's an example of how the ``p1`` optimisation (shown in `routines`) can be incorporated into an AU script (download from `here <https://github.com/foroozandehgroup/nmrpoise/blob/master/nmrpoise/au/poisecal>`_).
This AU script performs a very similar task to the existing ``pulsecal`` script: it finds the best value of ``p1`` and plugs it back into the current experiment.
Here we use the ``-q`` flag to suppress the final output message of POISE (which would display the optimised 360° pulse length), as it may be confusing to users.

.. literalinclude:: ../nmrpoise/au/poisecal
   :language: c
   :lines: 12-

Note that all six lines underneath "set some key params" can be collapsed to one line if an appropriate parameter set is set up beforehand.

Alternatively, you can wrap POISE within a Python script, which is arguably easier to write.
The corresponding syntax for running an optimisation would be::

   XCMD("xpy poise <routine_name> -q [options]")

As you can see, it is the same except that ``sendgui`` isn't needed.
Here's the Python equivalent of the AU programme above (download from `here <https://github.com/foroozandehgroup/nmrpoise/blob/master/nmrpoise/py/poisecalpy.py>`_):

.. literalinclude:: ../nmrpoise/py/poisecalpy.py
   :lines: 12-

The paper (technically the SI) has an example of a slightly more involved Python script, used for DOSY optimisations.
