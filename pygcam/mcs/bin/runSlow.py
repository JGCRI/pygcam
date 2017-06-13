#!/usr/bin/env python
#
# Feed trials to SLURM in managable batches and wait until these are
# underway before submitting more.
#

# TBD: Build this functionality into runsim?

import argparse
import subprocess
import sys
from time import sleep
from pygcam.config import getParam

def parseArgs():
    defaultSimId = 1
    defaultTrialCount = 100
    defaultMinutes = 5
    defaultMaxQueueSize = 400
    defaultQueueSleep = 60

    dfltProject = getParam('GCAM.DefaultProject')

    parser = argparse.ArgumentParser(description='''Run typical MCS analysis''')

    parser.add_argument('-c', '--trialsToQueue', type=int, default=defaultTrialCount,
                        help='''The number of trials to queue at once. Default is %d.''' % defaultTrialCount)

    parser.add_argument('-f', '--firstTrial', type=int, default=0,
                        help='''The trialNum of the first trial to process. Default is 0.''')

    parser.add_argument('-g', '--groupDir',
                        help='''The name of a scenario group to use as a directory name
                        between the project name and the scenario name.''')

    parser.add_argument('-P', '--project', default=dfltProject,
                        help='''The name of the project to run (current default project is "%s"''' % dfltProject)

    parser.add_argument('-t', '--trialsToRun', type=int, default=None,
                        help='''The total number of trials to create and run. If not provided, all trials
                        from the `firstTrial` to the last defined for the simulation will be run.''')

    parser.add_argument('-m', '--minutesToSleep', type=int, default=defaultMinutes,
                        help='''The number of minutes to sleep between tranches. Default is %d''' % defaultMinutes)

    parser.add_argument('-n', '--noRun', action='store_true',
                        help='''Print commands that would be executed, but don't run them.''')

    parser.add_argument('-q', '--maxQueueSize', type=int, default=defaultMaxQueueSize,
                        help='''Maximum number of queue slots to occupy. Default is %d.''' % defaultMaxQueueSize)

    parser.add_argument('-Q', '--queueSleep', type=int, default=defaultQueueSleep,
                        help='The number of seconds to sleep waiting for the queue to clear. Default is %d' % defaultQueueSleep)

    parser.add_argument('-s', '--simId', type=int, default=defaultSimId,
                        help='The id of the simulation to run. Default is %s.' % defaultSimId)

    parser.add_argument('-S', '--scenario', required=True,
                        help='''Comma-delimited list of scenarios to run''')

    args = parser.parse_args()
    return args

def run(cmd, ignoreError=False, printOnly=False):
    print(cmd)
    if printOnly:
        return

    status = subprocess.call(cmd, shell=True)

    if not ignoreError and status != 0:
        sys.exit(status)

# TBD: add ability to re-run trials of a given status, as runsim does with -r aborted,
# TBD: but using this "go slow" approach.
def main():
    from pygcammcs.Database import getDatabase

    args = parseArgs()

    project   = args.project
    simId     = args.simId
    scenarios = args.scenario.split(',')
    first     = args.firstTrial
    trials    = args.trials or getDatabase().getTrialCount(simId) - first
    noRun     = args.noRun
    count     = args.count

    last = first + trials - 1
    maxQueueSize = args.maxQueueSize
    delayMinutes = args.minutes
    delay = delayMinutes * 60
    queueSleep = args.queueSleep

    groupFlag = '-g ' + args.groupDir if args.groupDir else ''
    queueCmd = 'squeue -u $USER -p shared,slurm,short -h|wc -l'

    firstPass = True

    for scenario in scenarios:
        cmd = 'gt -P %s runsim -s %d -e %s %s' % (project, simId, scenario, groupFlag)

        for start in range(first, last, count):
            if firstPass:
                firstPass = False
            else:
                if noRun:
                    print('sleep(%d)' % delay)
                else:
                    sleep(delay)

            while True:
                result = subprocess.check_output(queueCmd, shell=True)
                queueCount = int(result)
                if queueCount + count > maxQueueSize:
                    print("Waiting %d sec for queue to clear. (%d entries)" % (queueSleep, queueCount))
                    sleep(queueSleep)
                else:
                    break

            trialSpec = '-t %d-%d' % (start, start + count - 1)
            run(cmd + trialSpec, printOnly=args.noRun)

main()
