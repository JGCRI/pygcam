# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from .McsSubcommandABC import McsSubcommandABC, clean_help

def driver(args, tool):
    """
    Start or stop an ipyparallel cluster. If starting the cluster, the number of
    engines launched is determined from the number of tasks to run (`ntasks`) and
    the maximum number of engines indicated in config file param IPP.MaxEngines.
    Wall time allowed per engine is computed from these values and config file
    variable IPP.MinutesPerRun.
    """
    from ..master import startCluster, stopCluster

    if args.mode == 'start':
        argDict = vars(args)
        startCluster(**argDict)
    else:
        stopCluster(profile=args.profile, cluster_id=args.clusterId,
                    stop_jobs=args.stopJobs, other_args=args.otherArgs)


class ClusterCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Start an ipyparallel cluster after generating batch
        file templates based on parameters in .pygcam.cfg and the number of tasks to run.'''}
        super(ClusterCommand, self).__init__('cluster', subparsers, kwargs)

    def addArgs(self, parser):
        from pygcam.config import getParam, getParamAsFloat, getParamAsInt

        defaultProfile     = getParam('IPP.Profile')
        defaultClusterId   = getParam('IPP.ClusterId')
        defaultQueue       = getParam('IPP.Queue')
        defaultWorkDir     = getParam('IPP.WorkDir')
        defaultStopJobsCmd = getParam('IPP.StopJobsCommand')

        defaultMaxEngines = getParamAsInt('IPP.MaxEngines')
        defaultMinutes    = getParamAsFloat('IPP.MinutesPerRun')

        parser.add_argument('mode', choices=['start', 'stop'],
                            help=clean_help('''Whether to start or stop the cluster'''))

        parser.add_argument('-c', '--clusterId', type=str, default=defaultClusterId,
                            help=clean_help('''A string to identify this cluster. Default is the
                            value of config var IPP.ClusterId, currently
                            "%s".''' % defaultClusterId))

        parser.add_argument('-e', '--maxEngines', type=int, default=defaultMaxEngines,
                            help=clean_help('''Set maximum number of engines to create.
                            Overrides config parameter IPP.MaxEngines, currently
                            %s''' % defaultMaxEngines))

        parser.add_argument('-m', '--minutesPerRun', type=int, default=defaultMinutes,
                            help=clean_help('''Set the number of minutes of walltime to allocate
                            per GCAM run.  Overrides config parameter IPP.MinutesPerRun,
                            currently %s.''' % defaultMinutes))

        parser.add_argument('-n', '--numTrials', type=int, default=10,
                            help=clean_help('''The total number of GCAM trials that will be run on this
                            cluster. (Relevant only for "start" command.)'''))

        parser.add_argument('-o', '--otherArgs', type=str, default='',
                            help=clean_help('Command line arguments to append to the ipcluster command.'))

        parser.add_argument('-p', '--profile', type=str, default=defaultProfile,
                            help=clean_help('''The name of the ipython profile to use. Default is
                            the value of config var IPP.Profile, currently
                            "%s".''' % defaultProfile))

        parser.add_argument('-q', '--queue', type=str, default=defaultQueue,
                            help=clean_help('''The queue or partition on which to create the controller
                            and engines. Overrides config var IPP.Queue, currently
                            "%s".''' % defaultQueue))

        parser.add_argument('-s', '--stopJobs', action='store_true',
                            help=clean_help('''Stop running jobs using the value if IPP.StopJobsCommand,
                            currently "%s". (Ignored for mode "start".)''' % defaultStopJobsCmd))

        parser.add_argument('-w', '--workDir', type=str, default=defaultWorkDir,
                            help=clean_help('''Where to run the ipcluster command. Overrides the
                            value of config var IPP.WorkDir, currently '%s'.''' % defaultWorkDir))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
