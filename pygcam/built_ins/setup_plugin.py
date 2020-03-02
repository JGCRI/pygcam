'''
.. gcamtool plugin for setting up / customizing GCAM project's XML files.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from ..subcommand import SubcommandABC, clean_help

class SetupCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help': '''Setup a scenario by creating modified XML input files.'''}

        super(SetupCommand, self).__init__('setup', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        defaultYears = '2015-2100'

        group1 = parser.add_mutually_exclusive_group()  # --dynamicOnly, --staticOnly
        group2 = parser.add_mutually_exclusive_group()  # --modulePath, --moduleSpec, --setupXml

        parser.add_argument('-b', '--baseline',
                            help=clean_help('''Identify the baseline the selected scenario is based on.
                                 Note: at least one of --baseline (-b) / --scenario (-s) must be used.'''))

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
                            help=clean_help('''The path to a scenario definition module. See -M flag for more info.'''))

        # mutually exclusive with --modulePath and --setupXml
        group2.add_argument('-M', '--moduleSpec',
                            help=clean_help('''The "dot spec" for the Python module holding the setup classes and
                            a function called 'scenarioMapper' or a dictionary called 'ClassMap' which map
                            scenario names to classes. If the function 'scenarioMapper' exists, it is
                            used. If not, the 'ClassMap' is used. Default is "{xmlsrc}/subdir/scenarios.py" (if
                            subdir is defined) or "{xmlsrc}/scenarios.py" (if subdir is undefined) under the
                            current ProjectRoot.'''))

        parser.add_argument('-p', '--stop', type=int, metavar='period-or-year', dest='stopPeriod',
                            help=clean_help('The number of the GCAM period or the year to stop after'))

        parser.add_argument('-r', '--refWorkspace', default="",
                            help=clean_help('''A reference workspace to use instead of the value of GCAM.RefWorkspace'''))

        parser.add_argument('-R', '--resultsDir',
                            help=clean_help('The parent directory holding the GCAM output workspaces'))

        parser.add_argument('-s', '--scenario',
                            help=clean_help('''Identify the scenario to run.
                            Note: at least one of --baseline (-b) / --scenario (-s) must be used.'''))

        parser.add_argument('-S', '--subdir', default="",
                            help=clean_help('A sub-directory to use instead of scenario name'))

        # mutually exclusive with --moduleSpec and --modulePath
        group2.add_argument('--setupXml',
                            help=clean_help('''An XML scenario definition file. Overrides configuration variable
                             GCAM.ScenarioSetupFile.'''))

        # mutually exclusive with --dynamicOnly
        group1.add_argument('-T', '--staticOnly', action='store_true',
                            help=clean_help('''Generate only static XML for local-xml: don't create dynamic XML.'''))

        parser.add_argument('-u', '--useGroupDir', action='store_true',
                            help=clean_help('Use the group name as a sub directory below xmlsrc, local-xml, and dyn-xml'))

        parser.add_argument('-x', '--xmlSourceDir',
                            help=clean_help('''The location of the xmlsrc directory.'''))

        parser.add_argument('-X', '--xmlOutputRoot',
                            help=clean_help('''The root directory into which to generate XML files.'''))

        parser.add_argument('-w', '--workspace', # i.e., sandbox
                            help=clean_help('''The pathname of the workspace to operate on.'''))

        # Deprecated or pass to scenario?
        parser.add_argument('-y', '--years', default=defaultYears,
                            help=clean_help('''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "%s"''' % defaultYears))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from importlib import import_module

        from ..config import getParam, pathjoin
        from ..error import SetupException
        from ..log import getLogger
        from ..scenarioSetup import createSandbox
        from ..utils import loadModuleFromPath

        _logger = getLogger(__name__)

        scenario = args.scenario or args.baseline
        if not scenario:
            raise SetupException('At least one of --baseline (-b) / --scenario (-s) must be used.')

        projectDir = getParam('GCAM.ProjectDir')
        groupName = args.group if args.useGroupDir else ''
        srcGroupDir = args.srcGroupDir or groupName

        if args.workspace:
            workspace = args.workspace
        else:
            workspace = pathjoin(projectDir, groupName, scenario, normpath=True)

        mcsMode = tool.getMcsMode()
        forceCreate = args.forceCreate or bool(mcsMode)

        if not mcsMode or mcsMode == 'trial':
            createSandbox(workspace, srcWorkspace=args.refWorkspace, forceCreate=forceCreate, mcsMode=mcsMode)

        xmlSourceDir = args.xmlSourceDir or getParam('GCAM.XmlSrc')

        # If a setup XML file is defined, use the defined (or default) XMLEditor subclass
        setupXml = args.setupXml or getParam('GCAM.ScenarioSetupFile')
        if setupXml:
            from ..xmlSetup import createXmlEditorSubclass
            _logger.debug('Setup using %s, mcsMode=%s', setupXml, mcsMode)
            scenClass = createXmlEditorSubclass(setupXml, mcsMode=mcsMode)

        else:
            # If neither is defined, we assume a custom scenarios.py file is used
            try:
                if args.moduleSpec:
                    module = import_module(args.moduleSpec, package=None)
                else:
                    modulePath = args.modulePath or pathjoin(xmlSourceDir, srcGroupDir, 'scenarios.py')
                    _logger.debug('Setup using %s', modulePath)
                    module = loadModuleFromPath(modulePath)

            except Exception as e:
                moduleName = args.moduleSpec or modulePath
                raise SetupException('Failed to load scenarioMapper or ClassMap from module %s: %s' % (moduleName, e))

            try:
                # First look for a function called scenarioMapper
                scenarioMapper = getattr(module, 'scenarioMapper', None)
                if scenarioMapper:
                    scenClass = scenarioMapper(scenario)

                else:
                    # Look for 'ClassMap' in the specified module
                    classMap  = getattr(module, 'ClassMap')
                    scenClass = classMap[scenario]

            except KeyError:
                raise SetupException('Failed to map scenario "%s" to a class in %s' % (scenario, module.__file__))

        subdir = args.subdir or scenario
        refWorkspace  = args.refWorkspace or getParam('GCAM.RefWorkspace')
        xmlOutputRoot = args.xmlOutputRoot or workspace

        # When called from gcammcs in 'trial' mode, we only run dynamic setup. When run
        # in 'gensim' mode, we do only static setup.
        args.dynamicOnly = args.dynamicOnly or mcsMode == 'trial'

        if mcsMode == 'gensim':
            args.dynamicOnly = False
            args.staticOnly  = True

        # TBD: Document that all setup classes must conform to this protocol
        obj = scenClass(args.baseline, args.scenario, xmlOutputRoot, xmlSourceDir,
                        refWorkspace, groupName, srcGroupDir, subdir, mcsMode=mcsMode)

        obj.mcsMode = mcsMode
        obj.setup(args)
