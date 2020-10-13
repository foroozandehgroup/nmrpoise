"""
costfunctions_user.py
---------------------

For user-defined cost functions.

Any cost functions defined here will shadow cost functions defined in
costfunctions.py. That means that (for example) if you redefine minabsint()
here, it will take precedent over the minabsint() defined in costfunctions.py.

SPDX-License-Identifier: GPL-3.0-or-later
"""

# You can import any other packages you need here (as long as they are present
# on the Python 3 used to install POISE).
import numpy as np

# Keep these imports here -- they provide the helper functions described in the
# documentation.
from .cfhelpers import *
from .shared import _g


# You're free to do anything here! For (very thoroughly commented) examples of
# how to setup your own cost functions, please check out costfunctions.py.
