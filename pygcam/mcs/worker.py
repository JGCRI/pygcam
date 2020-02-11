# Copyright (c) 2012-2016. The Regents of the University of California (Regents)
# and Richard Plevin. See the file COPYRIGHT.txt for details.
import os
import time
import ipyparallel as ipp

from pygcam.config import getConfig, getParam, setParam, getParamAsFloat, getParamAsBoolean
from pygcam.error import GcamError, GcamSolverError
from pygcam.log import getLogger, configureLogs
from pygcam.signals import (catchSignals, TimeoutSignalException, UserInterruptException)
from pygcam.utils import mkdirs

from pygcam.mcs.constants import RUNNER_SUCCESS, RUNNER_FAILURE
from pygcam.mcs.context import Context
from pygcam.mcs.error import PygcamMcsUserError, GcamToolError
from pygcam.mcs.Database import (RUN_SUCCEEDED, RUN_FAILED, RUN_KILLED, RUN_ABORTED,
                                 RUN_UNSOLVED, RUN_GCAMERROR, RUN_RUNNING)
from pygcam.mcs.util import readTrialDataFile, symlink
from pygcam.mcs.XMLParameterFile import XMLParameter, XMLParameterFile, decache

_logger = getLogger(__name__)

def _secondsToStr(t):
    minutes, seconds = divmod(t, 60)
    hours, minutes   = divmod(minutes, 60)
    return "%d:%02d:%02d" % (hours, minutes, seconds)


def _runPygcamSteps(steps, context, runWorkspace=None, raiseError=True):
    """
    run "gt +P {project} --mcs=trial run -s {step[,step,...]} -S {scenarioName} ..."
    For Monte Carlo trials.
    """
    import pygcam.tool

    runWorkspace = runWorkspace or getParam('MCS.RunWorkspace')

    trialDir = context.getTrialDir()
    groupArg = ['-g', context.groupName] if context.groupName else []

    # N.B. MCS.RunWorkspace is the RefWorkspace for trial sandboxes
    toolArgs = ['+P', context.projectName, '--mcs=trial',
                '--set=GCAM.SandboxRefWorkspace=' + runWorkspace,
                'run', '-s', steps, '-S', context.scenario,
                '--sandboxDir=' + trialDir] + groupArg

    command = 'gt ' + ' '.join(toolArgs)
    _logger.debug('Running: %s', command)
    status = pygcam.tool.main(argv=toolArgs, raiseError=True)
    msg = '"%s" exited with status %d' % (command, status)

    if status != 0 and raiseError:
        raise GcamToolError(msg)

    _logger.info("_runSteps: " + msg)
    return status

def _readParameterInfo(context, paramPath):
    from pygcam.xmlSetup import ScenarioSetup

    scenarioFile  = getParam('GCAM.ScenarioSetupFile')
    scenarioSetup = ScenarioSetup.parse(scenarioFile)
    scenarioNames = scenarioSetup.scenariosInGroup(context.groupName)

    paramFile = XMLParameterFile(paramPath)
    paramFile.loadInputFiles(context, scenarioNames, writeConfigFiles=False)
    paramFile.runQueries()
    return paramFile

def _applySingleTrialData(df, context, paramFile):
    simId    = context.simId
    trialNum = context.trialNum
    trialDir = context.getTrialDir(create=True)

    _logger.info('_applySingleTrialData for %s, %s', context, paramFile.filename)
    XMLParameter.applyTrial(simId, trialNum, df)   # Update all parameters as required
    paramFile.writeLocalXmlFiles(trialDir)         # N.B. creates trial-xml subdir

    linkDest = os.path.join(trialDir, 'local-xml')
    _logger.info('creating symlink to %s', linkDest)
    symlink('../../../../Workspace/local-xml', linkDest)


