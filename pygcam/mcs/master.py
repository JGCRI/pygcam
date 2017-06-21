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
from six import iteritems
import os
import stat
import sys
from time import sleep
from IPython.paths import locate_profile

import ipyparallel as ipp
# Exit codes for ipcluster command
from ipyparallel.apps.ipclusterapp import ALREADY_STARTED, ALREADY_STOPPED, NO_CLUSTER

from .error import IpyparallelError
from pygcam.log import getLogger

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
srun %s --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
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
%s --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
"""

_pbsControllerBatchTemplate = """#!/bin/sh
#PBS -V
#PBS -N {cluster_id}-controller
#PBS -q {queue}
#PBS -l walltime={timelimit}
%s --profile-dir="{profile_dir}" --cluster-id="{cluster_id}"
"""

# TBD: test PBS (where?)
batchTemplates = {'slurm' : {'engine'     : _slurmEngineBatchTemplate,
                             'controller' : _slurmControllerBatchTemplate},

                  'pbs'   : {'engine'     : _pbsEngineBatchTemplate,
                             'controller' : _pbsControllerBatchTemplate}
                  }

class Master(object):
    def __init__(self, args):
        from .Database import getDatabase

        self.args = args
        self.db = getDatabase(checkInit=False)
        self.client = None
        self.foundWorkers = False

    def waitForWorkers(self):
        from pygcam.config import getParamAsInt

        maxTries = getParamAsInt('IPP.StartupWaitTries')
        seconds  = getParamAsInt('IPP.StartupWaitSecs')
        client = None
        profile = self.args.profile
        clusterId = self.args.clusterId

        for i in range(maxTries):
            if not client:
                try:
                    # default timeout is 10 seconds
                    self.client = client = ipp.Client(profile=profile, cluster_id=clusterId)

                except IOError:
                    if i == maxTries - 1:
                        raise

                    _logger.info("Waiting for client (try %d of %d)", i, maxTries)
                    sleep(seconds)
                    continue

            if len(client) == 0:
                _logger.info("Waiting for engines (try %d of %d)", i, maxTries)
                sleep(seconds)

        if not client or len(client) == 0:
            raise IpyparallelError('Failed to connect to engines')

        # Apparently this is not necessary...
        # _logger.debug('Connected to controller; initializing workers.')
        # dview = client[:]
        # dview.execute('from pygcam.mcs.worker import runTrial')
        self.foundWorkers = True

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

        for key, value in iteritems(status):
            _logger.debug('  %s: %s', key, value)

        idleEngines = []

        unassigned = u'unassigned'

        # Shutdown idle engines if there are no unassigned tasks
        if status[unassigned] == 0:
            # collect ids of idle engines
            for id, stats in iteritems(status):
                if id == unassigned:    # ignore
                    continue

                _logger.debug('%d: %s', id, stats)
                if stats[u'tasks'] == 0 and stats[u'queue'] == 0:
                    idleEngines.append(id)

        if idleEngines:
            _logger.info('Shutting down engines %s', idleEngines)
            self.client.shutdown(targets=idleEngines, block=True)

            maxTries = 4
            seconds  = 1

            expectedEngines = len(self.client) - len(idleEngines)
            for i in range(maxTries):
                if len(self.client) != expectedEngines:
                    sleep(seconds)

            # TBD: handle timeout waiting for engines to stop

            _logger.debug("%d engines active", len(self.client))

    def createRuns(self, simId, scenario, trialNums):
        '''
        Create entries in the "run" table for the given simId, trialNums, and scenario.

        :param simId: (int) simulation ID
        :param scenario: (str) scenario name
        :param trialNums: (list of int) trial numbers
        :return: list of (runId, trialNum) tuples
        '''
        from .error import PygcamMcsUserError

        db = self.db
        session = db.Session()

        expId = db.getExpId(scenario)
        if expId is None:
            raise PygcamMcsUserError("Unknown scenario '%s'" % scenario)

        runs = []

        # Add a run record for each trial in this chunk
        for trialNum in trialNums:
            # Add a record in the "run" table listing this trial as "new"
            # (row for this simid, trialnum and expid is deleted if it exists)
            newRun = db.createRun(simId, trialNum, expId=expId, session=session)
            runs.append(newRun)

        session.commit()
        db.endSession(session)
        results = map(lambda run: (run.runId, run.trialNum), runs)
        return results

    # deprecated
    # def gather(self, category):
    #     """
    #     Collect message ids from the hub for the given `category`.
    #
    #     :param category: (str) one of 'queue', 'tasks', or 'completed'.
    #     :return: (list of str) message ids of the tasks in the category.
    #     """
    #     result = []
    #
    #     for key, value in self.client.queue_status(verbose=False).items():
    #         if type(key) == int:
    #             result.extend(value[category])
    #
    #     return result

    def runningTasks(self):
        from pygcam.utils import flatten

        # recs = self.client.db_query({'started': {'$ne': None}, 'completed': None}, keys=['msg_id'])
        qstatus = self.client.queue_status(verbose=True)
        ids = [rec['tasks'] for key, rec in iteritems(qstatus) if isinstance(key, (int, long))]
        return flatten(ids)

    def completedTasks(self):
        # def getId(rec):
        #     try:
        #         return rec['msg_id']
        #     except KeyError:
        #         # shouldn't happen, but something is blowing out...
        #         _logger.error('completedTasks: rec is missing msg_id field')

        recs = self.client.db_query({'completed': {'$ne': None}}, keys=['msg_id'])
        ids = [rec['msg_id'] for rec in recs] if recs else None
        return ids

    def processTrials(self, loopOnly=False, addTrials=False):
        """
        If `loopOnly` is False, run the trials identified in self.args. If
        `addTrials` is True, exit after running the trials, otherwise, loop
        until all tasks are completed, if "shutdown when idle" was given as
        a command-line arg, or loop indefinitely, allowing another task to
        add more trials to run.

        :param loopOnly: (bool) If True, run no trials; just enter the processing
            loop, otherwise run the trials given in self.args.trials
        :param addTrials: (bool) If True, exit after starting the trials (i.e.,
           don't wait for their results; presumably another client is doing that.)
        :return: none
        """
        from .Database import RUN_RUNNING, RUN_SUCCEEDED
        from .XMLResultFile import saveResults, RESULT_TYPE_SCENARIO, RESULT_TYPE_DIFF
        from ipyparallel.client.client import ExecuteReply

        db = self.db
        args = self.args

        if args.redoListOnly and args.statuses:
            listTrialsToRedo(db, args.simId, args.scenarios, args.statuses)
            return

        self.waitForWorkers()    # wait for engines to spin up

        updateDatabase = args.updateDatabase

        if not loopOnly:
            self.runTrials()

        if addTrials:
            # don't wait for results; just add trials to running cluster
            return

        client = self.client
        trialStatus = {}

        while True:
            # Check for newly running tasks
            running = self.runningTasks()
            if running:
                _logger.debug("%d tasks are running", len(running))
                ar = client.get_result(running, block=False)

                for dataDict in ar.data:
                    for runId, status in iteritems(dataDict):
                        _logger.debug('runId:%s status:%s', runId, status)
                        if status == RUN_RUNNING and trialStatus.get(runId) is None:
                            trialStatus[runId] = status
                            if updateDatabase:
                                _logger.debug('Setting runId %s to %s', runId, RUN_RUNNING)
                                db.setRunStatus(runId, RUN_RUNNING)

            completed = self.completedTasks()
            if completed:
                ar = client.get_result(completed, owner=True)
                # _logger.debug('Completed msg_ids: %s', completed)
                results = ar.get()

                # filter out results from execute command (e.g. imports)
                results = [r for r in results if not isinstance(r, ExecuteReply)]
                _logger.debug("%d completed tasks with results", len(results))

                # update database status
                if updateDatabase:
                    _logger.info("Processing %d results", len(results))

                    for resultsList in results:
                        result = resultsList[0]

                        runId    = result.runId
                        status   = result.status
                        context  = result.context
                        scenario = context.expName
                        baseline = context.baseline

                        _logger.debug('Setting runId %s to %s', runId, status)
                        db.setRunStatus(runId, status)

                        if status == RUN_SUCCEEDED:
                            saveResults(runId, scenario, RESULT_TYPE_SCENARIO)

                            if baseline:  # also save 'diff' results
                                saveResults(runId, scenario, RESULT_TYPE_DIFF, baseline=baseline)

                # remove processed results from client and hub
                client.purge_results(jobs=completed)

            moreCompleted = self.completedTasks()

            if not moreCompleted:
                # See if anything remains outstanding
                qtotals = self.queueTotals()
                _logger.debug('All engines: %s' % qtotals)
                if (args.shutdownWhenIdle and
                    qtotals['unassigned'] == 0 and qtotals['queue'] == 0 and qtotals['tasks'] == 0):
                    break

                _logger.debug('wait(%d)', args.waitSecs)
                sleep(args.waitSecs)

            # Shutdown idle engines when desired and possible
            if args.shutdownWhenIdle:
                self.shutdownIdleEngines()

        # Shutdown the hub
        if args.shutdownWhenIdle:
            _logger.info("Shutting down hub...")
            sleep(3)   # allow sockets to clear
            self.client.shutdown(hub=True, block=True)

    def runTrials(self):
        from argparse import Namespace
        from .util import parseTrialString
        from .worker import runTrial

        args = self.args

        simId     = args.simId
        statuses  = args.statuses
        scenarios = args.scenarios

        asyncResults = []
        view = self.client.load_balanced_view()

        for scenario in scenarios:

            if statuses:
                # If any of the "redo" options find trials, use these instead of args.trials
                tuples = self.db.getRunsByStatus(simId, scenario, statuses)

                if not tuples:
                    _logger.warn("No trials found for simId=%s, scenario=%s with statuses=%s",
                                 simId, scenario, statuses)
                    continue
            else:
                trialCount = self.db.getTrialCount(simId)

                if args.trials:
                    # convert arg string like "4,7,9-12,42" to a list of ints
                    trials = parseTrialString(args.trials)
                    userTrials = len(trials)

                    # remove values that don't make sense, and warn user about them
                    trialNums = filter(lambda trial: 0 <= trial < trialCount, trials)
                    goodTrials = len(trialNums)
                    if goodTrials != userTrials:
                        _logger.warn('Ignoring %d trial numbers that are out of range [0,%d]',
                                     userTrials - goodTrials, trialCount)
                else:
                    # if trials aren't specified, queue all of them
                    trialNums = range(trialCount)

                tuples = self.createRuns(simId, scenario, trialNums)

            argDict = vars(args)
            argDict['scenario'] = scenario
            argDict['baseline'] = self.db.getExpParent(scenario)

            try:
                for runId, trialNum in tuples:
                    argDict['trialNum'] = trialNum
                    argDict['runId'] = runId
                    trialArgs = Namespace(**argDict)

                    # Easier to deal with a list of AsyncResults instances than a
                    # single instance that contains info about all "future" results.
                    result = view.map_async(runTrial, [trialArgs])
                    asyncResults.append(result)

            except Exception as e:
                _logger.error("Exception running 'runTrial': %s", e)

        return asyncResults


