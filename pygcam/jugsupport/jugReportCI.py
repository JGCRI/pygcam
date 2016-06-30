#!/usr/bin/env python
import os

from pygcam.config import getParam
jugdir  = getParam('GCAM.JugDir')

import jug
jug.init(jugfile='jugWorker.py', jugdir=jugdir)

from jugWorker import parseArgs, getResults

__version__ = "0.1"

def main():
    args = parseArgs(os.path.basename(__file__), __version__)

    results = getResults(args.simId, args.trials, args.baseline, args.scenario)

    print "Success:"
    for r in filter(lambda result: result.status == 0, results):
        print(r)

    print "\nFailure:"
    for r in filter(lambda result: result.status, results):
        print(r)

main()
