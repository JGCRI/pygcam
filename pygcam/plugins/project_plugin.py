from pygcam.plugin import PluginBase
from pygcam.project import driver
# from pygcam.log import getLogger
# _logger = getLogger(__name__)

VERSION = '0.2'

class ProjectCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Run the steps for a project defined in a project.xml file''',
                  'description' : '''This sub-command reads a single XML input file
                        that defines one or more projects, one or more groups of scenarios, one
                        or more scenarios, and one or more workflow steps. The workflow steps
                        for the chosen project and scenario(s) are run in the order defined.'''}

        super(ProjectCommand, self).__init__('runProj', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('project', help='''The name of the project to run.''')

        parser.add_argument('-g', '--group', type=str, default=None,
                            help='''The name of the scenario group to process. If not specified,
                            the group with attribute default="1" is processed.''')

        parser.add_argument('-G', '--listGroups', action='store_true',
                            help='''List the scenario groups defined in the project file and exit.''')

        parser.add_argument('-l', '--listSteps', action='store_true', default=False,
                            help='''List the steps defined for the given project and exit.
                            Dynamic variables (created at run-time) are not displayed.''')

        parser.add_argument('-L', '--listScenarios', action='store_true', default=False,
                            help='''List the scenarios defined for the given project and exit.
                            Dynamic variables (created at run-time) are not displayed.''')

        parser.add_argument('-n', '--noRun', action='store_true', default=False,
                            help='''Display the commands that would be run, but don't run them.''')

        parser.add_argument('-p', '--projectFile', default=None,
                            help='''The XML file describing the project. If set, command-line
                            argument takes precedence. Otherwise, value is taken from config file
                            variable GCAM.ProjectXmlFile, if defined, otherwise the default
                            is './project.xml'.''')

        parser.add_argument('-q', '--quit', action='store_true',
                            help='''Quit if an error occurs when processing a scenario. By default, the
                            next scenario (if any) is run when an error occurs in a scenario.''')

        parser.add_argument('-s', '--step', dest='steps', action='append',
                            help='''The steps to run. These must be names of steps defined in the
                            project.xml file. Multiple steps can be given in a single (comma-delimited)
                            argument, or the -s flag can be repeated to indicate additional steps.
                            By default, all steps are run.''')

        parser.add_argument('-S', '--scenario', dest='scenarios', action='append',
                            help='''Which of the scenarios defined for the given project should
                            be run. Multiple scenarios can be given in a single (comma-delimited)
                            argument, or the -S flag can be repeated to indicate additional steps.
                            By default, all active scenarios are run.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)

        parser.add_argument('--vars', action='store_true', help='''List variables and their values''')

        return parser   # for auto-doc generation


    def run(self, args):
        driver(args)

PluginClass = ProjectCommand
