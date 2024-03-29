'''
.. Created on: 2/26/15

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2023 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from ..subcommand import SubcommandABC, clean_help, Deprecate

class GcamCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Run GCAM for the indicated configFile, scenario, or workspace.'''}
        super(GcamCommand, self).__init__('gcam', subparsers, kwargs, group='project', label='GCAM')

    def addArgs(self, parser):
        parser.add_argument('-C', '--configFile',
                            help=clean_help('''Specify the one or more GCAM configuration filenames, separated by commas.
                            If multiple configuration files are given, the are run in succession in the
                            same "job" on the cluster.'''))

        parser.add_argument('-g', '--group', default='',
                            help=clean_help('The scenario group name, if any.'))

        parser.add_argument('-n', '--noRun', action='store_true',
                            help=clean_help('''Don't run GCAM; just print the command that would be run.'''))

        parser.add_argument('-s', '--scenario', default='',
                            help=clean_help('''The scenario to run.'''))

        parser.add_argument('-x', '--sandbox',
                            help=clean_help('''Specify the path to the GCAM sandbox to use. If the named workspace 
                            doesn't exist, an exception is raised. If not specified on the command-line, the path
                            constructed as {GCAM.SandboxDir}/{optional-groupdir}/{scenario} is used, if scenario 
                            is defined.'''))

        parser.add_argument('-W', '--noWrapper', action='store_true',
                            help=clean_help('''Do not run gcam within a wrapper that detects errors as early as possible
                            and terminates the model run. By default, the wrapper is used.'''))

        # Deprecations
        parser.add_argument('-w', '--workspace', action=Deprecate, alt_text="Use -x / --sandbox instead.")
        parser.add_argument('-f', '--forceCreate', action=Deprecate)
        parser.add_argument('-r', '--refWorkspace', action=Deprecate)
        parser.add_argument('-S', '--scenariosDir', action=Deprecate)

        return parser

    def run(self, args, tool):
        from ..gcam import runGCAM
        from ..mcs.sim_file_mapper import get_mapper

        mapper = get_mapper(args.scenario, scenario_group=args.group)
        runGCAM(mapper, noRun=args.noRun, noWrapper=args.noWrapper)