def _runGcamTool(context, noGCAM=False, noBatchQueries=False,
                noPostProcessor=False):
    '''
    Run GCAM in the current working directory and return exit status.
    '''
    _logger.debug("_runGcamTool: %s", context)

    # For running in an ipyparallel engine, forget instances from last run
    decache()

    # TBD: #### set to True to help debug ipyparallel issues ####
    debuggingOnly = False
    if debuggingOnly:
        time.sleep(30)
        return RUNNER_SUCCESS

    simId = context.simId
    baselineName = context.baseline
    isBaseline = not baselineName

    if isBaseline and not noGCAM:
        paramPath = getParam('MCS.ParametersFile')      # TBD: gensim has optional override of param file. Keep it?
        paramFile = _readParameterInfo(context, paramPath)

        df = readTrialDataFile(simId)
        columns = df.columns

        # add data for linked columns if not present
        linkPairs = XMLParameter.getParameterLinks()
        for linkName, dataCol in linkPairs:
            if linkName not in columns:
                df[linkName] = df[dataCol]

        _applySingleTrialData(df, context, paramFile)

    if noGCAM:
        _logger.info('_runGcamTool: skipping GCAM')
        gcamStatus = 0
    else:
        start = time.time()

        # N.B. setup step calls pygcam.setup.setupWorkspace
        gcamStatus = _runPygcamSteps('setup,prequery,gcam', context)

        stop = time.time()
        _logger.info("_runGcamTool: elapsed time: %s", _secondsToStr(stop - start))

    if gcamStatus == 0:
        if not noBatchQueries:
            _runPygcamSteps('query', context)

        if not noPostProcessor:
            steps = getParam('MCS.PostProcessorSteps')     # e.g., "diff,CI"
            if steps:
                _runPygcamSteps(steps, context)

        status = RUNNER_SUCCESS
    else:
        status = RUNNER_FAILURE

    _logger.info("_runGcamTool: exiting with status %d", status)
    return status


class WorkerResult(object):
    '''
    Encapsulates the results returned from a worker task.
    '''
    def __init__(self, context, errorMsg):
        from .XMLResultFile import collectResults, RESULT_TYPE_SCENARIO, RESULT_TYPE_DIFF

        self.context  = context
        self.errorMsg = errorMsg
        self.resultsList = []

        if context.status == RUN_SUCCEEDED:
            self.resultsList = collectResults(context, RESULT_TYPE_SCENARIO)

            if context.baseline:  # also save 'diff' results
                diffResults = collectResults(context, RESULT_TYPE_DIFF)
                if diffResults:
                    self.resultsList += diffResults

            _logger.debug('Worker results saving %s', self.resultsList)


    def __str__(self):
        c = self.context
        return "<WorkerResult run=%s sim=%s trial=%s, scenario=%s, status=%s error=%s>" % \
               (c.runId, c.simId, c.trialNum, c.scenario, c.status, self.errorMsg)


