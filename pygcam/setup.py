'''
.. gcamtool.py plugin for setting up / customizing GCAM project's XML files.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''

import sys
import os
from .error import SetupException
from .config import getParam
from .utils import importFrom
from .subcommand import SubcommandABC


class SetupCommand(SubcommandABC):
    __version__ = '0.1'

    def __init__(self, subparsers):
        kwargs = {'help': '''Setup a scenario by creating modified XML input files.''',
                  'description': '''Automates modification to copies of GCAM's input XML files,
                   and construction of a corresponding configuration XML file.'''}

        super(SetupCommand, self).__init__('setup', subparsers, kwargs)

    def addArgs(self, parser):
        defaultYears = '2015-2100'

        parser.add_argument('-b', '--baseline',
                            help='Identify the baseline the selected scenario is based on.')

        parser.add_argument('-g', '--group',
                            help='The scenario group to process. Defaults to the group labeled default="1".')

        parser.add_argument('-G', '--noGenerate', action='store_true',
                            help='Do not generate constraints (useful before copying files for Monte Carlo simulation).')

        parser.add_argument('-m', '--module', default='xmlsrc.scenarios',
                            help='''The "dot spec" for the Python module holding the setup classes and
                            a dictionary called 'ClassMap' which maps scenario names to classes.
                            Default is "xmlsrc.scenarios" under the current Project Root.''')

        parser.add_argument('-p', '--stopPeriod', type=int,
                            help='The number of the GCAM period or the year to terminate after')

        parser.add_argument('-R', '--resultsDir',
                            help='The parent directory holding the GCAM output workspaces')

        parser.add_argument('-s', '--scenario',
                            help='Identify the scenario to run (N.B. The name is hardwired in some scripts).')

        parser.add_argument('-S', '--subdir', default="",
                            help='A sub-directory to use beneath the computed scenario directory')

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
        # TBD: remove ability to override on cmdline if not useful
        args.workspace  = args.workspace     or getParam('GCAM.RefWorkspace')
        args.xmlOutputRoot = args.xmlOutputRoot or getParam('GCAM.ProjectRoot')
        args.xmlSourceDir  = args.xmlSourceDir  or os.path.join(getParam('GCAM.XmlSrc'), args.scenario)
        #resultsDir    = args.resultsDir    or getParam('GCAM.RunWorkspaceRoot')

        sys.path.insert(0, os.path.dirname(os.path.dirname(args.xmlSourceDir)))

        try:
            # Look for 'ClassMap' in the specified module
            classMap  = importFrom(args.module, 'ClassMap')
            scenClass = classMap[args.scenario]

        except KeyError as e:
            raise SetupException('Failed to map scenario "%s" to a class in %s: %s' % (args.scenario, args.module, e))

        except Exception as e:
            raise SetupException('Failed to load %s.ClassMap: %s' % (args.module, e))

        # TBD: Ensure that all setup classes conform to this protocol
        obj = scenClass(args.baseline, args.scenario, args.xmlOutputRoot,
                        args.xmlSourceDir, args.workspace, args.subdir)

        obj.setup(args)
