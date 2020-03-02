# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from pygcam.log import getLogger
from .McsSubcommandABC import McsSubcommandABC, clean_help

_logger = getLogger(__name__)

def driver(args, tool):
    """
    Run a command for each trialDir or scenarioDir, using str.format to pass
    required args. Possible format args are: projectName, simId, trialNum,
    scenario, simDir, trialDir, and scenarioDir.
    """
    from subprocess import call
    from six.moves import xrange
    from pygcam.config import getSection

    from ..Database import getDatabase
    from ..error import PygcamMcsUserError
    from ..context import Context
    from .. import util as U

    simId    = args.simId
    command  = args.command
    scenario = args.scenario
    noRun    = args.noRun
    trialStr = args.trials

    projectName = getSection()

    if trialStr:
        trials = U.parseTrialString(trialStr)
    else:
        db = getDatabase()
        count = db.getTrialCount(simId)
        trials = xrange(count)

    # TBD: Add groupName
    context = Context(projectName=projectName, simId=simId, scenario=scenario)
    _logger.info('Running iterator for projectName=%s, simId=%d, scenario=%s, trials=%s, command="%s"',
                 projectName, simId, scenario, trialStr, command)

    # Create a dict to pass to str.format. These are constant across trials.
    argDict = {
        'projectName' : projectName,
        'simId'       : args.simId,
        'scenario'    : args.scenario,
        'expName'     : args.scenario,
    }

    for trialNum in trials:
        argDict['trialNum'] = context.trialNum = trialNum
        argDict['expDir']   = argDict['scenarioDir'] = context.getScenarioDir(create=True)
        argDict['trialDir'] = context.getTrialDir()
        argDict['simDir']   = context.getSimDir()

        try:
            cmd = command.format(**argDict)
        except Exception as e:
            raise PygcamMcsUserError("Bad command format: %s" % e)

        if noRun:
            print(cmd)
        else:
            try:
                call(cmd, shell=True)

            except Exception as e:
                raise PygcamMcsUserError("Failed to run command '%s': %s" % (cmd, e))


class IterateCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Run a command in each trialDir, or if scenario is given, 
        in each expDir. The following arguments are available for use in the command string,
        specified within curly braces: projectName, simId, trialNum, scenario, expName (a
        legacy alias for scenario), trialDir, scenarioDir, and expDir (a legacy alias for
        scenarioDir). For example, to run the fictional program "foo" in each trialDir for 
        a given set of parameters, you might write:
        gt iterate -s1 -c "foo -s{simId} -t{trialNum} -i{trialDir}/x -o{trialDir}/y/z.txt".'''}
        super(IterateCommand, self).__init__('iterate', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('-c', '--command', type=str, required=True,
                            help=clean_help('''A command string to execute for each trial. The following
                            arguments are available for use in the command string, specified
                            within curly braces: projectName, simId, trialNum, scenario, expName, 
                            trialDir, expDir.'''))

        parser.add_argument('-n', '--noRun', action='store_true',
                            help=clean_help("Show the commands that would be executed, but don't run them"))

        parser.add_argument('-s', '--simId', type=int, default=1,
                            help=clean_help('The id of the simulation. Default is 1.'))

        parser.add_argument('-S', '--scenario', type=str, default="",
                            help=clean_help('The name of the scenario'))

        parser.add_argument('-t', '--trials', type=str, default=None,
                             help=clean_help('''Comma separated list of trial or ranges of trials to run. Ex: 1,4,6-10,3.
                             Defaults to running all trials for the given simulation.'''))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
