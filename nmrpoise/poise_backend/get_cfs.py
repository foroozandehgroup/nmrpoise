"""
get_cfs.py
----------

Script which parses costfunctions.py to see what cost functions are available.
Used by the frontend.

SPDX-License-Identifier: GPL-3.0-or-later
"""

import sys
import ast
import json
from pathlib import Path


def main():
    """
    Parses costfunctions.py to get the top-level functions. Prints them to
    stdout with a space as the delimiter. This allows the frontend to read them
    in using Popen.communicate().
    """
    def get_cfs(file):
        # Gets cost functions and docstrings from a given file.
        # Returns dictionary in the format {'function_name' : 'docstring'}.
        with open(file, 'r') as fp:
            tree = ast.parse(fp.read())
        # Find out which nodes are actually functions.
        functions = [func for func in tree.body
                     if isinstance(func, ast.FunctionDef)]
        # Get their names as well as their docstrings.
        function_names = [func.name for func in functions]
        docstrings = [ast.get_docstring(func) for func in functions]
        return dict(zip(function_names, docstrings))

    cf_system_file = Path(__file__).resolve().parent / "costfunctions.py"
    cf_user_file = Path(__file__).resolve().parent / "costfunctions_user.py"

    # System and user cost functions.
    system_cfs = get_cfs(cf_system_file)
    user_cfs = get_cfs(cf_user_file)
    # {**x, **y} causes the entries from y to overwrite entries from x with the
    # same name, which means that user cost functions shadow system cost
    # functions. In 3.9+ we can do this with all_cfs = system_cfs | user_cfs :)
    all_cfs = {**system_cfs, **user_cfs}
    print(json.dumps(all_cfs))


if __name__ == "__main__":
    main()
