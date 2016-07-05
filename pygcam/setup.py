'''
.. gcamtool plugin for setting up / customizing GCAM project's XML files.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''

import sys
import os
from importlib import import_module
from .error import SetupException
from .config import getParam
from .log import getLogger
from .subcommand import SubcommandABC
from .utils import loadModuleFromPath

_logger = getLogger(__name__)

class SetupCommand(SubcommandABC):
    __version__ = '0.1'

    def __init__(self, subparsers):
        kwargs = {'help': '''Setup a scenario by creating modified XML input files.'''}

        super(SetupCommand, self).__init__('setup', subparsers, kwargs)

    def addArgs(self, parser):
        defaultYears = '2015-2100'

        parser.add_argument('-b', '--baseline',
                            help='''Identify the baseline the selected scenario is based on.
                                 Note: at least one of --baseline (-b) / --scenario (-s) must be used.''')

        parser.add_argument('-g', '--group',
                            help='The scenario group to process. Defaults to the group labeled default="1".')

        parser.add_argument('-G', '--noGenerate', action='store_true',
                            help='Do not generate constraints (useful before copying files for Monte Carlo simulation).')

        parser.add_argument('-m', '--module',
                            help='''The "dot spec" for the Python module holding the setup classes and
                            a function called 'scenarioClass' or a dictionary called 'ClassMap' which map
                            scenario names to classes. If the function 'scenarioClass' exists, it is
                            used. If not, the 'ClassMap' is used. Default is "{xmlsrc}/subdir/scenarios.py" (if
                            subdir is defined) or "{xmlsrc}/scenarios.py" (if subdir is undefined) under the
                            current ProjectRoot.''')

        parser.add_argument('-p', '--stop', type=int, metavar='period-or-year', dest='stopPeriod',
                            help='The number of the GCAM period or the year to stop after')

        parser.add_argument('-R', '--resultsDir',
                            help='The parent directory holding the GCAM output workspaces')

        parser.add_argument('-s', '--scenario',
                            help='''Identify the scenario to run.
                            Note: at least one of --baseline (-b) / --scenario (-s) must be used.''')

        parser.add_argument('-S', '--subdir', default="",
                            help='A sub-directory to use instead of scenario name')

        parser.add_argument('-u', '--useGroupDir', action='store_true',
                            help='Use the group name as a subdir below xmlsrc, local-xml, and dyn-xml')

        parser.add_argument('-x', '--xmlSourceDir',
                            help='''The location of the xmlsrc directory.''')

        parser.add_argument('-X', '--xmlOutputRoot',
                            help='''The root directory into which to generate XML files.''')

        parser.add_argument('-w', '--workspace',
                            help='''The pathname of the workspace to operate on.''')

        parser.add_argument('-y', '--years', default=defaultYears,
                            help='''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "%s"''' % defaultYears)

        return parser   # for auto-doc generation


    def run(self, args, tool):
        scenario = args.scenario or args.baseline

        if not scenario:
            raise SetupException('At least one of --baseline (-b) / --scenario (-s) must be used.')

        # TBD: remove ability to override on cmdline if not useful
        args.workspace     = args.workspace     or getParam('GCAM.RefWorkspace')
        args.xmlOutputRoot = args.xmlOutputRoot or getParam('GCAM.ProjectDir')
        groupDir = args.group if args.useGroupDir else ''
        subdir = args.subdir or scenario
        args.xmlSourceDir  = args.xmlSourceDir or getParam('GCAM.XmlSrc')

        # TBD: document this
        try:
            if args.module:
                module = import_module(args.module, package=None)
            else:
                modulePath = os.path.join(args.xmlSourceDir, groupDir, 'scenarios.py')
                module = loadModuleFromPath(modulePath)

        except Exception as e:
            raise SetupException('Failed to load scenarioMapper or ClassMap from module %s: %s' % (args.module, e))

        _logger.debug('Loaded module %s', module)

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

        # TBD: Ensure that all setup classes conform to this protocol
        obj = scenClass(args.baseline, args.scenario, args.xmlOutputRoot,
                        args.xmlSourceDir, args.workspace, groupDir)

        obj.setup(args)
