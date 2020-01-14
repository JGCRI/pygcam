# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from .McsSubcommandABC import McsSubcommandABC, clean_help

def driver(args, tool):
    """
    Start ipyparallel engines.
    """
    from pygcam.config import getParam
    from ..master import startEngines, templatePath

    scheduler = getParam('IPP.Scheduler')
    batchTemplate = templatePath(scheduler, args.profile, args.clusterId, 'engine')
    startEngines(args.numTrials, batchTemplate)


class EngineCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Starts additional worker engines on a running cluster.'''}
        super(EngineCommand, self).__init__('engine', subparsers, kwargs)

    def addArgs(self, parser):
        from pygcam.config import getParam #, getParamAsInt

        # defaultQueue     = getParam('IPP.Queue')
        defaultProfile   = getParam('IPP.Profile')
        defaultClusterId = getParam('IPP.ClusterId')
        defaultWorkDir   = getParam('IPP.WorkDir')
        defaultNumTrials = 1

        parser.add_argument('-c', '--clusterId', type=str, default=defaultClusterId,
                            help=clean_help('''A string to identify this cluster. Default is the
                            value of config var IPP.ClusterId, currently
                            "%s".''' % defaultClusterId))

        parser.add_argument('-n', '--numTrials', type=int, default=defaultNumTrials,
                            help=clean_help('''The number of additional trials to create engines for.
                            Default is %d''' % defaultNumTrials))

        parser.add_argument('-o', '--otherArgs', type=str, default='',
                            help=clean_help('Command line arguments to append to the ipengine command.'))

        parser.add_argument('-p', '--profile', type=str, default=defaultProfile,
                            help=clean_help('''The name of the ipython profile to use. Default is
                            the value of config var IPP.Profile, currently
                            "%s".''' % defaultProfile))

        # parser.add_argument('-q', '--queue', type=str, default=defaultQueue,
        #                     help=clean_help('''The queue or partition on which to create the controller
        #                     and engines. Overrides config var IPP.Queue, currently
        #                     "%s".''' % defaultQueue))

        parser.add_argument('-w', '--workDir', type=str, default=defaultWorkDir,
                            help=clean_help('''Where to run the ipengine command. Overrides the
                            value of config var IPP.WorkDir, currently '%s'.''' % defaultWorkDir))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
