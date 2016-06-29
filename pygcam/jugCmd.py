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
import os
import subprocess
import pipes
from .error import CommandlineError, ConfigFileError, ProgramExecutionError, PygcamException
from .config import getParam, getParamAsInt
from .utils import mkdirs, getTempFile, parseTrialString, createTrialString, chunkify
from .subcommand import SubcommandABC
from .log import getLogger

PROGRAM = os.path.basename(__file__)
__version__ = "0.1"

_logger = getLogger(__name__)

#
# TBD: duplicated from tool.py to avoid mutual imports
#
def _writeBatchScript(args):
    """
    Create a shell script in a temporary file which calls gt with the
    given `args`.
    :param args: (list of str) arguments to "gt" to write into a
        script to be executed as a batch job
    :param delete: (bool) if True, mark the tmp file for deletion.
    :return: (str) the pathname of the script
    """
    tmpDir = getParam('GCAM.UserTempDir')
    mkdirs(tmpDir)

    scriptFile  = getTempFile(suffix='.pygcam.sh', tmpDir=tmpDir, delete=False)
    _logger.info("Creating batch script '%s'", scriptFile)

    jugCmd = getParam('GCAM.JugCommand')
    jugFile = getParam('GCAM.JugScript')

    with open(scriptFile, 'w') as f:
        # jug doesn't pass through args starting with '--', so we strip
        # those and add them back in jugWorker.py. A bit of a hack...
        shellArgs = [jugCmd, 'execute', jugFile,
                     'simId='    + str(args.simId),
                     'trials='   + args.trials,
                     'baseline=' + pipes.quote(args.baseline),
                     'scenario=' + pipes.quote(args.scenario),
                     ]
        f.write("#!/bin/bash\n")
        f.write("rm -f %s\n" % pipes.quote(scriptFile)) # file removes itself once running
        f.write(' '.join(shellArgs))
        f.write('\n')

    os.chmod(scriptFile, 0755)
    return scriptFile


def runWorkers(args, run=True):
    import platform

    system = platform.system()
    if False and system in ['Windows', 'Darwin']:
        system = 'Mac OS X' if system == 'Darwin' else system
        raise CommandlineError('Batch commands are not supported on %s' % system)

    jobName = args.jobName
    queueName = args.queueName or getParam('GCAM.DefaultQueue')
    logFile = args.logFile or getParam('GCAM.BatchLogFile', raw=False)
    minutes = args.minutes or float(getParam('GCAM.Minutes'))
    walltime = "%02d:%02d:00" % (minutes / 60, minutes % 60)

    if logFile:
        logDir = getParam('GCAM.BatchLogDir')
        logFile = os.path.normpath(os.path.join(logDir, logFile))
        mkdirs(os.path.dirname(logFile))

    tasksPerNode = args.ntasksPerNode or getParamAsInt('GCAM.JugTasksPerNode')
    batchCmd = getParam('GCAM.BatchCommand') + '--ntasks-per-node=%d' % tasksPerNode

    # TBD: default should be the 0-(number of trials in the sim minus 1)
    # TBD: deal with this when the database is integrated into this
    trialList = parseTrialString(args.trials) if args.trials else ['0']
    numTrials = len(trialList)
    if numTrials < args.nodes:
        _logger.info('Reducing requested node count(%d) to number of trials (%d)',
                               args.nodes, numTrials)
        args.nodes = numTrials

    for trialSublist in chunkify(trialList, args.nodes):

        args.trials = createTrialString(trialSublist)
        scriptFile = _writeBatchScript(args)

        # This dictionary is applied to the string value of GCAM.BatchCommand, via
        # the str.format method, which must specify options using any of the keys.
        batchArgs = {'scriptFile': scriptFile,
                     'logFile': logFile,
                     'minutes': minutes,
                     'walltime': walltime,
                     'queueName': queueName,
                     'jobName': jobName}

        try:
            command = batchCmd.format(**batchArgs)
        except KeyError as e:
            raise ConfigFileError('Badly formatted batch command (%s) in config file: %s', batchCmd, e)

        # deal with problem "%" chars used by SLURM variables
        if getParam('GCAM.BatchLogFileDollarToPercent'):
            command = command.replace('$', '%')

        # TBD: this assumes SLURM...
        # Add the --array arg to process a subset of runs on each node
        tasks = min(tasksPerNode, len(trialSublist))
        command += ' --array=1-%d' % tasks

        if not run:
            print(command)
            print("Script file '%s':" % scriptFile)
            with open(scriptFile) as f:
                print(f.read())
            os.remove(scriptFile)
            return

        _logger.info('Running: %s', command)
        try:
            exitCode = subprocess.call(command, shell=True)
            if exitCode != 0:
                raise ProgramExecutionError(command, exitCode)

        except Exception as e:
            raise PygcamException("Error running command '%s': %s" % (command, e))


class JugCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Run jug to queue worker processes to run a Monte Carlo simulation.'''}
        super(JugCommand, self).__init__('jug', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('--baseline', required=True,
                            help='''The name of the baseline scenario to run''')

        parser.add_argument('--scenario', required=True,
                            help='''Specify the scenario(s) to run. Can be a comma-delimited list of
                            scenario names.''')

        parser.add_argument('-s', '--simId', type=int, required=True,
                            help='The id of the simulation')

        parser.add_argument('-n', '--noRun', action='store_true',
                            help="Show the commands that would be executed, but don't run them")

        parser.add_argument('-N', '--nodes', type=int, default=1,
                            help='''Request that at least this many nodes are allocated for jug workers''')

        parser.add_argument('--ntasksPerNode', type=int,
                            help='''The number of worker tasks to run per compute node (default is the value
                            config variable GCAM.JugTasksPerNode)''')

        parser.add_argument('-t', '--trials', type=str, default=None,
                            help='''Comma separated list of trial or ranges of trials to run. Ex: 1,4,6-10,3.
                             Defaults to running all trials for the given simulation.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

        return parser

    def run(self, args, tool):
        runWorkers(args)

PluginClass = JugCommand    # in case this becomes a true plug-in
