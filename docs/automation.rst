POISE under automation
======================

The command-line interface that POISE offers (see `frontend`) allows us to wrap POISE within a larger script.
Here we present some examples of how this can be accomplished: after this, the extension to automation is largely straightforward.
For example, if POISE is used inside an AU programme, then set the the ``AUNM`` parameter in TopSpin appropriately.

To incorporate POISE in an AU programme, you can use the syntax::

    XCMD("sendgui xpy poise <routine_name> [options]")

inside the AU script.

Here's an example of how the ``p1`` optimisation (shown in `routines`) can be incorporated into an AU script:

.. code-block:: c

   // use current dataset but change expno to 99999
   GETCURDATA
   int old_expno = expno;
   DATASET(name, 99999, procno, disk, user)
   // set some key params
   RPAR("PROTON", "all")
   GETPROSOL
   STOREPAR("PULPROG", "zg")
   STOREPAR("NS", 1)
   STOREPAR("DS", 0)
   STOREPAR("D 1", 1.0)
   // run optimisation
   XCMD("sendgui xpy poise p1cal -a bobyqa -q")
   // store optimised value of p1 in variable
   float p1opt;
   FETCHPAR("P 1", &p1opt)   // don't get status parameter!!
   p1opt = p1opt/4;
   // move back to old dataset and set p1 to optimised value
   DATASET(name, old_expno, procno, disk, user)
   VIEWDATA_SAMEWIN  // not strictly necessary, just re-focuses the original spectrum
   STOREPAR("P 1", p1opt)
   // (optional) run acquisition
   ZG
   QUIT

Note that all six lines underneath "set some key params" can be collapsed to one line if an appropriate parameter set is set up beforehand.

Alternatively, you can wrap POISE within a Python script, which is arguably easier to write.
The corresponding syntax for running an optimisation would be::

   XCMD("xpy poise <routine_name> -q [options]")

As you can see, it is the same except that ``sendgui`` isn't needed.
Here's the Python equivalent of the AU programme above::

   # use current dataset but change expno to 99999
   old_dataset = CURDATA()
   opt_dataset = CURDATA()
   opt_dataset[1] = "99999"
   # create and move to dataset
   NEWDATASET(opt_dataset, None, "PROTON")
   RE(opt_dataset)
   # set some key params
   XCMD("getprosol")
   PUTPAR("PULPROG", "zg")
   PUTPAR("NS", "1")
   PUTPAR("DS", "0")
   PUTPAR("D 1", "1")
   # run optimisation
   XCMD("poise p1cal -a bobyqa -q")
   # store optimised value of p1 in variable
   p1opt = float(GETPAR("P 1"))/4   # don't get status parameter!
   # move back to old dataset and set p1 to optimised value
   RE(old_dataset)
   PUTPAR("P 1", str(p1opt))
   # (optional) run acquisition
   ZG()

The paper (technically the SI) has an example of a slightly more involved Python script, used for DOSY optimisations.
