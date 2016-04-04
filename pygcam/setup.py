'''
.. gcamtool.py plugin for setting up / customizing GCAM project's XML files.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''

import sys
import os
from importlib import import_module
from .error import SetupException
from .config import getParam
from .utils import importFrom
from .subcommand import SubcommandABC

# def (ns, argName, default=None, raiseError=False):
#     """
#     Return the value of parameter `argName` from the Namespace `ns`.
#     If not found, raise a SetupException if `raiseError` is True,
#     otherwise return the given `default`.
#     :param ns: (argparse.Namespace) a namespace containing arguments to
#       a call to the gcamtools.py setup sub-command
#     :param argName: (str) the name of an argument
#     :param default: the default value to return if the argument is missing.
#     :param raiseError: (bool) whether to raise an error if the argument is missing.
#     :return: the value of the parameter argName in the Namespace
#     :raises: SetupError
#     """
#     if ns in argName:
#         return ns[argName]
#
#     if raiseError:
#         raise SetupException('Required argument "%s" is missing for setup step', argName)
#
#     return default


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
                            a function called 'scenarioClass' or a dictionary called 'ClassMap' which map
                            scenario names to classes. If the function 'scenarioClass' exists, it is
                            used. If not, the 'ClassMap' is used.
                            Default is "xmlsrc.scenarios" under the current Project Root.''')

        parser.add_argument('-p', '--stopPeriod', type=int,
                            help='The number of the GCAM period or the year to terminate after')

        parser.add_argument('-R', '--resultsDir',
                            help='The parent directory holding the GCAM output workspaces')

        parser.add_argument('-s', '--scenario',
                            help='Identify the scenario to run.')

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
        scenario = args.scenario or args.baseline

        # TBD: remove ability to override on cmdline if not useful
        args.workspace     = args.workspace     or getParam('GCAM.RefWorkspace')
        args.xmlOutputRoot = args.xmlOutputRoot or getParam('GCAM.ProjectRoot')
        args.xmlSourceDir  = args.xmlSourceDir  or os.path.join(getParam('GCAM.XmlSrc'), scenario)

        sys.path.insert(0, os.path.dirname(os.path.dirname(args.xmlSourceDir)))

        try:
            # Try to load the user's module
            module = import_module(args.module, package=None)

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

        except Exception as e:
            raise SetupException('Failed to load scenarioMapper or ClassMap from module %s: %s' % (args.module, e))

        # TBD: Ensure that all setup classes conform to this protocol
        obj = scenClass(args.baseline, args.scenario, args.xmlOutputRoot,
                        args.xmlSourceDir, args.workspace, args.subdir)

        obj.setup(args)
