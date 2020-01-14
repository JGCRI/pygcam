# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
import os
from .McsSubcommandABC import McsSubcommandABC, clean_help
from pygcam.error import CommandlineError
from pygcam.log import getLogger

_logger = getLogger(__name__)

#
# Changes to make to boilerplate ipython parallel config files. Format is
# {filename : ((match, replacement), (match, replacement)), filename: ...}
#
FileChanges = {
    'ipcluster_config.py': (
        ("#c.IPClusterEngines.engine_launcher_class = 'LocalEngineSetLauncher",
         "c.IPClusterEngines.engine_launcher_class = '{scheduler}'"),

        ("#c.IPClusterEngines.n = ",    # not sure if number is constant across platforms...
         "# Attempt to allocate ~8 GB per engine\nc.IPClusterEngines.n = {engines}"),

        ("#c.IPClusterStart.delay = 1.0",
         "# No need to delay queuing engines with controller on login node\nc.IPClusterStart.delay = 0.1"),

        ("#c.SlurmLauncher.account = u''",
         "c.SlurmLauncher.account = u'{account}'"),

        ("#c.SlurmLauncher.timelimit = u''",
         "c.SlurmLauncher.timelimit = u'{walltime}'"),

        ("#c.SlurmControllerLauncher.batch_file_name = u'slurm_controller.sbatch'",
         "c.SlurmControllerLauncher.batch_template_file = u'slurm_mcs_controller.template'"),

        ("#c.SlurmEngineSetLauncher.batch_file_name = u'slurm_engine.sbatch'",
         "c.SlurmEngineSetLauncher.batch_template_file = u'slurm_mcs_engine.template'"),

        ("#c.PBSControllerLauncher.batch_file_name = u'pbs_controller'",
         "c.PBSControllerLauncher.batch_template_file = u'pbs_mcs_controller.template'"),

        ("#c.PBSEngineSetLauncher.batch_file_name = u'pbs_engine'",
         "c.PBSEngineSetLauncher.batch_template_file = u'pbs_mcs_engine.template'"),

        ("#c.LSFControllerLauncher.batch_file_name = u'lsf_controller'",
         "c.LSFControllerLauncher.batch_template_file = u'lsf_mcs_controller.template'"),

        ("#c.LSFEngineSetLauncher.batch_file_name = u'lsf_engine'",
         "c.LSFEngineSetLauncher.batch_template_file = u'lsf_mcs_engine.template'"),
    ),

    'ipcontroller_config.py': (
        ("#c.HubFactory.client_ip = u''",
         "c.HubFactory.client_ip = u'*'"),

        ("#c.HubFactory.engine_ip = u''",
         "c.HubFactory.engine_ip = u'*'"),
    )
}

class IppSetupCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Start an ipyparallel cluster after generating batch
        file templates based on parameters in .pygcam.cfg and the number of tasks to run.'''}
        super(IppSetupCommand, self).__init__('ippsetup', subparsers, kwargs)

    def addArgs(self, parser):
        defaultAccount = ''
        defaultProfile = 'pygcam'
        defaultEngines = 4
        defaultMinutes = 30
        schedulers = ('Slurm', 'PBS', 'LSF')
        defaultScheduler = schedulers[0]

        parser.add_argument('-a', '--account', default=defaultAccount,
                            help=clean_help('''The account name to use to run jobs on the cluster system.
                            Used by Slurm only. Default is "%s"''' % defaultAccount))

        parser.add_argument('-e', '--engines', type=int, default=defaultEngines,
                            help=clean_help('''Set default number of engines to allow per node.
                            This is overridden by runsim; this value is used when running
                            the cluster "manually". Default value is %d.''' % defaultEngines))

        parser.add_argument('-m', '--minutes', type=int, default=defaultMinutes,
                            help=clean_help('''The default number of minutes to allocate
                            per GCAM run. (Used by Slurm only.) This is used for 
                            the "+b / --batch" and "gt run -D" options only. The 
                            "runsim" sub-command uses the value in 
                            IPP.MinutesPerRun. Default value is %d.''' % defaultMinutes))

        parser.add_argument('-p', '--profile', type=str, default=defaultProfile,
                            help=clean_help('''The name of the ipython profile to create. Set config 
                            variable IPP.Profile to the same value. Default is
                            "%s".''' % defaultProfile))

        parser.add_argument('-s', '--scheduler', choices=schedulers, default=defaultScheduler,
                            help=clean_help('''The resource manager / scheduler your system uses. 
                            Default is %s.''' % defaultScheduler))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from IPython.paths import get_ipython_dir
        import subprocess as subp

        minutes = args.minutes
        walltime = '%d:%02d:00' % (minutes/60, minutes%60)

        formatDict = {'account'  : args.account,
                      'engines'  : args.engines,
                      'scheduler': args.scheduler,
                      'minutes'  : minutes,
                      'walltime' : walltime}

        profile = args.profile

        ipythonDir = get_ipython_dir()
        profileDir = os.path.join(ipythonDir, 'profile_' + profile)

        if os.path.isdir(profileDir):
            raise CommandlineError('Ipython profile directory "%s" already exists. Delete it or choose another name.' % profileDir)

        cmd = 'ipython profile create --parallel ' + profile
        _logger.info('Running command: %s', cmd)
        subp.call(cmd, shell=True)

        for basename, tuples in FileChanges.items():
            pathname = os.path.join(profileDir, basename)
            backup   = pathname + '~'

            if not os.path.isfile(pathname):
                raise CommandlineError('Missing configuration file: "%s"' % pathname)

            _logger.info('Editing config file: %s', pathname)
            os.rename(pathname, backup)
            with open(backup, 'r') as input:
                lines = input.readlines()

            with open(pathname, 'w') as output:
                for line in lines:
                    for pattern, replacement in tuples:
                        if line.startswith(pattern):
                            line = replacement.format(**formatDict) + '\n'
                            break

                    output.write(line)
