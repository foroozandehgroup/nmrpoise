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
    cf_file = Path(__file__).resolve().parent / "costfunctions.py"
    with open(cf_file, 'r') as fp:
        tree = ast.parse(fp.read())
    # Find out which nodes are actually functions.
    functions = [func for func in tree.body
                 if isinstance(func, ast.FunctionDef)]
    # Get their names as well as their docstrings.
    function_names = [func.name for func in functions]
    docstrings = [ast.get_docstring(func) for func in functions]
    # Serialise both as a JSON string, which the frontend can parse.
    fdict = dict(zip(function_names, docstrings))
    print(json.dumps(fdict))


if __name__ == "__main__":
    main()
