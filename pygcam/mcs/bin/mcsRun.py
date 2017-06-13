#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import argparse
import subprocess

from pygcam.config import getParam

def parseArgs():
    defaultSimId = 1
    defaultTrialCount = 10

    parser = argparse.ArgumentParser(description='''Run typical MCS analysis''')

    parser.add_argument('-b', '--baseline',
                        help='''The name of the baseline scenario, which will be run
                        if specified, unless --noRun is also specified''')

    dfltProject = getParam('GCAM.DefaultProject')
    parser.add_argument('-P', '--project', default=dfltProject,
                        help='''The name of the project to run (current default project is "%s"''' % dfltProject)

    parser.add_argument('-t', '--trialCount', type=int, default=defaultTrialCount,
                        help='''The number of trials to create and run''')

    parser.add_argument('-g', '--groupDir',
                        help='''The name of a scenario group to use as a directory name
                        between the project name and the scenario name.''' )

    parser.add_argument('-G', '--dontGensim', action='store_true',
                        help='''Skip the 'gensim' step, but print the command''')

    parser.add_argument('-n', '--noRun', action='store_true',
                        help='''Print commands that would be executed, but don't run them.''')

    parser.add_argument('-q', '--dontQueue', action='store_true',
                        help='''Skip the 'queue' step, but print the command''')

    parser.add_argument('-s', '--simId', type=int, default=defaultSimId,
                        help='The id of the simulation to run. Default is %s.' % defaultSimId)

    args = parser.parse_args()
    return args


def run(cmd, ignoreError=False, printOnly=False):
    print(cmd)
    if printOnly:
        return

    status = subprocess.call(cmd, shell=True)

    if not ignoreError and status != 0:
        sys.exit(status)


def main():
    args = parseArgs()
    projectName = args.project

    if args.noRun:
        args.dontGensim = args.dontQueue = True

    simId = args.simId

    run("gt -P %s newsim" % projectName, printOnly=args.noRun)

    groupFlag = '-g ' + args.groupDir if args.groupDir else ''
    run("gt -P %s gensim -s %d -t %d %s" % (projectName, simId, args.trialCount, groupFlag),
        printOnly=args.dontGensim)

    if args.baseline:
        run("gt -P %s runsim -s %d -S %s" % (projectName, simId, args.baseline), printOnly=args.dontQueue)


main()
