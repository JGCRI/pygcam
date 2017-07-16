# Copyright (c) 2012-2016. The Regents of the University of California (Regents)
# and Richard Plevin. See the file COPYRIGHT.txt for details.

# from datetime import datetime
import os
from signal import alarm, SIGTERM, SIGQUIT, SIGALRM

from pygcam.config import getConfig, setParam, getParamAsFloat, getParamAsBoolean
from pygcam.error import GcamError, GcamSolverError
from pygcam.log import getLogger, configureLogs
from pygcam.signals import catchSignals, SignalException, TimeoutSignalException, AlarmSignalException

from pygcam.mcs.context import Context
from pygcam.mcs.error import PygcamMcsUserError, TimeoutError, AlarmError
from pygcam.mcs.Database import (RUN_SUCCEEDED, RUN_FAILED, RUN_KILLED,
                                RUN_ABORTED, RUN_ALARMED, RUN_UNSOLVED,
                                RUN_GCAMERROR, RUN_RUNNING)
from pygcam.mcs.gcamtool import runGcamTool

_logger = getLogger(__name__)

def _sighandler(signum, _frame):
    err = SignalException(signum)   # convenient way to compose msg

    if signum == SIGALRM:
        raise AlarmError(str(err))

    elif signum in (SIGQUIT, SIGTERM):
        raise TimeoutError(str(err))

    else:
        raise SignalException(signum)


class WorkerResult(object):
    '''
    Encapsulates the results returned from a worker task.
    '''
    def __init__(self, context, errorMsg):
        self.context  = context
        self.errorMsg = errorMsg

    def __str__(self):
        c = self.context
        return "<WorkerResult run=%s sim=%s trial=%s, scenario=%s, status=%s error=%s>" % \
               (self.runId, c.simId, c.trialNum, c.expName, c.status, self.errorMsg)


class Worker(object):
    '''
    Defines the methods and data associated with a worker task.
    '''
    # startTime = datetime.now()

    def __init__(self, args):
        getConfig()
        configureLogs()

        self.context = Context(runId=args.runId, simId=args.simId, trialNum=args.trialNum,
                               expName=args.scenario, baseline=args.baseline,
                               projectName=args.projectName, groupName=args.groupName, store=False)
        self.errorMsg = None
        self.runLocal = args.runLocal

    @classmethod
    def runTrial(cls, args): # TBD: pass context, too
        """
        Run a single trial on the current engine using the local Worker.

        :param args: (argparse.Namespace) command-line args plus a few added elements
        :return: (WorkerResult) holds run identification info and completion status
        """
        from pygcam.utils import mkdirs

        getConfig()

        worker = cls(args)
        context = worker.context

        runDir = context.getScenarioDir(create=True)
        _logger.info("runDir is %s", runDir)
        os.chdir(runDir)

        trialDir = os.path.dirname(runDir)
        logDir = os.path.join(trialDir, 'log')
        mkdirs(logDir)

        if not args.runLocal:
            logFile = os.path.join(logDir, args.scenario + '.log')
            setParam('GCAM.LogFile', logFile)
            setParam('GCAM.LogConsole', 'False')    # avoids duplicate output to file
            configureLogs(force=True)

            worker.setStatus(RUN_RUNNING)

        result = worker._runTrial(args) # TBD: pass context
        return result

    def setStatus(self, status):
        from ipyparallel.datapub import publish_data

        context = self.context
        context.setVars(status=status)

        if not self.runLocal:
            publish_data({context.runId: context})

    def _runTrial(self, args):
        """
        Run a single Monte Carlo trial.

        :param args: (argparse.Namespace) args passed from Master
        :return: (str) execution status, one of {'succeeded', 'failed', 'alarmed', 'aborted', 'killed'}
        """
        catchSignals(_sighandler)

        try:
            context = self.context
            trialNum = context.trialNum
            errorMsg = None

            # Set an internal time limit for each trial
            minPerTask = getParamAsFloat('GCAM.Minutes')
            seconds = max(30, int(minPerTask * 60) - 45)

            _logger.info('Running trial %d' % trialNum)

            if seconds:
                alarm(seconds) # don't let any job use more than its allotted time
                _logger.debug('Alarm set for %d sec' % seconds)

            try:
                # endTime = datetime.now()
                # elapsedMinutes = (endTime - cls.startTime) / 60
                # timeRemaining = allocatedMinutes - elapsedMinutes
                # if timeRemaining < getParamAsFloat('IPP.MinimumTimeToRun'):
                #     what?

                exitCode = runGcamTool(args, context)
                status = RUN_SUCCEEDED if exitCode == 0 else RUN_FAILED

            except TimeoutSignalException:
                errorMsg = "Trial %d terminated by system" % trialNum
                status = RUN_KILLED

            except AlarmSignalException:
                errorMsg = "Trial %d terminated by internal alarm" % trialNum
                status = RUN_ALARMED

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

        except Exception as e:
            errorMsg = "%s" % e
            status = RUN_ABORTED

        finally:
            alarm(0)  # turn off timer

        if errorMsg:
            _logger.error("Trial status: %s: %s", status, errorMsg)
            if status == RUN_ABORTED and getParamAsBoolean('GCAM.ShowStackTrace'):
                import traceback
                errorMsg = traceback.format_exc()
                _logger.debug(errorMsg)
        else:
            _logger.info('Trial status: %s', status)

        self.setStatus(status)
        result = WorkerResult(self.context, errorMsg)
        return result


def runTrial(args): # TBD: pass context and args
    '''
    Remotely-callable function providing an interface to the Worker
    class.

    :param args: (argparse.Namespace) arguments to pass to the worker
    :return: (WorkerResult) run identification info and completion status
    '''
    # TBD: worker = Worker(context) or runTrial(context, args)
    return Worker.runTrial(args)

if __name__ == '__main__':
    from argparse import Namespace
    args = Namespace(runId=1001, simId=1, trialNum=2, scenario='baseline',
                     noGCAM=False, noBatchQueries=False,
                     updateDatabase=True, shutdownIdleEngines=False,
                     noPostProcessor=False, waitSecs=5)
    result = runTrial(args)
    print(result)
