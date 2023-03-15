'''
.. gcamtool plugin for setting up / customizing GCAM project's XML files.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016-2023 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from ..log import getLogger
from ..subcommand import SubcommandABC, clean_help
from ..constants import McsMode

_logger = getLogger(__name__)

class SetupCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help': '''Setup a scenario by creating modified XML input files.'''}

        super(SetupCommand, self).__init__('setup', subparsers, kwargs, group='project')

    # TBD: current cmd in project.xml:
    #   @setup -b {baseline} -s {scenario} -g {scenarioGroup} -S {scenarioSubdir} -w {scenarioDir} -p {endYear} -y {shockYear}-{endYear}
    #   Most of the remaining args may be superfluous.
    def addArgs(self, parser):
        defaultYears = '2015-2100'

        yes_or_no = ['yes', 'no']

        group1 = parser.add_mutually_exclusive_group()  # --dynamicOnly, --staticOnly
        group2 = parser.add_mutually_exclusive_group()  # --modulePath, --moduleSpec, --setupXml

        # Deprecated? Can determine this from scenarios.xml
        parser.add_argument('-b', '--baseline',
                            help=clean_help('''Identify the baseline the selected scenario is based on.
                                 Note: at least one of --baseline (-b) / --scenario (-s) must be used.'''))

        parser.add_argument('--createSandbox', choices=yes_or_no, default='yes',
                            help='''Whether to create the run-time sandbox directory from the reference workspace.
                                    Default is "yes".''')

        # mutually exclusive with --staticOnly
        group1.add_argument('-d', '--dynamicOnly', action='store_true',
                            help=clean_help('''Generate only dynamic XML for dyn-xml: don't create static XML.'''))

        parser.add_argument('-f', '--forceCreate', action='store_true',
                            help=clean_help('''Re-create the workspace, even if it already exists.'''))

        parser.add_argument('-g', '--group',
                            help=clean_help('The scenario group to process. Defaults to the group labeled default="1".'))

        parser.add_argument('-G', '--srcGroupDir',
                            help=clean_help('''A sub-directory under xmlsrc in which to find scenario dirs for this group.
                            Use this to consolidate static XML files shared by multiple scenario groups.
                            If --useGroupDir is specified, srcGroupDir defaults to the scenario group name.
                            Using --srcGroupDir implies --useGroupDir.'''))

        # mutually exclusive with --moduleSpec and --setupXml
        group2.add_argument('-m', '--modulePath',
                            help=clean_help('''The path to a scenario definition module. See -M/--moduleSpec
                            flag for more info.'''))

        # mutually exclusive with --modulePath and --setupXml
        group2.add_argument('-M', '--moduleSpec',
                            help=clean_help('''The "dot spec" for the Python module holding the setup classes and
                            a function called 'scenarioMapper' or a dictionary called 'ClassMap' which map
                            scenario names to classes. If the function 'scenarioMapper' exists, it is
                            used. If not, the 'ClassMap' is used. Default is "{xmlsrc}/subdir/scenarios.py" (if
                            subdir is defined) or "{xmlsrc}/scenarios.py" (if subdir is undefined) under the
                            current ProjectRoot.'''))

        parser.add_argument('-p', '--stopYear', type=int,
                            help=clean_help('The year after which to stop running GCAM'))

        parser.add_argument('--stopPeriod', type=int,
                            help=clean_help('DEPRECATED: please use --stopYear instead.'))

        # Deprecated -- set GCAM.RefWorkspace instead
        # parser.add_argument('-r', '--refWorkspace', default="",
        #                     help=clean_help('''A reference workspace to use instead of the value of
        #                             config variable "GCAM.RefWorkspace".'''))

        parser.add_argument('-R', '--resultsDir',
                            help=clean_help('The parent directory holding the GCAM output workspaces'))

        parser.add_argument('--runScenarioSetup', choices=yes_or_no, default='yes',
                            help='''Whether to run the commands in scenarios.xml for the current scenario.
                                    Default is "yes".''')

        parser.add_argument('-s', '--scenario', required=True,
                            help=clean_help('''Identify the scenario to run.
                            Note: at least one of --baseline (-b) / --scenario (-s) must be used.'''))

        # TBD: is this really used? Probably can be deprecated.
        # parser.add_argument('-S', '--subdir', default="",
        #                     help=clean_help('A sub-directory to use instead of scenario name'))

        # TBD: candidate for deletion. Just adds complexity and not really needed.
        # mutually exclusive with --moduleSpec and --modulePath
        group2.add_argument('--setupXml',
                            help=clean_help('''An XML scenario definition file. Defaults to the value of
                             config variable "GCAM.ScenariosFile".'''))

        # mutually exclusive with --dynamicOnly
        group1.add_argument('-T', '--staticOnly', action='store_true',
                            help=clean_help('''Generate only static XML for local-xml: don't create dynamic XML.'''))

        parser.add_argument('-u', '--useGroupDir', action='store_true',
                            help=clean_help('Use the group name as a sub directory below xmlsrc, local-xml, and dyn-xml'))

        # Deprecated
        # parser.add_argument('-x', '--xmlSourceDir',
        #                     help=clean_help('''The location of the xmlsrc directory.
        #                          Defaults to the value of config parameter "GCAM.ProjectXmlsrc".'''))

        # TBD: candidate for deletion
        parser.add_argument('-X', '--xmlOutputRoot',
                            help=clean_help('''The root directory into which to generate XML files.'''))

        parser.add_argument('-w', '--sandbox',  # -w for backwards compatibility
                            help=clean_help('''The pathname of the sandbox to operate on.'''))

        # Deprecated or pass to scenario?
        parser.add_argument('-y', '--years', default=defaultYears,
                            help=clean_help(f'''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "{defaultYears}"'''))

        return parser   # for auto-doc generation

    # TBD: this should take just a Sandbox or McsSandbox as argument
    #   Perhaps with dynamicOnly=False, staticOnly=False as kwds
    def run_scenario_setup(self, args, sbx):
        """
        Run the setup steps indicated in scenarios.xml.
        """
        from ..config import getParam, pathjoin

        scenario = sbx.scenario

        # TBD: read these from sbx
        projectDir = getParam('GCAM.ProjectDir')

        # TBD: get values from sbx rather than args
        groupName = args.group if args.useGroupDir else ''
        srcGroupDir = args.srcGroupDir or groupName

        if args.sandbox:
            workspace = args.sandbox
        else:
            workspace = pathjoin(projectDir, groupName, scenario, normpath=True)

        scenClass = sbx.editor_class(scenario, moduleSpec=args.moduleSpec, modulePath=args.modulePath)

        # TBD: take these from sbx
        subdir = args.subdir or scenario
        xmlOutputRoot = args.xmlOutputRoot or workspace

        mcsMode = getParam('MCS.Mode')

        # When called in 'trial' mode, we only run dynamic setup.
        # When run in 'gensim' mode, we do only static setup.
        args.dynamicOnly = args.dynamicOnly or mcsMode == McsMode.TRIAL

        if mcsMode == McsMode.GENSIM:
            args.dynamicOnly = False
            args.staticOnly = True

        # TBD: Document that all setup classes must conform to this protocol
        # TBD: scenClass(sbx) ??
        obj = scenClass(sbx.baseline, scenario, xmlOutputRoot, sbx.project_xml_src,
                        sbx.ref_workspace, groupName, srcGroupDir, subdir, mcsMode=mcsMode)

        obj.setup(args)

    def run(self, args, tool):
        from ..config import getParam
        from ..error import CommandlineError
        from ..mcs.mcsSandbox import sandbox_for_mode

        if args.baseline:
            raise CommandlineError("The -b/--baseline argument to 'setup' has been deprecated. Use -s/--scenario instead.")

        if args.stopPeriod is not None:
            raise CommandlineError("The --stopPeriod argument to 'setup' has been deprecated. Use --stopYear instead.")

        if args.createSandbox == 'no' and args.runScenarioSetup == 'no':
            raise CommandlineError("Specified both --createSandbox='no' and --runScenarioSetup='no' so there's nothing to do.")

        # scenario = args.scenario or args.baseline
        # if not scenario:
        #     raise CommandlineError('At least one of --baseline (-b) / --scenario (-s) must be used.')

        mcs_mode = getParam('MCS.Mode')
        sbx = sandbox_for_mode(mcs_mode, args.scenario, scenarioGroup=args.group, createDirs=True)

        if args.createSandbox == 'yes' and mcs_mode != McsMode.GENSIM: # mcs_mode is None or TRIAL
            sbx.create_sandbox(forceCreate=args.forceCreate)

        if args.runScenarioSetup == 'yes':
            self.run_scenario_setup(args, sbx)


