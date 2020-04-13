#!/usr/bin/env bash
# Yeah, the output messages are manually coded

dir=$(dirname $0)

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
            printf "\nPath to Python 3 not found.\nPlease install it first and make sure that it is in \$PATH."
            exit 1
        fi
    fi
    printf "$pyex\n"
fi

printf "Checking Python version... "
pyv=$($pyex --version 2>&1) && printf "$pyv\n"
if [[ $pyv != "Python 3"* ]]; then
    if [[ $PY3PATH ]]; then
        printf "\n\n\$PY3PATH was given as $pyex, but it was not a Python 3 executable.\n"
    else
        printf "\n\nA Python executable was found at $pyex, but it was not Python 3.\n"
        printf "Please install Python 3 and make sure that it is in \$PATH.\n"
    fi
    exit 1
fi

printf "Setting Python path in TopSpin scripts... "
if sed -i.bak "s:p_python3 = .*$:p_python3 = \"$pyex\":g" $dir/*.py && \
        rm $dir/*.py.bak 2>/dev/null; then
    printf "done\n"
fi

printf "Locating TopSpin installation directory... "
if [[ $TOPSPINDIR ]]; then # if the user set the environment variable already
    tspath=$TOPSPINDIR
    printf "provided as \$TOPSPINDIR: $TOPSPINDIR\n"
    if ! [[ -d "$TOPSPINDIR/py/user" ]]; then
        printf "\nThe directory provided ($TOPSPINDIR) was not a valid TopSpin directory.\n"
        exit 1
    fi
else
    # find all possible TopSpin directories
    unset tsdirs i # from http://mywiki.wooledge.org/BashFAQ/020
    while IFS= read -r -d '' file; do
        tsdirs[i++]="$file"
    done < <(find /opt -type d -ipath "**/topspin*/exp/stan/nmr" -print0 2>/dev/null)
    ntsdirs=${#tsdirs[@]}
    # offer choices depending on how many were found
    if [[ $ntsdirs -eq 0 ]]; then
        printf "not found\n"
        printf "\nPlease set the environment variable \$TOPSPINDIR, e.g. with\n"
        printf "    export \$TOPSPINDIR=/path/to/TopSpin3.5.1\n"
        printf "then run this script again.\n"
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
        tspath=${tsdirs[$((nselected-1))]}
        printf "Selected $tspath as the TopSpin directory.\n"
    else
        tspath=${tsdirs[0]}
        printf "$tspath\n"
    fi
    # check that it's valid
    if ! [[ -d "$tspath/py/user" ]]; then
        printf "\nThe directory found ($tspath) was not a valid TopSpin directory.\n"
        printf "Please specify the TopSpin directory with \$TOPSPINDIR.\n"
        exit 1
    fi
fi

printf "Setting TopSpin path in TopSpin scripts... "
if sed -i.bak "s:p_tshome = .*$:p_tshome = \"$tspath\":g" $dir/*.py && \
        rm $dir/*.py.bak 2>/dev/null; then
    printf "done\n"
fi

unset i
packages=("numpy" "scipy")
for i in ${packages[@]}; do
    printf "Checking for $i... "
    if $pyex -c "import pkgutil; exit(not pkgutil.find_loader(\"$i\"))"; then
        printf "found\n"
    else
        printf "not found\n"
        if [[ $pyex == *"conda"* ]]; then
            conda install $i || (printf "Please install the package $i with your Python package manager.\n" && exit 1)
        else
            pip3 install $i || pip install $i || (printf "Please install the package $i with your Python package manager.\n" && exit 1)
        fi
        printf "\n"
    fi
done

printf "Copying scripts to TopSpin directory... "
tspy=$tspath/py/user
if cp $dir/poptpy.py $tspy && \
        mkdir -p $tspy/poptpy $tspy/poptpy/routines && \
        cp $dir/poptpy_be.py $tspy/poptpy && \
        cp -r $dir/cost_functions $tspy/poptpy; then
    printf "done\n"
else
    printf "failed\n"
    printf "\nError copying files to $tspath/py/user: please ensure you have the correct permissions to do so.\n"
fi
