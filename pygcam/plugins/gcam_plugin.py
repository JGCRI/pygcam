'''
.. Created on: 2/26/15

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import platform
from pygcam.plugin import PluginBase
from pygcam.log import getLogger
from pygcam.config import DEFAULT_SECTION
from pygcam.run import driver

PROGRAM = os.path.basename(__file__)
VERSION = "0.2"

PlatformName = platform.system()

_logger = getLogger(__name__)


class GcamCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Run the GCAM executable''',
                  'description' : '''Queue a GCAM job on a Linux cluster or run the job
                  locally (via "-l" flag). (On OS X, the "-l" flag is not needed; only
                  local running is supported.)'''}

        super(GcamCommand, self).__init__('gcam', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('-c', '--configSection', type=str, default=DEFAULT_SECTION,
                            help='''The name of the section in the config file to read from.
                            Defaults to %s''' % DEFAULT_SECTION)

        parser.add_argument('-C', '--configFile', type=str, default=None,
                            help='''Specify the one or more GCAM configuration filenames, separated commas.
                                    If multiple configuration files are given, the are run in succession in
                                    the same "job" on the cluster.
                                    N.B. This argument is ignored if scenarios are named via the -s flag.''')

        parser.add_argument('-E', '--enviroVars', type=str, default=None,
                            help='''Comma-delimited list of environment variable assignments to pass
                                    to qsub, e.g., -E "FOO=1,BAR=2".''')

        parser.add_argument('-j', '--jobName', type=str, default='queueGCAM',
                            help='''Specify a name for the queued job. Default is "queueGCAM".''')

        parser.add_argument('-l', '--runLocal', action='store_true', default=(PlatformName in ['Darwin', 'Windows']),
                            help='''Run GCAM locally on current host, not via qsub. (It's not necessary
                                    to specify this flag on OS X and Windows since only local execution
                                    is supported.)''')

        parser.add_argument('-m', '--minutes', type=float,
                            help='''Set the number of minutes to allocate for each job submitted.
                                    Overrides config parameter GCAM.Minutes.''')

        parser.add_argument('-n', '--noRun', action="store_true",
                            help="Show the 'qsub' command to be run, but don't run it")

        parser.add_argument('-N', '--noRunGCAM', action="store_true",
                            help="Don't run GCAM, just run the post-processing script on existing results.")

        parser.add_argument('-r', '--resources', type=str, default='',
                            help='''Specify resources for the qsub command. Can be a comma-delimited list of
                                    assignments NAME=value, e.g., -r pvmem=6GB.''')

        parser.add_argument('-p', '--postProcessor', type=str, default='',
                            help='''Specify the path to a script to run after GCAM completes. It should accept three
                                    command-line arguments, the first being the path to the workspace in which GCAM
                                    was executed, the second being the name of the configuration file used, and the
                                    third being the scenario name of interest. Defaults to value of configuration
                                    parameter GCAM.PostProcessor.''')

        parser.add_argument('-P', '--noPostProcessor', action='store_true', default=False,
                            help='''Don't run the post-processor script. (Use this to skip post-processing when a script
                                    is named in the ~/.gcam.cfg configuration file.)''')

        parser.add_argument('-Q', '--queueName', type=str, default=None,
                            help='''Specify a queue name for qsub. Default is given by config file
                                    param GCAM.DefaultQueue.''')

        parser.add_argument('-s', '--scenario', type=str, default='',
                            help='''Specify the scenario(s) to run. Can be a comma-delimited list of scenario names.
                                    The scenarios will be run serially in a single batch job, with an allocated
                                    time = GCAM.Minutes * {the number of scenarios}.''')

        parser.add_argument('-S', '--scenariosDir', type=str, default='',
                            help='''Specify the directory holding scenarios. Default is the value of config file param
                            GCAM.ScenariosDir, if set, otherwise ".".''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)

        parser.add_argument('-w', '--workspace', type=str, default=None,
                            help='''Specify the path to the GCAM workspace to use. If it doesn't exist, the named workspace
                                    will be created. If not specified on the command-line, the value of config file parameter
                                    GCAM.Workspace is used, i.e., the "standard" workspace.''')

        return parser

    def run(self, args):
        driver(args)

PluginClass = GcamCommand
