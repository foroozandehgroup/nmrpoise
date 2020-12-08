"""
poisecalpy.py
-------------

Download from: https://git.io/JUHOU

Python script which automates p1 optimisation using POISE. Behaves similarly to
pulsecal: optimises the value of p1 in expno 99999, then sets the optimised
value to the current dataset and shows a message.

This does not have the command-line argument functionality of the poisecal AU
programme, and tends to suffer from some edge-case bugs which are not present
in poisecal. This is generally a result of TopSpin's Python programmes being
more buggy than AU programmes. Nonetheless, as a result of this, we recommend
using the poisecal AU programme instead of this (which is retained mainly to
serve as a illustrative example in the documentation).

SPDX-License-Identifier: GPL-3.0-or-later
"""

# Read in F1P and F2P from current dataset.
f1p = GETPAR("F1P")
f2p = GETPAR("F2P")
# Use EXPNO 99999 in the current folder for optimisation.
old_dataset = CURDATA()
opt_dataset = CURDATA()
opt_dataset[1] = "99999"
# Create new dataset and move to it.
NEWDATASET(opt_dataset, None, "PROTON")
RE(opt_dataset)
# Set some key parameters. Notice that these lines can be cut if an appropriate
# parameter set is set up beforehand (and loaded using NEWDATASET()).
XCMD("getprosol")
PUTPAR("PULPROG", "zg")
PUTPAR("NS", "1")
PUTPAR("DS", "0")
PUTPAR("D 1", "1")
PUTPAR("RG", "1")
XCMD("s f1p {}".format(f1p))  # PUTPAR("status F1P") doesn't work.
XCMD("s f2p {}".format(f2p))  # Even though the documentation says it should.
# Run optimisation.
XCMD("poise p1cal -a bobyqa -q")
# POISE stores the optimised value in p1 after it's done. We can retrieve it
# here. Don't try to get the *status* parameter, since that is not the
# optimised value (it is the value used for the last function evaluation!)
p1opt = float(GETPAR("P 1"))/4
# Move back to old dataset and set p1 to optimised value.
RE(old_dataset)
PUTPAR("P 1", str(p1opt))
ERRMSG("Optimised value of p1: {:.3f}".format(p1opt))
# A TopSpin quirk: using MSG() will block subsequent commands until user hits
# "OK". You can use ERRMSG(), as is done here. There are other ways around
# this, see MSG_nonmodal() in the POISE frontend script.
# (Optional) Run acquisition.
# ZG()
