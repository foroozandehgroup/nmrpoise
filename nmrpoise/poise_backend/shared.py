"""
shared.py
---------

Stores the _g class which holds global variables (to track the state of the
optimisation).

SPDX-License-Identifier: GPL-3.0-or-later
"""

from pathlib import Path


class _g():
    """
    Class to store the "global" variables.

    Attributes
    ----------
    optimiser : str from {'nm', 'mds', 'bobyqa'}
        The optimiser being used.

    routine_id : str
        The name of the routine being used.

    p_spectrum : |Path|
        The path to the procno folder of the spectrum just acquired. (e.g.
        ``/path/to/data/1/pdata/1``)

    p_optlog : |Path|
        The path to the currently active ``poise.log`` file.

    p_errlog : |Path|
        The path to the currently active ``poise_err_backend.log`` file.

    maxfev : int
        The maximum number of function evaluations specified by the user. Can
        be zero, indicating no limit (beyond the hard limit of 500 times the
        number of parameters).

    p_poise : |Path|
        The path to the ``$TS/exp/stan/nmr/py/user/poise_backend`` folder.

    spec_f1p : float or tuple of float
        The ``F1P`` parameter. For a 1D spectrum this is a float. For a 2D
        spectrum this is a tuple of floats (``indirect, direct``) corresponding
        to the values of ``F1P`` in both spectral dimensions.

    spec_f2p : float or tuple of float
        The ``F2P`` parameter.
    """
    optimiser = None
    routine_id = None
    p_spectrum = None
    p_optlog = None
    p_errlog = None
    maxfev = 0
    nfev = 0
    p_poise = Path(__file__).parent.resolve()
    spec_f1p = None
    spec_f2p = None