class Worker(object):
    '''
    Defines the methods and data associated with a worker task.
    '''
    def __init__(self, context, argDict):
        """
        Initialize a Worker instance

        :param context: (Context) description of trial to run
        :param argDict: (dict) various args passed from command-line
        """
        getConfig()
        configureLogs()

        catchSignals()
        # signal.signal(signal.SIGUSR1, _handleSIGUSR1)

        self.errorMsg = None
        self.context  = context
        self.argDict  = argDict
        self.runLocal = argDict.get('runLocal', False)

    def runTrial(self):
        """
        Run a single trial on the current engine using the local Worker.

        :return: (WorkerResult) holds run identification info and completion status
        """
        context = self.context
        runDir = context.getScenarioDir(create=True)
        _logger.info("runDir is %s", runDir)
        os.chdir(runDir)

        trialDir = os.path.dirname(runDir)
        logDir = os.path.join(trialDir, 'log')
        mkdirs(logDir)

        if not self.runLocal:
            logFile = os.path.join(logDir, context.scenario + '.log')
            setParam('GCAM.LogFile', logFile)
            setParam('GCAM.LogConsole', 'False')    # avoids duplicate output to file
            configureLogs(force=True)

            self.setStatus(RUN_RUNNING)

        result = self._runTrial()
        return result

    def setStatus(self, status):
        from ipyparallel.datapub import publish_data

        context = self.context
        context.setVars(status=status)

        if not self.runLocal:
            publish_data(dict(context=context))

    def _runTrial(self):
        """
        Run a single Monte Carlo trial.

        :return: (WorkerResult) Contains execution status, one of {'succeeded', 'failed', 'alarmed', 'aborted', 'killed'},
           as well as Context, any error message, and a list of results to post to the database.
        """
        context = self.context
        argDict = self.argDict

        noGCAM          = argDict.get('noGCAM', False)
        noBatchQueries  = argDict.get('noBatchQueries', False)
        noPostProcessor = argDict.get('noPostProcessor', False)

        trialNum = context.trialNum
        errorMsg = None

        _logger.info('Running trial %d' % trialNum)
        try:
            exitCode = _runGcamTool(context, noGCAM=noGCAM,
                                    noBatchQueries=noBatchQueries,
                                    noPostProcessor=noPostProcessor)
            status = RUN_SUCCEEDED if exitCode == 0 else RUN_FAILED

        except TimeoutSignalException:
            errorMsg = "Trial %d terminated by system" % trialNum
            status = RUN_KILLED

        # except AlarmSignalException:
        #     errorMsg = "Trial %d terminated by internal alarm" % trialNum
        #     status = RUN_ALARMED

        except UserInterruptException:
            errorMsg = "Interrupted by user"
            status = RUN_KILLED

        except GcamToolError as e:
            errorMsg = "%s" % e
            status = RUN_FAILED

        except PygcamMcsUserError as e:
            errorMsg = "%s" % e
            status = RUN_FAILED

        except GcamSolverError as e:
            errorMsg = "%s" % e
            status = RUN_UNSOLVED

        except GcamError as e:
            errorMsg = "%s" % e
            status = RUN_GCAMERROR

        except Exception as e:
            errorMsg = "%s" % e
            status = RUN_ABORTED     # run-time error in loaded module

        if errorMsg:
            _logger.error("Trial status: %s: %s", status, errorMsg)
            if status == RUN_ABORTED and getParamAsBoolean('GCAM.ShowStackTrace'):
                import traceback
                errorMsg = traceback.format_exc()
                _logger.debug(errorMsg)
        else:
            _logger.info('Trial status: %s', status)

        self.setStatus(status)
        result = WorkerResult(context, errorMsg)
        return result


latestStartTime = None

def runTrial(context, argDict):
    '''
    Remotely-callable function providing an interface to the Worker
    class.

    :param context: (Context) information describing the run
    :param argDict: (dict) with bool values for keys 'runLocal',
        'noGCAM', 'noBatchQueries', and 'noPostProcessor'
    :return: (WorkerResult) run identification info and completion status
    '''
    global latestStartTime

    if not argDict.get('runLocal', False):
        # On the first run, compute the latest time we should start a new trial.
        # On subsequent runs, check that there's adequate time still left.
        if latestStartTime is None:
            startTime = time.time()

            wallTime  = os.getenv('MCS_WALLTIME', '2:00') # should always be set except when debugging
            parts = [int(item) for item in wallTime.split(':')]
            secs = parts.pop()
            mins = parts.pop() if parts else 0
            hrs  = parts.pop() if parts else 0

            minTimeToRun = getParamAsFloat('IPP.MinTimeToRun')
            latestStartTime = (startTime + secs + 60 * mins + 3600 * hrs) - (minTimeToRun * 60)

        else:
            if time.time() > latestStartTime:
                # TBD: test this!
                # raising UnmetDependency error causes scheduler to reassign to another engine
                _logger.info("Insufficient time remaining on engine. Worker raising 'ipp.UnmetDependency'")
                raise ipp.UnmetDependency()

                # context.setVars(status=ENG_TERMINATE) # tell master to terminate us
                # time.sleep(10) # don't consume queue while waiting for termination
                # return WorkerResult(context, 'insufficient time remaining')

    worker = Worker(context, argDict)
    result = worker.runTrial()
    return result


if __name__ == '__main__':
    context = Context(runId=1001, simId=1, trialNum=2, scenario='baseline',
                      projectName='paper1', groupName='mcs', store=False)

    argDict = {'runLocal': True,
               'noGCAM': False,
               'noBatchQueries': False,
               'noPostProcessor': False}
    result = runTrial(context, argDict)
    print(result)
