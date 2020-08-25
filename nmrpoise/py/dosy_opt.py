"""
dosy_opt.py
-----------

Script that optimises parameters for a diffusion experiment. Currently only
works with oneshot DOSY (Pelta et al., Magn. Reson. Chem. 2002, 40 (13),
S147–S152, DOI: 10.1002/mrc.1107).

This is meant to be called from the TopSpin command line on a 2D diffusion
experiment.

Note that this script does not tweak the gradient lengths ("little delta"), so
these should be set to a sensible value (e.g. 1 ms) before running this script.

The algorithm is as follows:

 1. Create 1D versions of the diffusion experiment, one with the minimum
    gradient (10%, the "reference spectrum", expno 99998) and one with the
    maximum gradient (80%, "optimisation spectrum", expno 99999).
 2. Acquires both spectra.
 3. Check whether the opt. spectrum has at least 75% signal attenuation
    relative to the ref. spectrum. If not, increases the diffusion delay
    ("big Delta") and repeats steps 1 and 2.
 4. If the attenuation is sufficient, it then runs a POISE optimisation on the
    opt. spectrum to find the gradient strength at which 75% signal attenuation
    is achieved.
 5. Once this gradient strength has been found, returns to the 2D experiment
    and runs the `dosy` Bruker AU programme using the new parameter.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import time
import os

# Find the correct parameter set for the 1D sequence.
if GETPAR("PULPROG") == "doneshot_2d_jy":
    pulprog = "doneshot_1d_jy"
else:
    MSG("dosy_opt: unsupported pulse programme")
# Other variants can be added here.

# Get the expno of the 2D dataset, and store the parameter set. This is
# important because we want the optimisation to inherit most parameters, e.g.
# D1, SW, etc. from the parent experiment (which has presumably been set up by
# the user).
original_2d_expno = int(CURDATA()[1])
original_2d_dataset = CURDATA()
XCMD("wpar dosytemp all")

# Set up the reference experiment.
reference_expno = 99998
reference_dataset = list(original_2d_dataset)
reference_dataset[1] = str(reference_expno)
NEWDATASET(reference_dataset, None, "dosytemp")
RE(reference_dataset)
PUTPAR("PULPROG", pulprog)
PUTPAR("PARMODE", "1D")
PUTPAR("PPARMOD", "1D")
PUTPAR("GPZ 1", "10")
XCMD("sendgui browse_update_tree")
# Acquire reference dataset.
XCMD("poise_1d", wait=WAIT_TILL_DONE)

# Set up optimisation expno.
optimisation_expno = 99999
optimisation_dataset = list(original_2d_dataset)   # make a copy
optimisation_dataset[1] = str(optimisation_expno)
NEWDATASET(optimisation_dataset, None, "dosytemp")
RE(optimisation_dataset)
PUTPAR("PULPROG", pulprog)
PUTPAR("PARMODE", "1D")
PUTPAR("PPARMOD", "1D")
PUTPAR("GPZ 1", "80")
XCMD("sendgui browse_update_tree")

# Before we can run POISE, we need to delete the acqu2s and proc2s files from
# both ref. and opt. datasets (they are there because are inherited from the 2D
# parameter set we set the experiments up with). If we don't do this, then
# POISE gets very confused as it looks at the file structure and thinks that
# they are 2D spectra.
ref_expnof = os.path.join(reference_dataset[3],
                          reference_dataset[0],
                          reference_dataset[1])
opt_expnof = os.path.join(optimisation_dataset[3],
                          optimisation_dataset[0],
                          optimisation_dataset[1])
for f in (os.path.join(ref_expnof, "acqu2s"),
          os.path.join(opt_expnof, "acqu2s"),
          os.path.join(ref_expnof, "pdata", reference_dataset[2], "proc2s"),
          os.path.join(opt_expnof, "pdata", optimisation_dataset[2], "proc2s")
          ):
    if os.path.isfile(f):
        os.remove(f)

while True:
    # Here we use the `--maxfev 1` trick to evaluate a cost function at 80%
    # gradient. The cost function is stored as the `TI` parameter after the
    # experiment has been recorded.
    RE(optimisation_dataset)
    XCMD("poise dosy1d_aux -a nm --maxfev 1 -q", wait=WAIT_TILL_DONE)
    cf = float(GETPAR("TI"))
    # The dosy1d_aux cost function is (opt. intensity/ref. intensity) - 0.25.
    # If the opt. spectrum has been attenuated too little, then this value will
    # be positive.
    if cf > 0:
        # Increase D20, i.e. big Delta, by 100 ms
        current_d20 = float(GETPAR("D 20"))
        new_d20 = current_d20 + 0.1
        PUTPAR("D 20", str(new_d20))
        # Set it in the reference spectrum too
        RE(reference_dataset)
        PUTPAR("D 20", str(new_d20))
        # Re-acquire the reference spectrum.
        XCMD("xau poise_1d", wait=WAIT_TILL_DONE)
    # If the cost function is negative, then that means it's sufficiently
    # attenuated, and we can go on to the actual optimisation.
    else:
        break

# At this point, we know that 80% gradient strength provides at least 75%
# attenuation. So we can run an optimisation to find the actual value that does
# provide 75% attenuation (which is somewhere between 10% and 80%).
RE(optimisation_dataset)
XCMD("poise dosy1d -a bobyqa -q", wait=WAIT_TILL_DONE)
# Save the final parameters.
best_d20 = GETPAR("D 20")
best_gpz1 = GETPAR("GPZ 1")

# Jump back to original 2D expt. Set D20, but not GPZ1 as that should always be
# 100% (the actual gradient amplitude is controlled by Difframp, which will be
# generated by the `dosy` AU programme).
RE(original_2d_dataset)
PUTPAR("D 20", best_d20)
PUTPAR("GPZ 1", "100")
# Generate Difframp, etc. and then run the AU programme.
XCMD("xau dosy 10 {} 16 l y".format(best_gpz1))

y = time.time()
MSG(str(y - x))
