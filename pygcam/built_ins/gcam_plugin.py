'''
.. Created on: 2/26/15

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from ..subcommand import SubcommandABC, clean_help

class GcamCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Run GCAM for the indicated configFile, scenario, or workspace.'''}
        super(GcamCommand, self).__init__('gcam', subparsers, kwargs, group='project', label='GCAM')

    def addArgs(self, parser):
        # parser.add_argument('-c', '--copyWorkspace', action='store_true',
        #                     help=clean_help('''Create a copy of the source workspace in the location specified
        #                     by GCAM.'''))

        parser.add_argument('-C', '--configFile',
                            help=clean_help('''Specify the one or more GCAM configuration filenames, separated by commas.
                            If multiple configuration files are given, the are run in succession in the
                            same "job" on the cluster.'''))

        parser.add_argument('-f', '--forceCreate', action='store_true',
                            help=clean_help('''Re-create the workspace, even if it already exists.'''))

        parser.add_argument('-g', '--groupDir', default='',
                            help=clean_help('The scenario group directory name, if any.'))

        parser.add_argument('-n', '--noRun', action='store_true',
                            help=clean_help('''Don't run GCAM; just print the command that would be run.'''))

        parser.add_argument('-r', '--refWorkspace',
                            help=clean_help('''The reference workspace to use to create the new sandbox. This is
                            used only if the indicated or implied workspace doesn't exist. Defaults
                            to the value of GCAM.RefWorkspace.'''))

        parser.add_argument('-s', '--scenario', default='',
                            help=clean_help('''The scenario to run.'''))

        parser.add_argument('-S', '--scenariosDir', default='',
                            help=clean_help('''Specify the directory holding scenario files. Default is the value of
                            config variable GCAM.ScenariosDir, if set, otherwise it's the current directory.'''))

        parser.add_argument('-w', '--workspace',
                            help=clean_help('''Specify the path to the GCAM workspace to use. If it doesn't exist, the
                            named workspace will be created. If not specified on the command-line, the path
                            constructed as {GCAM.SandboxDir}/{scenario} is used.'''))

        parser.add_argument('-W', '--noWrapper', action='store_true',
                            help=clean_help('''Do not run gcam within a wrapper that detects errors as early as possible
                            and terminates the model run. By default, the wrapper is used.'''))
        return parser

    def run(self, args, tool):
        from ..gcam import gcamMain
        gcamMain(args)
