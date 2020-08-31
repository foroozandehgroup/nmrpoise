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
    """
    optimiser = None
    routine_id = None
    p_spectrum = None
    p_optlog = None
    p_errlog = None
    maxfev = 0
    p_poise = Path(__file__).parent.resolve()
    spec_f1p = None
    spec_f2p = None
