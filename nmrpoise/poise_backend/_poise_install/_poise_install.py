"""
_poise_install.py
-----------------

Tiny script which handles the `poise --install` commands from the frontend.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import sys
from shutil import copy2
from pathlib import Path


def main():
    this_dir = Path(__file__).parent.resolve().expanduser()
    # poise --install p1: copy poisecal to the AU directory. The cost function
    # is installed by default.
    if sys.argv[1] == "p1":
        src = this_dir / "poisecal"
        dst = this_dir.parents[3] / "au" / "src" / "user"
        copy2(src, dst)
    # poise --install dosy: copy dosy_opt.py to the PY directory. The cost
    # function is already installed, as well.
    elif sys.argv[1] == "dosy":
        # dosy_opt.py
        src = this_dir / "dosy_opt.py"
        dst = this_dir.parents[1]
        copy2(src, dst)
    else:
        print("sys.argv[1] not provided, exiting")


if __name__ == "__main__":
    main()
