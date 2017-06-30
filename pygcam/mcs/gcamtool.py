# Created on Sep 20, 2013
#
# @author: Richard Plevin
#
# Copyright (c) 2014-2015. The Regents of the University of California (Regents)
# and Richard Plevin. See the file COPYRIGHT.txt for details.

import time
from pygcam.config import getParam, setParam
from pygcam.log import getLogger
from .constants import RUNNER_SUCCESS, RUNNER_FAILURE
from .error import TimeoutError, AlarmError, GcamToolError
from .util import readTrialDataFile
from .XMLParameterFile import readParameterInfo, applySingleTrialData

_logger = getLogger(__name__)


def secondsToStr(t):
    minutes, seconds = divmod(t, 60)
    hours, minutes   = divmod(minutes, 60)
    return "%d:%02d:%02d" % (hours, minutes, seconds)


def runPygcamSteps(steps, context, runWorkspace=None, raiseError=True):
    """
    run "gt +P {project} --mcs=trial run -s {step[,step,...]} -S {scenarioName} ..."
    For Monte Carlo trials.
    """
    import pygcam.tool

    runWorkspace = runWorkspace or getParam('MCS.RunWorkspace')

    trialDir = context.getTrialDir()
    groupArg = ['-g', context.groupName] if context.groupName else []

    # N.B. gcammcs' RunWorkspace is the gcamtool's RefWorkspace
    toolArgs = ['+P', context.appName, '--mcs=trial',
                '--set=GCAM.SandboxRefWorkspace=' + runWorkspace,
                'run', '-s', steps, '-S', context.expName,
                '--sandboxDir=' + trialDir] + groupArg

    command = 'gt ' + ' '.join(toolArgs)
    _logger.debug('Running: %s', command)
    status = pygcam.tool.main(argv=toolArgs, raiseError=True)
    msg = '"%s" exited with status %d' % (command, status)

    if status != 0 and raiseError:
        raise GcamToolError(msg)

    _logger.info("_runSteps: " + msg)
    return status


def runGcamTool(args, context):
    '''
    Run GCAM in the current working directory and return exit status.
    '''
    from XMLParameterFile import XMLParameter, decache

    _logger.debug("runGcamTool: %s", context)

    # For running in an ipyparallel engine, forget instances from last run
    decache()

    simId = context.simId
    baselineName = args.baseline
    isBaseline = not baselineName

    # deprecated
    # groupName = context.groupName
    # setParam('MCS.ScenarioSubdir', groupName, section=context.appName)

    if isBaseline and not args.noGCAM:
        paramPath = getParam('MCS.ParametersFile')      # TBD: gensim has optional override of param file. Keep it?
        paramFile = readParameterInfo(context, paramPath)

        df = readTrialDataFile(simId)
        columns = df.columns

        # add data for linked columns if not present
        linkPairs = XMLParameter.getParameterLinks()
        for linkName, dataCol in linkPairs:
            if linkName not in columns:
                df[linkName] = df[dataCol]

        applySingleTrialData(df, context, paramFile)

    try:
        if args.noGCAM:
            _logger.info('runGcamTool: skipping GCAM')
            gcamStatus = 0
        else:
            start = time.time()

            # N.B. setup step calls pygcam.setup.setupWorkspace
            gcamStatus = runPygcamSteps('setup,prequery,gcam', context)

            stop = time.time()
            _logger.info("runGcamTool: elapsed time: %s", secondsToStr(stop - start))

        if gcamStatus == 0:
            if not args.noBatchQueries:
                runPygcamSteps('query', context)

            if not args.noPostProcessor:
                steps = getParam('MCS.PostProcessorSteps')     # e.g., "diff,CI"
                if steps:
                    runPygcamSteps(steps, context)

            status = RUNNER_SUCCESS
        else:
            status = RUNNER_FAILURE

    except (TimeoutError, AlarmError):
        # handled by Runner.py
        raise

    except GcamToolError as e:
        status = RUNNER_FAILURE
        _logger.error("runGcamTool: %s" % e)
        raise   # see if this produces desired result

    except Exception as e:
        _logger.error("runGcamTool: %s" % e)
        raise

    _logger.info("runGcamTool: exiting")
    return status


# if __name__ == '__main__':
