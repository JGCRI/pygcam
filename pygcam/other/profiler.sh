#!/bin/bash

DELAY=2

if [[ $(uname -s) == Darwin ]]; then
    echo "COMMAND          %CPU  MEM    TIME"
    # e.g., gcam.exe         100.0 11G+   17:56.03
    top -o mem -l 0 -s $DELAY -stats command,cpu,mem,time | egrep '(gcam|objects)'
else
    # Run it once to output the header
    top -b -n1 -U $USER | grep COMMAND
    top -d $DELAY -a -b -M -U $USER | grep gcam
fi
