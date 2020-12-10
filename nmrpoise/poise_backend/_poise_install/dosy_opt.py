"""
dosy_opt.py
-----------

Download from: https://git.io/JUHOY

Script that optimises parameters for a diffusion experiment. Currently works
with oneshot DOSY (Pelta et al., Magn. Reson. Chem. 2002, 40 (13), S147-S152,
DOI: 10.1002/mrc.1107), as well as the stegp1s and ledgp2s DOSY variants which
are standard TopSpin pulse programmes.

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

# Dictionary of DOSY pulse programmes, to be entered in the form
#    "2d_pulprog": ["1d_pulprog", "GRAD_AMPLITUDE_PARAM", "DIFF_DELAY_PARAM"]
# In more detail:
#  - 2d_pulprog is the name of the 2D DOSY pulse sequence.
#  - 1d_pulprog is the name of the corresponding 1D DOSY pulse sequence, which
#     should be just a single increment of the 2D sequence, but with Difframp
#     removed. See the doneshot_nd_jy pulse programmes for an example.
#  - GRAD_AMPLITUDE_PARAM is the parameter name in the 2D DOSY pulse sequence
#     that is multiplied by Difframp. In the 1D DOSY pulse sequence it should
#     not be multiplied by Difframp, so simply corresponds to the gradient
#     strength. Note that you need a space between GPZ and the number.
#  - DIFF_DELAY_PARAM is the parameter name in both 1D and 2D sequences that
#     corresponds to the diffusion delay. Again, a space between D and the
#     number is required.
# Other DOSY variants can be entered here to "register" them and make them
# available for use with this script.
pulprog_dict = {
    # doneshot_nd_jy can be downloaded from https://git.io/JUHOX and
    # https://git.io/JUHOP.
    "doneshot_2d_jy": ["doneshot_1d_jy", "GPZ 1", "D 20"],
    # the following two entries are Bruker standard sequences and already come
    # with TopSpin.
    "stegp1s": ["stegp1s1d", "GPZ 6", "D 20"],
    "ledgp2s": ["ledgp2s1d", "GPZ 6", "D 20"],
}


def main():
    # Look up the 1D pulse programme and associated parameters based on the
    # current 2D pulse programme.
    pp2d = GETPAR("PULPROG")
    if pp2d in pulprog_dict:
        pp1d, gpzparam, dparam = pulprog_dict[pp2d]
    else:
        MSG("dosy_opt: unsupported pulse programme. New pulse programmes can"
            " be added in the dosy_opt.py script.")
        EXIT()

    # Create new routines. We need to do this within this script since the
    # routine depends on the GPZ parameter being optimised; we can't hardcode
    # that in a predefined routine.
    gpzparam_short = gpzparam.replace(" ", "").lower()
    XCMD("poise --create dosy {} 20 80 50 2"
         " dosy poise_1d".format(gpzparam_short))
    XCMD("poise --create dosy_aux {} 79 81 80 0.1"
         " dosy_aux poise_1d".format(gpzparam_short))

    # Get the expno of the 2D dataset, and store the parameter set. This is
    # important because we want the optimisation to inherit most parameters,
    # e.g.  D1, SW, etc. from the parent experiment (which has presumably been
    # set up by the user).
    original_2d_expno = int(CURDATA()[1])
    original_2d_dataset = CURDATA()
    XCMD("wpar dosytemp all")

    # Set up the reference experiment.
    reference_expno = 99998
    reference_dataset = list(original_2d_dataset)
    reference_dataset[1] = str(reference_expno)
    NEWDATASET(reference_dataset, None, "dosytemp")
    RE(reference_dataset)
    PUTPAR("PULPROG", pp1d)
    PUTPAR("PARMODE", "1D")
    PUTPAR("PPARMOD", "1D")
    PUTPAR(gpzparam, "10")
    XCMD("sendgui browse_update_tree")
    # Acquire reference dataset.
    msg_nonmodal("dosy_opt: optimising diffusion delay...")
    XCMD("poise_1d", wait=WAIT_TILL_DONE)

    # Set up optimisation expno.
    optimisation_expno = 99999
    optimisation_dataset = list(original_2d_dataset)   # make a copy
    optimisation_dataset[1] = str(optimisation_expno)
    NEWDATASET(optimisation_dataset, None, "dosytemp")
    RE(optimisation_dataset)
    PUTPAR("PULPROG", pp1d)
    PUTPAR("PARMODE", "1D")
    PUTPAR("PPARMOD", "1D")
    PUTPAR(gpzparam, "80")
    XCMD("sendgui browse_update_tree")

    # Optimise the diffusion delay first.
    while True:
        # Here we use the `--maxfev 1` trick to evaluate a cost function at 80%
        # gradient. The cost function is stored as the `TI` parameter after the
        # experiment has been recorded.
        RE(optimisation_dataset)
        PUTPAR("TI", " ")  # has to be one space, not an empty string (try it)
        XCMD("poise dosy_aux -a nm --maxfev 1 -q", wait=WAIT_TILL_DONE)
        # If TI isn't a valid float, something went wrong with POISE.
        try:
            cf = float(GETPAR("TI"))
        except ValueError:
            EXIT()
        # The dosy_aux cost function is (opt. intensity/ref. intensity) minus
        # 0.25. If the opt. spectrum has been attenuated too little, then this
        # value will be positive.
        if cf > 0:
            # Increase delay, i.e. big Delta, by 100 ms
            current_delay = float(GETPAR(dparam))
            new_delay = current_delay + 0.1
            PUTPAR(dparam, str(new_delay))
            # Set it in the reference spectrum too
            RE(reference_dataset)
            PUTPAR(dparam, str(new_delay))
            # Re-acquire the reference spectrum.
            XCMD("xau poise_1d", wait=WAIT_TILL_DONE)
        # If the cost function is negative, then that means it's sufficiently
        # attenuated, and we can go on to the actual optimisation.
        else:
            break

    # At this point, we know that 80% gradient strength provides at least 75%
    # attenuation. So we can run an optimisation to find the actual value that
    # does provide 75% attenuation (which is somewhere between 10% and 80%).
    RE(optimisation_dataset)
    best_delay = GETPAR(dparam)
    msg_nonmodal("dosy_opt: diffusion delay set to {} seconds.\n"
                 "    now optimising gradient amplitude...".format(best_delay))
    PUTPAR("TI", " ")
    XCMD("poise dosy -a bobyqa -q", wait=WAIT_TILL_DONE)
    # Again, check to make sure that TI is a valid float.
    try:
        float(GETPAR("TI"))
    except ValueError:
        EXIT()
    best_gpz = GETPAR(gpzparam)

    # Jump back to original 2D expt. Set dparam, but not gpzparam as that
    # should always be 100% (the actual gradient amplitude is controlled by
    # Difframp, which will be generated by the `dosy` AU programme).
    RE(original_2d_dataset)
    PUTPAR(dparam, best_delay)
    PUTPAR(gpzparam, "100")
    # Generate Difframp, etc. and then run the AU programme.
    msg_nonmodal("dosy_opt: maximum gradient set to {}%.\n"
                 "    starting 2D experiment with optimised"
                 " parameters...".format(best_gpz))
    XCMD("xau dosy 10 {} 16 l y".format(best_gpz))


def msg_nonmodal(s):
    """
    Show a message box that does not force the user to click OK before the
    programme continues. See also the same function in poise.py (the frontend
    script).
    """
    dialog = mfw.BInfo()
    dialog.setMessage(s)
    dialog.setTitle("dosy_opt")
    dialog.setBlocking(0)  # in ordinary MSG() this is 1
    dialog.show()


if __name__ == "__main__":
    main()
