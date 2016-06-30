#!/usr/bin/env python
#
# Author:  Rich Plevin (rich@plevin.com)
# Created: 27 Jun 2016
#
# This is the main driver ("jugfile" used by jug) to run a Monte Carlo simulation.
# See jugWorker.py for more details.
#
import os
import sys
from pygcam.jugsupport.jugWorker import parseArgs, getResults

__version__ = "0.1"

# Convert args like "simId=1" to "--simId=1" since jug has trouble with '--'
sys.argv = [sys.argv[0]] + map(lambda arg: '--' + arg, sys.argv[1:])

args = parseArgs(os.path.basename(__file__), __version__)

results = getResults(args.simId, args.trials, args.baseline, args.scenario)
