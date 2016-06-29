#!/usr/bin/env python
#
# Author:  Rich Plevin (rich@plevin.com)
# Created: 27 Jun 2016
#
# This is the "jugfile" used by "jug" to run a Monte Carlo simulation.
# For each trial, a policy scenario or scenarios depend on a baseline
# scenario, so the baseline is run first, and the policy is run only if
# the baseline succeeds.
#
# The work is split into two TaskManagers. The first runs GCAM and queries it
# to produce CSV files, then, by default, deletes the GCAM "output" directory,
# which holds the large XML database. The second task depends on the policy
# scenario completing the first task, after which it runs the "diff" command,
# computes carbon intensity, and stores results in the SQL database.
#
# Each task returns an overall status code, which is 0 for success and non-zero
# otherwise.
#
#
import os
import sys
from random import random
from time import sleep
import argparse
from jug import TaskGenerator, task

from pygcam.utils import parseTrialString
from pygcam.log import getLogger

PROGRAM = os.path.basename(__file__)
__version__ = "0.1"

_logger = getLogger(__name__)

class Context(object):
    def __init__(self, simId, trialNum, scenario):
        self.simId = simId
        self.trialNum = trialNum
        self.scenario = scenario

    def __str__(self):
        return "<Context simId=%d trialNum=%d scenario=%s>" % (self.simId, self.trialNum, self.scenario)

class Result(object):
    def __init__(self, status, context, step, policy=None, value=None):
        self.status  = status
        self.context = context
        self.step    = step         # the final step that was run
        self.policy  = policy
        self.value   = value        # numerical result

    def __str__(self):
        try:
            valueStr = '%.2f' % self.value
        except:
            valueStr = str(self.value)

        return "<Result step=%s status=%s value=%s>" % (self.step, self.status, valueStr)

def runGCAM(context):
    sleep(1)
    result = 0 if random() < 0.85 else 1  # succeed 85% of the time
    return Result(result, context, 'runGCAM')

def runQueries(context):
    sleep(1)
    result = 0 if random() < 0.95 else 1    # succeed 95% of the time
    return Result(result, context, 'runQueries')

def runDiffs(context, policy):
    result = 0 if random() < 0.95 else 1    # succeed 95% of the time
    return Result(result, context, 'runDiffs', policy=policy)

def computeCI(context, policy):
    ci = random() * 100
    return Result(0, context, 'computeCI', policy=policy, value=ci)

def runScenario(context):
    result = runGCAM(context)
    if result.status:
        return result

    result = runQueries(context)
    return result

# baseline is run as separate task, but policy is run directly,
# followed by diffs and CI
@TaskGenerator
def runBaseline(context):
    return runScenario(context)

@TaskGenerator
def runPolicy(baselineResult, policy):
    if baselineResult.status:
        return baselineResult

    context = baselineResult.context

    result = runScenario(Context(context.simId, context.trialNum, policy))
    if result.status:
        return result

    result = runDiffs(context, policy)
    if result.status:
        return result

    result = computeCI(context, policy)
    if result.status:
        return result

    return Result(0, context, 'CI', policy=policy, value=result.value)


def parseArgs():
    parser = argparse.ArgumentParser(prog=PROGRAM)

    parser.add_argument('-b', '--baseline',
                        help='''The name of the baseline scenario to run''')

    parser.add_argument('-S', '--scenario', default='',
                        help='''Specify the scenario(s) to run. Can be a comma-delimited list of
                            scenario names.''')

    parser.add_argument('-s', '--simId', type=int, default=1,
                        help='The id of the simulation')

    parser.add_argument('-t', '--trials', type=str, default='0',
                        help='''Comma separated list of trial or ranges of trials to run. Ex: 1,4,6-10,3.
                             Defaults to running all trials for the given simulation.''')

    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

    # parser.add_argument('-W', '--noWrapper', action='store_true',
    #                     help='''Do not run gcam within a wrapper that detects errors as early as possible
    #                     and terminates the model run. By default, the wrapper is used.''')

    return parser.parse_args()

# Convert args like "simId=1" to "--simId=1" since jug has trouble with '--'
sys.argv = [sys.argv[0]] + map(lambda arg: '--' + arg, sys.argv[1:])

args = parseArgs()
simId = args.simId
trials = parseTrialString(args.trials)
baseline = args.baseline
scenarios = args.scenario.split(',')

results = [runPolicy(runBaseline(Context(simId, trial, baseline)), policy) for trial in trials for policy in scenarios]

def getResults(simId, trialStr, baseline, scenarioStr):
    """
    Get result for the given trials, baseline, and scenario list for the given simId.
    Intended to be called by a Python script that needs to collect status.

    :param simId: (int) simulation id
    :param trialStr: (str) string representation of a set of trials
    :param baseline: (str) name of baseline scenario
    :param scenarios: (str) comma-delimited scenario names
    :return: a list of Result instances
    """
    trials = parseTrialString(trialStr)
    scenarios = scenarioStr.split(',')

    results = [runPolicy(runBaseline(Context(simId, trial, baseline)), policy) for trial in trials for policy in scenarios]
    return task.value(results)
