"""
.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
#
# Generate template batch files, then launch ipyparallel
# controller and engines using the values in the template.
#
from __future__ import division, print_function
import copy
from six import iteritems
import os
import stat
import sys
from time import sleep
from IPython.paths import locate_profile

import ipyparallel as ipp
from ipyparallel.apps.ipclusterapp import ALREADY_STARTED, ALREADY_STOPPED, NO_CLUSTER

from .context import Context
from .Database import RUN_NEW, RUN_RUNNING, RUN_SUCCEEDED, RUN_QUEUED, RUN_KILLED, ENG_TERMINATE, getDatabase
from .error import IpyparallelError, PygcamMcsSystemError

from ..log import getLogger

# Exit values for Master.processTrials()
CONTINUE = 1
EXIT = 2

_logger = getLogger(__name__)

#
# SLURM
#
_slurmEngineBatchTemplate = """#!/bin/sh
#SBATCH --account={account}
#SBATCH --partition={queue}
#SBATCH --job-name={cluster_id}-engine
#SBATCH --nodes=1
#SBATCH --tasks-per-node={tasks_per_node}
#SBATCH --time={timelimit}
#{engine_args}
export MCS_WALLTIME={timelimit}
srun %s --profile-dir="{profile_dir}" --cluster-id="{cluster_id}" --prolog="{prolog_script}" --epilog="{epilog_script}"
"""
# These attempts accomplished nothing since TBB doesn't use them
# export OMP_NUM_THREADS=5
# export MKL_NUM_THREADS=1
# export MKL_DOMAIN_NUM_THREADS="BLAS=5"

# No need to run the controller on a compute node, but just in case
_slurmControllerBatchTemplate = """#!/bin/sh
#SBATCH --account={account}
#SBATCH --partition={queue}
#SBATCH --job-name={cluster_id}-controller
#SBATCH --ntasks=1
#SBATCH --time={timelimit}
%s --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
"""

#
# PBS
#
_pbsEngineBatchTemplate = """#!/bin/sh
#PBS -V
#PBS -N {cluster_id}-engine
#PBS -q {queue}
#PBS -l walltime={timelimit}
{engine_args}
%s --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
"""

_pbsControllerBatchTemplate = """#!/bin/sh
#PBS -V
#PBS -N {cluster_id}-controller
#PBS -q {queue}
#PBS -l walltime={timelimit}
%s --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
"""

#
# LSF
#
_lsfEngineBatchTemplate = """#!/bin/sh
TBD
"""

_lsfControllerBatchTemplate = """#!/bin/sh
TBD
"""

# TBD: test PBS (where?)
batchTemplates = {'slurm' : {'engine'     : _slurmEngineBatchTemplate,
                             'controller' : _slurmControllerBatchTemplate},

                  'pbs'   : {'engine'     : _pbsEngineBatchTemplate,
                             'controller' : _pbsControllerBatchTemplate},

                  'lsf'   : {'engine'     : _lsfEngineBatchTemplate,
                             'controller' : _lsfControllerBatchTemplate},
                  }

class Master(object):
    def __init__(self, args):
        self.args = args
        self.db = getDatabase(checkInit=False)
        self.client = None
        self.finished = False

        projectName = args.projectName

        # If we're just adding trials, no point in caching runs from database
        if not args.addTrials:
            # cache run definitions from the database and amend as necessary when creating runs
            for scenario in args.scenarios:
                rows = self.db.getRunInfo(args.simId, scenario, includeSucceededRuns=False)
                _logger.info('Caching info for %d runs of scenario %s', len(rows), scenario)
                for row in rows:
                    assert len(row) == 4, 'db.getRunInfo failed to return 4 values'
                    runId, simId, trialNum, status = row
                    context = Context(projectName=projectName, runId=runId, simId=simId,
                                      trialNum=trialNum, scenario=scenario, status=status)
                    #_logger.debug("Loaded %s", context)

    def waitForWorkers(self):
        from pygcam.config import getParamAsInt

        maxTries  = getParamAsInt('IPP.StartupWaitTries')
        seconds   = getParamAsInt('IPP.StartupWaitSecs')
        profile   = self.args.profile
        clusterId = self.args.clusterId
        client = None

        for i in range(1, maxTries+1):
            if client and len(client) > 0:
                return

            if client is None:
                try:
                    # default timeout is 10 seconds
                    self.client = client = ipp.Client(profile=profile, cluster_id=clusterId)

                except IOError:
                    if i == maxTries - 1:
                        raise

                    _logger.info("Waiting for client (%d/%d)", i, maxTries)
                    sleep(seconds)
                    continue

            if len(client) == 0:
                _logger.info("Waiting for engines (%d/%d)", i, maxTries)
                sleep(seconds)

        if not client or len(client) == 0:
            raise IpyparallelError('Failed to connect to engines')

    def queueTotals(self):
        """
        Return totals for queue status across all engines
        """
        dv = self.client[:]
        qstatus = dv.queue_status()

        totals = dict(queue=0, completed=0, tasks=0)

        for id, stats in iteritems(qstatus):
            if id == u'unassigned':
                totals[id] = stats
            else:
                for key, count in iteritems(stats):
                    totals[key] += count

        return totals

    def shutdownIdleEngines(self):
        '''
        Shutdown the engines.
        '''
        if len(self.client) == 0:
            _logger.info("No engines are running")
            return

        dview = self.client[:]
        status = dview.queue_status()

        # for key, value in iteritems(status):
        #     _logger.debug('  %s: %s', key, value)

        idleEngines = []

        unassigned = u'unassigned'

        # Shutdown idle engines if there are no unassigned tasks
        if status[unassigned] == 0:
            # collect ids of idle engines
            for id, stats in iteritems(status):
                if id == unassigned:    # ignore
                    continue

                # _logger.debug('%d: %s', id, stats)
                if stats[u'tasks'] == 0 and stats[u'queue'] == 0:
                    idleEngines.append(id)

        if idleEngines:
            _logger.info('Shutting down %d idle engines', len(idleEngines))
            self.client.shutdown(targets=idleEngines, block=True)

            maxTries = 4
            seconds  = 1

            expectedEngines = len(self.client) - len(idleEngines)
            for i in range(maxTries):
                if len(self.client) != expectedEngines:
                    sleep(seconds)

            # TBD: handle timeout waiting for engines to stop
            _logger.info("%d engines active", len(self.client))

    def createRuns(self, simId, scenario, trialNums):
        '''
        Create entries in the "run" table for the given simId, trialNums, and scenario.

        :param simId: (int) simulation ID
        :param scenario: (str) scenario name
        :param trialNums: (list of int) trial numbers
        :return: list of Context instances
        '''
        from .error import PygcamMcsUserError

        db = self.db
        session = db.Session()

        try:
            exp = db.getExp(scenario)
            if exp is None:
                raise PygcamMcsUserError("Unknown scenario '%s'" % scenario)

            expId    = exp.expId
            baseline = exp.parent

            runs = []
            projectName = self.args.projectName
            groupName   = self.args.groupName

            # Add a run record for each trial in this chunk
            for trialNum in trialNums:
                # Add a record in the "run" table listing this trial as "new"
                # (row for this simid, trialnum and expid is deleted if it exists)
                run = db.createRun(simId, trialNum, expId=expId, status=RUN_NEW, session=session)
                runs.append(run)

            session.commit()

        except Exception:
            raise

        finally:
            db.endSession(session)

        contexts = map(lambda r: Context(projectName=projectName, runId=r.runId,
                                         simId=simId, trialNum=r.trialNum,
                                         scenario=scenario, groupName=groupName,
                                         baseline=baseline, status=r.status), runs)
        return contexts

    def setRunStatuses(self, pairs):
        """
        Process a list of status changes in a single transaction, e.g., when setting
        the status for a long list of runs to "queued".
        """
        from .Database import getDatabase

        db = getDatabase()
        with db.sessionScope() as session:
            for context, status in pairs:
                self.setRunStatus(context, status=status, session=session)

    def setRunStatus(self, context, status=None, session=None):
        """
        Cache the status of this run, and if it has changed, save the new
        status to the database. Some context objects are retrieved from the
        worker tasks, so we lookup the equivalent in our local cache to test
        for whether a change has occurred.
        """
        debug = False   # set to True for extra diagnostic msgs

        if debug:
            _logger.debug('setRunStatus: %s', context)

        status = status or context.status

        cached = Context.getRunInfo(context.runId)
        if cached:
            if debug:
                _logger.debug('setRunStatus: cache hit: %s', cached)

            if cached.status == status:
                if debug:
                    _logger.debug('setRunStatus: no change; returning')
                return
        else:
            if debug:
                _logger.debug('adding context for runId %d to cache', context.runId)
            cached = context.saveRunInfo()

        _logger.info('%s -> %s', cached, status)
        cached.setVars(status=status)
        self.db.setRunStatus(context.runId, status, session=session)

    def runningTasks(self):
        from pygcam.utils import flatten

        qstatus = self.client.queue_status(verbose=True)
        ids = [rec['tasks'] for key, rec in iteritems(qstatus) if isinstance(key, (int, long))]
        return flatten(ids)

    def completedTasks(self):
        recs = self.client.db_query({'completed': {'$ne': None}}, keys=['msg_id'])
        ids = [rec['msg_id'] for rec in recs] if recs else None
        return ids

    def checkRunning(self):
        """
        Check for newly running tasks
        """
        tasks = self.runningTasks()
        # _logger.debug("Found %d running tasks", len(running))

        for task in tasks:
            try:
                ar = self.client.get_result(task, block=False, owner=False)

                # if tasks are ready, we handle them later.
                if ar.ready():
                    #_logger.debug('checkRunning: skipping task with result (%s)', task)
                    continue

                if ar.data:
                    context = ar.data.get('context')
                    if context:
                        self.setRunStatus(context)

            except (KeyError, ipp.RemoteError) as e:
                #_logger.warning('checkRunning: purging result: %s', e)
                self.client.purge_results(jobs=task)

            except Exception as e:
                _logger.warning("checkRunning: %s", e)

    def resubmit(self, task, context):
        _logger.info('Resubmitting task %s', context)
        self.client.resubmit(task)
        self.setRunStatus(context, RUN_QUEUED)

    def getResults(self, tasks):
        if not tasks:
            return None

        client = self.client
        results = []

        for task in tasks:
            try:
                ar = client.get_result(task, block=False, owner=True)

                try:
                    if not ar.ready():
                        continue

                except KeyError:        # stale message id can trigger KeyError
                    client.purge_results(jobs=task)
                    continue

                chunk = ar.get()
                workerResult = chunk[0]
                context = workerResult.context
                status = context.status

                if status == ENG_TERMINATE:
                    if ar.engine_id is not None:
                        _logger.info("Terminating engine %s: insufficient time remaining", ar.engine_id)
                        client.shutdown(ar.engine_id)
                        sleep(2)
                        self.resubmit(task, context)

                elif status == RUN_KILLED:
                    self.resubmit(task, context)
                    continue

                else:
                    results.append(workerResult)

            except Exception as e:
                # Raised if an engine dies, e.g., walltime expired.
                # With retries=1, should be able to recover from this.
                _logger.warning('getResults: %s', e)

            client.purge_results(jobs=task)

        return results

    def saveResults(self, results):
        '''
        Called on the master to save results to the database that were prepared by the worker.
        '''
        from .Database import getDatabase

        db = getDatabase()
        session = db.Session()

        try:
            # Delete all old values in first transaction
            for result in results:
                context = result.context
                resultsList = result.resultsList

                if resultsList:
                    # Delete any stale results for this runId (i.e., if re-running a given runId)
                    names = [resultDict['paramName'] for resultDict in resultsList]
                    ids = db.getOutputIds(names)
                    db.deleteRunResults(context.runId, outputIds=ids, session=session)

            db.commitWithRetry(session)

            # Add all new values in a second transaction
            for result in results:
                context = result.context
                resultsList = result.resultsList or []
                runId   = context.runId

                self.setRunStatus(context, session=session)

                if context.status != RUN_SUCCEEDED:
                    continue

                for resultDict in resultsList:
                    paramName  = resultDict['paramName']
                    value      = resultDict['value']
                    regionName = resultDict['regionName']

                    # Save the values to the database
                    if resultDict['isScalar']:
                        db.setOutValue(runId, paramName, value, session=session)
                    else:
                        regionId = db.getRegionId(regionName)   # cached; not a DB query
                        units = resultDict['units']
                        db.saveTimeSeries(runId, regionId, paramName, value, units=units, session=session)

            db.commitWithRetry(session)

        except Exception as e:
            session.rollback()
            # TBD: distinguish database save errors from data access errors?
            raise PygcamMcsSystemError("saveResults failed: %s" % e)

        finally:
            db.endSession(session)

    def checkCompleted(self):

        while True:
            completed = self.completedTasks()
            if not completed:
                return

            _logger.debug('%d completed tasks', len(completed))

            results = self.getResults(completed)
            if not results:
                _logger.warning('Purging %d completed tasks with no results (engine died?)', len(completed))
                self.client.purge_results(jobs=completed)
                continue

            # _logger.debug('Saving %d results', len(results))
            self.saveResults(results)
            # for result in results:
            #     self.saveResults(result)

            seconds = 2
            sleep(seconds)    # brief sleep before checking for more completed tasks

    def outstandingTasks(self):
        '''
        Return True if any tasks remain to be completed.
        '''
        tot = self.queueTotals()
        _logger.info('%d engines: %s' % (len(self.client), tot))

        return tot['tasks'] or tot['queue'] or tot['unassigned'] or self.completedTasks()

    def mainloop(self):
        """
        Takes parameters from arguments passed from runsim plugin.
        If `args.loopOnly` is False, run the trials identified in self.args.
        If `args.addTrials` is True, exit after running the trials, otherwise,
        loop until all tasks are completed, if "shutdown when idle" was given
        as a command-line arg, or loop indefinitely, allowing another task to
        add more trials to run.

        :return: none
        """
        from ipyparallel import NoEnginesRegistered
        from pygcam.error import PygcamException
        from .slurm import Slurm

        slurm = Slurm()

        args = self.args
        shutdownWhenIdle = args.shutdownWhenIdle

        if args.redoListOnly and args.statuses:
            listTrialsToRedo(self.db, args.simId, args.scenarios, args.statuses)
            return

        if not args.runLocal:
            self.waitForWorkers()    # wait for engines to spin up

        if not args.loopOnly:
            self.runTrials()

        if args.addTrials or args.runLocal:
            return      # Exit after adding or running trials

        while True:
            try:
                self.checkRunning()         # Check for newly running tasks
                self.checkCompleted()       # Check for completed tasks

                outstanding = self.outstandingTasks()
                if outstanding:
                    if len(self.client) == 0:
                        pending = slurm.jobsInState('pending', jobName='mcs-engine')
                        if pending:
                            _logger.info('No engines registered; %d workers PENDING', len(pending))
                            sleep(30)
                            continue
                        else:
                            _logger.info("No engines running or pending. Shutting down hub.")
                            self.client.shutdown(hub=True, block=True)
                            return

                    # self.checkRunning()         # Check for newly running tasks
                    # self.checkCompleted()       # Check for completed tasks

                else:   # no outstanding tasks
                    _logger.info("No outstanding tasks. Shutting down hub.")
                    self.client.shutdown(hub=True, block=True)
                    return

                if shutdownWhenIdle:
                    self.shutdownIdleEngines()

                _logger.debug('sleep(%d)', args.waitSecs)
                sleep(args.waitSecs)

            except NoEnginesRegistered:
                pass    # handled in loop

            except Exception as e:
                raise PygcamException("mainloop: %s" % e)

    def runTrials(self):
        from .util import parseTrialString
        import worker

        args = vars(self.args)
        argDict = {}
        for key in ('runLocal', 'noGCAM', 'noBatchQueries', 'noPostProcessor'):
            argDict[key] = args.get(key, False)

        simId       = args['simId']
        statuses    = args['statuses']
        scenarios   = args['scenarios']
        projectName = args['projectName']
        groupName   = args['groupName']
        trialStr    = args['trials']
        runLocal    = args['runLocal']

        asyncResults = []
        view = None if runLocal else self.client.load_balanced_view(retries=2)

        for scenario in scenarios:

            if statuses:
                # Change this to return Run instances?
                # If any of the "redo" options find trials, use these instead of args.trials
                contexts = self.db.getRunsByStatus(simId, scenario, statuses,
                                                   projectName=projectName,
                                                   groupName=groupName)

                if not contexts:
                    _logger.warn("No trials found for simId=%s, scenario=%s with statuses=%s",
                                 simId, scenario, statuses)
                    continue
            else:
                trialCount = self.db.getTrialCount(simId)

                if trialStr:
                    # convert arg string like "4,7,9-12,42" to a list of ints
                    trialList = parseTrialString(trialStr)
                    userTrials = len(trialList)

                    # remove nonsense values and warn user about them
                    trialNums = filter(lambda trial: 0 <= trial < trialCount, trialList)
                    goodTrials = len(trialNums)
                    if goodTrials != userTrials:
                        _logger.warn('Ignoring %d trial numbers that are out of range [0,%d]',
                                     userTrials - goodTrials, trialCount)
                else:
                    # if trials aren't specified, queue all of them
                    trialNums = range(trialCount)

                contexts = self.createRuns(simId, scenario, trialNums)

            statusPairs = []

            for context in contexts:
                try:
                    if runLocal:
                        #self.setRunStatus(context, status=RUN_RUNNING)
                        statusPairs.append((context, RUN_RUNNING))
                        ctx = copy.copy(context)    # use a copy to simulate what happens with remote call...
                        result = worker.runTrial(ctx, argDict)
                        self.saveResults([result])
                    else:
                        # Easier to deal with a list of AsyncResults instances than a
                        # single instance that contains info about all "future" results.
                        result = view.map_async(worker.runTrial, [context], [argDict])
                        #self.setRunStatus(context, status=RUN_QUEUED)
                        statusPairs.append((context, RUN_QUEUED))

                    asyncResults.append(result)

                except Exception as e:
                    _logger.error("Exception running 'runTrial': %s", e)

            self.setRunStatuses(statusPairs)

        return asyncResults


def listTrialsToRedo(db, simId, scenarios, statuses):
    from .util import createTrialString

    # 'missing' is not a real status found in the database
    missing = 'missing' in statuses
    if missing:
        statuses.remove('missing')

    for scenario in scenarios:
        trialNums = []

        # If any of the "redo" options find trials, use these instead of args.trials
        tuples = db.getRunsByStatus(simId, scenario, statuses)
        if tuples:
            # Just print the corresponding trial string
            trialNums += map(lambda tuple: tuple[2], tuples)  # unpack(runId, simId, trialNum, ...) tuple

        if missing:
            trialNums += db.getMissingTrials(simId, scenario)

        if trialNums:
            trialStr = createTrialString(trialNums)
            print("%s:\n%s" % (scenario, trialStr))
        else:
            _logger.warn("No trials found for simId=%s, scenario=%s with statuses=%s",
                         simId, scenario, statuses)

def templatePath(scheduler, profile, clusterId, process):
    profileDir = locate_profile(profile)
    basename = '%s_%s_%s.template' % (scheduler, clusterId, process)
    filename = os.path.join(profileDir, basename)
    return filename

def _saveBatchFiles(numTrials, argDict):
    """
    Create and save engine and controller batch files that will
    be used by ipcontroller and ipengine at start-up. The files are
    created in the profile directory, indicated in `argDict` either
    as "profile_dir" or constructed from "profile" by ipython's
    `locate_profile` function. The ipyparallel config files must set
    the batch_template_file to the names of the generated files, which
    are "{scheduler}-{cluster_id}-{process}.template",
    where {process} is "engine" or "controller", depending as appropriate.
    So for SLURM (the default scheduler), and the default cluster id ("mcs"),
    the two generated files are "slurm-mcs-engine.template" and
    "slurm-mcs-controller.template".

    :param numTrials: (int) the number of GCAM trials to run
    :param argDict: (dict) values for "scheduler", "account", "queue",
       "profile", "cluster_id", "tasks_per_node", "num_engines", "timelimit",
       and "minimum_seconds" are substituted into the batch templates. For
       most of these, defaults are taken from ~/.pygcam.cfg and overridden
       by argDict. Both "ntasks" and "timelimit" are computed on-the-fly.
    :return: (dict) the names of the generated files, keyed by 'engine' or 'controller'
    """
    import pipes
    from pygcam.config import getParam, getParamAsInt

    minutesPerRun = argDict['minutesPerRun']
    maxEngines    = argDict['maxEngines']
    numEngines    = min(numTrials, maxEngines)
    maxRunsPerEngine = numTrials // numEngines + (1 if numTrials % numEngines else 0)

    minutesPerEngine = minutesPerRun * maxRunsPerEngine
    timelimit = "%02d:%02d:00" % (minutesPerEngine // 60, minutesPerEngine % 60)

    defaults = {'scheduler'       : getParam('IPP.Scheduler'),
                'account'         : getParam('IPP.Account'),
                'queue'           : getParam('IPP.Queue'),
                'engine_args'     : getParam('IPP.OtherEngineArgs'),
                'cluster_id'      : argDict['clusterId'],
                'tasks_per_node'  : getParamAsInt('IPP.TasksPerNode'),
                'min_secs_to_run' : getParamAsInt('IPP.MinTimeToRun') * 60,
                'timelimit'       : timelimit,
                'prolog_script'   : getParam('IPP.PrologScript'),
                'epilog_script'   : getParam('IPP.EpilogScript'),
                }

    defaults.update(argDict)

    profile    = defaults['profile']
    scheduler  = defaults['scheduler']
    cluster_id = defaults['cluster_id']

    defaults['profile_dir'] = locate_profile(profile)

    templates = batchTemplates[scheduler.lower()]
    files = {}

    # N.B. process is 'controller' or 'engine'
    for process, template in templates.items():
        cmd_argv = [sys.executable, "-m", "ipyparallel.%s" % process]
        text = template % ' '.join(map(pipes.quote, cmd_argv))  # insert command line
        text = text.format(**defaults)   # insert other parameters

        files[process] = filename = templatePath(scheduler, profile, cluster_id, process)

        _logger.debug('Writing %s', filename)
        with open(filename, 'w') as f:
            f.write(text)

        os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)  # make executable

    return files


def _clusterCommand(cmd):
    from pygcam.utils import shellCommand

    status = shellCommand(cmd, shell=True, raiseError=False)

    if status:
        statusStrings = {
            ALREADY_STOPPED: 'Cluster already stopped',
            ALREADY_STARTED: 'Cluster already started',
            NO_CLUSTER:      'No cluster found',
        }
        msg = statusStrings.get(status, 'Exit status: %d' % status)
        _logger.warning(msg)

    return status


def startEngines(numTrials, batchTemplate):
    """
    Uses the batch file created when the cluster was started, so it has
    the profile, cluster-id, and ntasks-per-node already set.
    """
    from pygcam.config import getParamAsInt
    from pygcam.utils import shellCommand

    tasksPerNode = getParamAsInt('IPP.TasksPerNode')
    maxEngines   = getParamAsInt('IPP.MaxEngines')
    numEngines   = min(numTrials, maxEngines)
    numNodes     = (numEngines // tasksPerNode) + (1 if numEngines % tasksPerNode else 0)

    # TBD: use "ipcluster engines" if there's a way to avoid leaving procs running after shutdown
    # enginesCmd = "ipcluster engines -n %d" % tasksPerNode
    enginesCmd = "sbatch '%s'" % batchTemplate

    for i in range(numNodes):
        _logger.info(enginesCmd)
        status = shellCommand(enginesCmd, shell=True, raiseError=False)
        if status:
            _logger.error('Attempt to launch engines failed; status=%d', status)
            return


def _defaultFromConfig(argDict, name, param):
    '''
    If kwargs doesn't have the named keyword, default to the value of
    the config file param, and set the kwargs dict so this value will
    be used in formatting the template.
    '''
    from pygcam.config import getParam

    if argDict.get(name, None) is None:
        argDict[name] = getParam(param)

    return argDict[name]

def pidFileExists(profile, clusterId):
    """
    Check if a process-id (pid) file exists for this profile and clusterId.

    :param profile: (str) profile name
    :param clusterId: (str) cluster ID
    :return: (bool) True if computed pid file pathname exists, else False
    """
    profileDir = locate_profile(profile)
    basename = 'ipcluster-%s.pid' % clusterId
    pidFile = os.path.join(profileDir, 'pid', basename)
    return os.path.isfile(pidFile)


def startCluster(**kwargs):
    """
    Start an ipyparallel cluster to run `numTrials`, using the given `profile`
    and `cluster_id`, if specified, otherwise using values of config vars
    IPP.Profile and IPP.ClusterId, respectively. Writes out a template batch
    file for use with either SLURM or PBS, depending on settings in the user's
    .pygcam.cfg, which is then used by the ipcluster command when launching
    the controller and engines. If the number of trials to run (`numTrials`)
    is greater than the value of config variable IPP.MaxEngines, this max
    number of engines is run but the time limit per engine is increased to allow
    engine each to run the required number of tasks.

    :param clusterId: (str) an id string for the new cluster
    :param numTrials: (int) the number of GCAM trials to run
    :param otherArgs: (str) other arguments appended to the ipcluster command-line
    :param profile: (str) the ipython profile to use
    :param workDir: (str) a directory to change to before starting the cluster
    :return: (int) exit status from the ipcluster command (zero => success)
    """
    # :param maxEngines: (int) the maximum number of engines that will run at once
    # :param minutesPerRun: (int) the time limit to set for each GCAM trial
    # :param queue: (str) the name of the queue to submit the jobs on
    # _defaultFromConfig(kwargs, 'queue',         'IPP.Queue')
    # _defaultFromConfig(kwargs, 'maxEngines',    'IPP.MaxEngines')

    clusterId = _defaultFromConfig(kwargs, 'clusterId', 'IPP.ClusterId')
    profile   = _defaultFromConfig(kwargs, 'profile',   'IPP.Profile')
    _defaultFromConfig(kwargs, 'minutesPerRun', 'IPP.MinutesPerRun')
    _defaultFromConfig(kwargs, 'otherArgs', 'IPP.OtherClusterArgs')
    _defaultFromConfig(kwargs, 'workDir', 'IPP.WorkDir')

    numTrials = kwargs['numTrials']
    templates = _saveBatchFiles(numTrials, kwargs)
    sleep(1)    # allow files to flush and close

    # If the pid file exists, stop the cluster first
    if pidFileExists(profile, clusterId):
        _logger.info('Stopping cluster "%s"', clusterId)
        stopCluster(profile=profile, cluster_id=clusterId, stop_jobs=True)
        sleep(1)

    # Start cluster with no engines; we add them later based on trial count
    template = "ipcluster start -n 0 --daemonize --profile={profile} --cluster-id={clusterId} --work-dir={workDir} {otherArgs}"
    controllerCmd = template.format(**kwargs)
    status = _clusterCommand(controllerCmd)

    if status == 0:
        startEngines(numTrials, templates['engine'])

    return status


def stopCluster(profile=None, cluster_id=None, stop_jobs=False, other_args=None):
    from pygcam.config import getParam
    from pygcam.utils import shellCommand

    # This allows user to pass empty string (e.g., -c='') to override default
    cluster_id = getParam('IPP.ClusterId') if cluster_id is None else cluster_id
    profile    = getParam('IPP.Profile')   if profile    is None else profile
    other_args = getParam('IPP.OtherClusterArgs') if other_args is None else other_args

    template = "ipcluster stop --profile={profile} --cluster-id={cluster_id} {other_args}"
    cmd = template.format(profile=profile, cluster_id=cluster_id, other_args=other_args)

    # shutdown engines, including those that cluster may not be tracking directly
    try:
        client = ipp.Client(profile=profile, cluster_id=cluster_id, timeout=1)
        client.shutdown(hub=False)
    except:
        pass

    status = _clusterCommand(cmd)

    # kill the engines
    if stop_jobs:
        cmd = getParam('IPP.StopJobsCommand').strip()
        if cmd:
            shellCommand(cmd, shell=True, raiseError=False)

    return status


# if __name__ == '__main__':
