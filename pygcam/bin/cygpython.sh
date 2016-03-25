#!/bin/bash
#
# Use this script instead of python in shebang (#!) lines to fix cygwin paths
# so a non-cygwin python can understand them.
#
if [[ $# == 0 ]]; then
    echo "USAGE: pythonCygwin <filename> args..."
    exit -1
fi

script=$1
shift

path=$(which cygpath)

if [[ $? == 0 ]]; then
    # if cygpath was found, convert the path
    PythonFile=$(cygpath -wl "$script")
else
    # otherwise, don't
    PythonFile=$script
fi

echo python ${PythonFile} $*
python ${PythonFile} $*
