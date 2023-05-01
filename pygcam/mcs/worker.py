# Copyright (c) 2012-2022. The Regents of the University of California (Regents)
# and Richard Plevin. See the file COPYRIGHT.txt for details.
import os
import time
import ipyparallel as ipp

from ..config import (getConfig, getParam, setParam, getParamAsFloat, getParamAsBoolean,
                      pathjoin)
from ..error import GcamError, GcamSolverError
from ..log import getLogger, configureLogs
from ..signals import catchSignals, TimeoutSignalException, UserInterruptException

from .error import PygcamMcsUserError, GcamToolError
from .database import (RUN_SUCCEEDED, RUN_FAILED, RUN_KILLED, RUN_ABORTED,
                       RUN_UNSOLVED, RUN_GCAMERROR, RUN_RUNNING)
from .sim_file_mapper import SimFileMapper
from .XMLParameterFile import XMLParameter, XMLParameterFile, decache

# Status codes for invoked programs
RUNNER_SUCCESS = 0
RUNNER_FAILURE = -1

_logger = getLogger(__name__)


def _secondsToStr(t):
    minutes, seconds = divmod(t, 60)
    hours, minutes   = divmod(minutes, 60)
    return "%d:%02d:%02d" % (hours, minutes, seconds)

def _runPygcamSteps(steps, mapper, raiseError=True):
    """
    run "gt +P {project} --mcs=trial run -s {step[,step,...]} -S {scenarioName} ..."
    For Monte Carlo trials.
    """
    from .. import tool
    from ..constants import McsMode

    context = mapper.context
    trial_dir = mapper.trial_dir()

    # N.B. mapper.sandbox_workspace is the reference workspace for trial sandboxes
    toolArgs = ['--projectName', context.projectName,
                '--mcs', McsMode.TRIAL.value,
                # '--set', f"GCAM.SandboxWorkspace={mapper.sandbox_workspace}",
                'run',

                # eliminate any unwanted blanks between steps
                '--step', ','.join(map(str.strip, steps.split(','))),
                '--scenario', context.scenario,
                '--sandboxDir', trial_dir]

    if context.groupName:
        toolArgs.extend(['--group', context.groupName])

    command = 'gt ' + ' '.join(toolArgs)
    _logger.debug(f'Running: {command}')

    status = tool.main(argv=toolArgs, mapper=mapper, raiseError=True)
    msg = f'"{command}" exited with status {status}'

    if status != 0 and raiseError:
        raise GcamToolError(msg)

    _logger.info(f"_runPygcamSteps: {msg}")
    return status

def _readParameterInfo(mapper):
    from ..xmlScenario import XMLScenario

    paramFile = XMLParameterFile(mapper.get_app_xml_param_file())  # reads cached copy from app-xml
    # xmlScenario = XMLScenario.get_instance(mapper.get_scenarios_file())
    # scenarioNames = xmlScenario.scenariosInGroup(mapper.get_scenario_group())
    # paramFile.loadInputFiles(mapper, scenarioNames, writeConfigFiles=False) # TBD: remove middle arg if this solves the problem
    paramFile.loadInputFiles(mapper, writeConfigFiles=False)
    paramFile.runQueries()
    return paramFile

def _applySingleTrialData(df, mapper, paramFile):
    context = mapper.context
    trial_num = context.trialNum
    trial_dir = mapper.trial_dir()

    _logger.info(f'_applySingleTrialData for {context}, {paramFile.filename}')
    XMLParameter.applyTrial(context.simId, trial_num, df)   # Update all stochastic parameters
    paramFile.writeLocalXmlFiles(trial_dir)                 # N.B. creates trial-xml subdir

    # Deprecated?
    # linkDest = pathjoin(trialDir, LOCAL_XML_NAME)       # does this require subdir?
    # _logger.info(f'creating symlink to {linkDest}')
    # symlink(f'../../../../Workspace/{LOCAL_XML_NAME}', linkDest)


def _runGcamTool(mapper, noGCAM=False, noBatchQueries=False,
                noPostProcessor=False):
    '''
    Run GCAM in the current working directory and return exit status.
    '''
    context = mapper.context
    _logger.debug(f"_runGcamTool: {context}")

    # For running in an ipyparallel engine, forget instances from last run
    decache()

    # TBD: #### set to True to help debug ipyparallel issues ####
    debuggingOnly = False
    if debuggingOnly:
        time.sleep(30)
        return RUNNER_SUCCESS

    # simId = context.simId
    baselineName = context.baseline
    isBaseline = not baselineName

    # Run setup steps before applying trial data
    setup_steps = getParam('MCS.SetupSteps')

    if setup_steps:
        _runPygcamSteps(setup_steps, mapper)

    if isBaseline and not noGCAM:
        paramFile = _readParameterInfo(mapper)

        df = mapper.readTrialDataFile()
        columns = df.columns

        # add data for linked columns if not present
        linkPairs = XMLParameter.getParameterLinks()
        for linkName, dataCol in linkPairs:
            if linkName not in columns:
                df[linkName] = df[dataCol]

        _applySingleTrialData(df, mapper, paramFile)

    if noGCAM:
        _logger.info('_runGcamTool: skipping GCAM')
        gcamStatus = 0
    else:
        start = time.time()
        gcamStatus = _runPygcamSteps('gcam2', mapper)        # TBD: set back to 'gcam' for pygcam 2.0
        stop = time.time()

        elapsed = _secondsToStr(stop - start)
        _logger.info(f"_runGcamTool: elapsed time: {elapsed}")

    if gcamStatus == 0:
        if not noBatchQueries:
            _runPygcamSteps('query', mapper)

        if not noPostProcessor:
            steps = getParam('MCS.PostProcessorSteps')     # e.g., "diff,CI"
            if steps:
                _runPygcamSteps(steps, mapper)

        status = RUNNER_SUCCESS
    else:
        status = RUNNER_FAILURE

    _logger.info(f"_runGcamTool: exiting with status {status}")
    return status


