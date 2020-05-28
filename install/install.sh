#!/usr/bin/env bash

# Path to the poptpy folder. This folder should contain poptpy.py, as well as the poptpy_backend folder.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"  # directory of this bash script.
POPTPYDIR="$(dirname $DIR)/poptpy"   # up one directory then down poptpy.

# Fetch $TSDIR if it's available.

# Search for Python 3 executable
printf "Locating python3 executable... "
if [[ $PY3PATH ]]; then # if the user set the environment variable already
    pyex=$PY3PATH
    printf "provided as \$PY3PATH: $PY3PATH\n"
else
    pyex=$(which python3)
    if [[ -z $pyex ]]; then
        printf "not found\n"
        printf "Locating python executable... "
        pyex=$(which python)
        if [[ -z $pyex ]]; then
            printf "not found\n"
            printf "\nPath to Python 3 not found.\nPlease install it first and make sure that it is in \$PATH.\n\n"
            exit 1
        fi
    fi
    printf "$pyex\n"
fi

# Check that Python version is >=3
printf "Checking Python version... "
pyv=$($pyex --version 2>&1) && printf "$pyv\n"
if [[ $pyv != "Python 3"* ]]; then
    if [[ $PY3PATH ]]; then
        printf "\n\n\$PY3PATH was given as $pyex, but it was not a Python 3 executable.\n\n"
    else
        printf "\n\nA Python executable was found at $pyex, but it was not Python 3.\n"
        printf "Please install Python 3 and make sure that it is in \$PATH.\n\n"
    fi
    exit 1
fi

# Set path to Python executable
printf "Setting Python path in TopSpin scripts... "
if sed -i.bak "s:p_python3 = .*$:p_python3 = \"$pyex\":g" $POPTPYDIR/*.py && \
        rm $POPTPYDIR/*.py.bak 2>/dev/null; then
    printf "done\n"
else
    printf "failed\n"
    printf "\nError editing TopSpin scripts with sed: please ensure you have the correct permissions to do so.\n\n"
    exit 1
fi

# Search for TopSpin installation directory
printf "Locating TopSpin installation directory... "
if [[ $TSDIR ]]; then # if the user set the environment variable already
    tspath=$TSDIR
    printf "provided as \$TSDIR: $TSDIR\n"
    if ! [[ -d "$TSDIR/py/user" ]]; then
        printf "\nThe directory provided ($TSDIR) was not a valid TopSpin directory.\n\n"
        exit 1
    fi
else
    # find all possible TopSpin directories
    unset tsdirs i # from http://mywiki.wooledge.org/BashFAQ/020
    while IFS= read -r -d '' file; do
        tsdirs[i++]="$file"
    done < <(find /opt -type d -ipath "*/topspin*/exp/stan/nmr" -print0 2>/dev/null)
    ntsdirs=${#tsdirs[@]}
    # offer choices depending on how many were found
    if [[ $ntsdirs -eq 0 ]]; then
        printf "not found\n"
        printf "\nThe TopSpin installation directory was not found.\n"
        printf "Please specify the TopSpin directory with \$TSDIR.\n\n"
        exit 1
    elif [[ $ntsdirs -gt 1 ]]; then
        printf "$ntsdirs possible candidates found\n"
        printf "\n"
        unset i
        for i in ${!tsdirs[@]}; do
            printf "%2d:  %s\n" "$((i+1))" "${tsdirs[$i]}"
        done
        printf "\nPlease enter a selection: "
        read nselected
        re='^[0-9]+$'
        if ! [[ $nselected =~ $re ]] || [[ -z $nselected ]]; then
            # First condition checks whether it's a number.
            # Second condition checks whether it's empty (e.g. called via pip).
            printf "\nThe TopSpin directory was not uniquely identified.\n"
            printf "Please specify it using the environment variable \$TSDIR.\n\n"
            exit 1
        fi
        TSDIR=${tsdirs[$((nselected-1))]}
        printf "Selected $TSDIR as the TopSpin directory.\n"
    else
        TSDIR=${tsdirs[0]}
        printf "$TSDIR\n"
    fi
    # check that it's valid
    if ! [[ -d "$TSDIR/py/user" ]]; then
        printf "\nThe directory found ($TSDIR) was not a valid TopSpin directory.\n"
        printf "Please specify the TopSpin directory with \$TSDIR.\n\n"
        exit 1
    fi
fi

# Install the files
printf "Copying scripts to TopSpin directory... "
tspy=$TSDIR/py/user
if cp $POPTPYDIR/poptpy.py $tspy && \
        cp -r $POPTPYDIR/poptpy_backend $tspy; then
    printf "done\n"
else
    printf "failed\n"
    printf "\nError copying files to $tspath/py/user: please ensure you have the correct permissions to do so.\n\n"
    exit 1
fi

printf "\nInstallation to TopSpin directory successful.\n\n"
