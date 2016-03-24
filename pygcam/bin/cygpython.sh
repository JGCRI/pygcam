#!/bin/bash
#
# Use this script instead of python in shebang (#!) lines to fix cygwin paths
# so a non-cygwin python can understand them.
#
if [[ $# != 1 ]]; then
    echo "USAGE: pythonCygwin <filename>"
    exit -1
fi

path=$(which cygpath)

if [[ $? == 0 ]]; then
    # if cygpath was found, convert the path
    PythonFile=$(cygpath -wl "$1")
else
    # otherwise, don't
    PythonFile=$1
fi

python ${PythonFile}