class WorkerResult(object):
    '''
    Encapsulates the results returned from a worker task.
    '''
    def __init__(self, mapper, context, errorMsg):
        from .XMLResultFile import collectResults, RESULT_TYPE_SCENARIO, RESULT_TYPE_DIFF

        self.context  = context
        self.errorMsg = errorMsg
        self.resultsList = []

        if context.status == RUN_SUCCEEDED:
            self.resultsList = collectResults(mapper, context, RESULT_TYPE_SCENARIO)

            if context.baseline:  # also save 'diff' results
                diffResults = collectResults(mapper, context, RESULT_TYPE_DIFF)
                if diffResults:
                    self.resultsList += diffResults

            _logger.debug(f'Worker results saving {self.resultsList}')


    def __str__(self):
        c = self.context
        return f"<WorkerResult run={c.runId} sim={c.simId} trial={c.trialNum}, scenario={c.scenario}, status={c.status} error={self.errorMsg}>"


class Worker(object):
    '''
    Defines the methods and data associated with a worker task.
    '''
    def __init__(self, context, argDict):
        """
        Initialize a Worker instance

        :param context: (McsContext) description of trial to run
        :param argDict: (dict) various args passed from command-line
        """
        getConfig()
        configureLogs()

        catchSignals()
        # signal.signal(signal.SIGUSR1, _handleSIGUSR1)

        self.errorMsg = None
        self.context  = ctx = context
        self.argDict  = argDict
        self.runLocal = argDict.get('runLocal', False)

        # create SimFileMapper from context and use it for all paths
        self.mapper = SimFileMapper(ctx)

    def runTrial(self):
        """
        Run a single trial on the current engine using the local Worker.

        :return: (WorkerResult) holds run identification info and completion status
        """
        from ..utils import random_sleep

        max_sleep = getParamAsFloat('MCS.MaxRandomSleep')
        if max_sleep > 0:
            random_sleep(0, max_sleep)     # try to avoid all trials accessing the same file at once

        exe_dir = self.mapper.sandbox_exe_dir
        _logger.info(f"exe_dir is {exe_dir}")
        os.chdir(exe_dir)

        if not self.runLocal:
            log_file = self.mapper.get_log_file()
            setParam('GCAM.LogFile', log_file)
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
           as well as McsContext, any error message, and a list of results to post to the database.
        """
        context = self.context
        argDict = self.argDict

        noGCAM          = argDict.get('noGCAM', False)
        noBatchQueries  = argDict.get('noBatchQueries', False)
        noPostProcessor = argDict.get('noPostProcessor', False)

        trialNum = context.trialNum
        errorMsg = None

        _logger.info(f'Running trial {trialNum}')

        try:
            exitCode = _runGcamTool(self.mapper, noGCAM=noGCAM,
                                    noBatchQueries=noBatchQueries,
                                    noPostProcessor=noPostProcessor)

            status = RUN_SUCCEEDED if exitCode == 0 else RUN_FAILED

        except TimeoutSignalException:
            errorMsg = f"Trial {trialNum} terminated by system"
            status = RUN_KILLED

        # except AlarmSignalException:
        #     errorMsg = "Trial %d terminated by internal alarm" % trialNum
        #     status = RUN_ALARMED

        except UserInterruptException:
            errorMsg = "Interrupted by user"
            status = RUN_KILLED

        except GcamToolError as e:
            errorMsg = str(e)
            status = RUN_FAILED

        except PygcamMcsUserError as e:
            errorMsg = str(e)
            status = RUN_FAILED

        except GcamSolverError as e:
            errorMsg = str(e)
            status = RUN_UNSOLVED

        except GcamError as e:
            errorMsg = str(e)
            status = RUN_GCAMERROR

        except Exception as e:
            errorMsg = str(e)
            status = RUN_ABORTED     # run-time error in loaded module

            if getParamAsBoolean('GCAM.ShowStackTrace'):
                import traceback
                traceback.print_exc()

        if errorMsg:
            _logger.error(f"Trial status: {status}: {errorMsg}")
        else:
            _logger.info(f'Trial status: {status}')

        self.setStatus(status)
        result = WorkerResult(self.mapper, context, errorMsg)
        return result


latestStartTime = None

def runTrial(context, argDict):
    '''
    Remotely-callable function providing an interface to the Worker
    class.

    :param context: (McsContext) information describing the run
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


# if __name__ == '__main__':
#     context = McsContext(runId=1001, simId=1, trialNum=2, scenario='baseline',
#                       projectName='paper1', groupName='mcs', store=False)
#
#     argDict = {'runLocal': True,
#                'noGCAM': False,
#                'noBatchQueries': False,
#                'noPostProcessor': False}
#     result = runTrial(context, argDict)
#     print(result)
