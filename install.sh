#!/usr/bin/env bash
# Yeah, the output messages are manually coded

dir=$(dirname $0)

printf "Locating python3 executable... "
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

printf "Checking Python version... "
pyv=$($pyex --version 2>&1) && printf "$pyv\n"
if [[ $pyv != "Python 3"* ]]; then
    printf "\nA Python executable was found at $pyex, but it was not Python 3.\n"
    printf "Please install Python 3 and make sure that it is in \$PATH.\n"
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
fi

printf "Setting TopSpin path in TopSpin scripts... "
if sed -i.bak "s:p_tshome = .*$:p_tshome = \"$tspath\":g" $dir/*.py && \
        rm $dir/*.py.bak 2>/dev/null; then
    printf "done\n"
fi

unset i
packages=("numpy" "scipy" "dill")
for i in ${packages[@]}; do
    printf "Checking for $i... "
    if $pyex -c "import pkgutil; exit(not pkgutil.find_loader(\"$i\"))"; then
        printf "found\n"
    else
        printf "not found\n"
        printf "\nPlease install the Python package $i, e.g. with\n"
        printf "    pip install $i\n"
        printf "then run this script again.\n"
    fi
done

printf "Copying scripts to TopSpin directory... "
tspy=$tspath/py/user
if cp $dir/pypopt.py $dir/pypopt-makecf.py $tspy && \
        mkdir -p $tspy/pypopt $tspy/pypopt/routines $tspy/pypopt/cost_functions && \
        cp $dir/pypopt-be.py $tspy/pypopt; then
    printf "done\n"
fi