def listTrialsToRedo(db, simId, scenarios, statuses):
    from .util import createTrialString

    for scenario in scenarios:
        # If any of the "redo" options find trials, use these instead of args.trials
        tuples = db.getRunsByStatus(simId, scenario, statuses)

        if tuples:
            # Just print the corresponding trial string
            trialNums = map(lambda tuple: tuple[1], tuples)  # unpack(runId, trialNum) tuple
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
       "profile", "cluster_id", "tasks_per_node", "num_engines", and "timelimit"
       are substituted into the batch templates. For most of these, defaults
       are taken from ~/.pygcam.cfg and overridden by argDict. Both "ntasks"
       and "timelimit" are computed on-the-fly.
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

    defaults = {'scheduler'      : getParam('IPP.Scheduler'),
                'account'        : getParam('IPP.Account'),
                'queue'          : getParam('IPP.Queue'),
                'cluster_id'     : argDict['clusterId'],
                'tasks_per_node' : getParamAsInt('IPP.TasksPerNode'),
                'timelimit'      : timelimit,
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
    numNodes     = numEngines // tasksPerNode + (1 if numEngines % tasksPerNode else 0)

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
    _defaultFromConfig(kwargs, 'otherArgs',     'IPP.OtherArgs')
    _defaultFromConfig(kwargs, 'workDir',       'IPP.WorkDir')

    numTrials = kwargs['numTrials']
    templates = _saveBatchFiles(numTrials, kwargs)
    sleep(1)    # allow files to flush and close

    # If the pid file exists, stop the cluster first
    if pidFileExists(profile, clusterId):
        stopCluster(profile=profile, cluster_id=clusterId)
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
    other_args = getParam('IPP.OtherArgs') if other_args is None else other_args

    template = "ipcluster stop --profile={profile} --cluster-id={cluster_id} {other_args}"
    cmd = template.format(profile=profile, cluster_id=cluster_id, other_args=other_args)

    # shutdown engines that cluster may not be tracking directly
    try:
        client = ipp.Client(profile=profile, cluster_id=cluster_id, timeout=1)
        client.shutdown(hub=False)
    except:
        pass

    status = _clusterCommand(cmd)
    if stop_jobs:
        cmd = getParam('IPP.StopJobsCommand').strip()
        if cmd:
            shellCommand(cmd, shell=True, raiseError=False)

    return status


# if __name__ == '__main__':
