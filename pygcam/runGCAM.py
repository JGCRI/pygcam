'''
.. Created on: 2/26/15

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import platform
import subprocess
import sys

from .config import getParam, getParamAsBoolean
from .error import ProgramExecutionError, GcamRuntimeError
from .log import getLogger
from .subcommand import SubcommandABC
from .utils import writeXmldbDriverProperties, getExeDir
from .windows import setJavaPath, IsWindows

_logger = getLogger(__name__)

PROGRAM = os.path.basename(__file__)
__version__ = "0.2"

PlatformName = platform.system()

CONFIG_FILE_DELIM = ':'

def gcamWrapper(args):
    import subprocess as subp
    import re

    buffered = getParamAsBoolean('GCAM.BufferedWrapperOutput')
    buff = 'buffered' if buffered else 'unbuffered'
    _logger.debug('running gcamWrapper (%s)', buff)

    try:
        gcamProc = subp.Popen(args, bufsize=0, stdout=subp.PIPE, stderr=subp.STDOUT, close_fds=True)

    except Exception as e:
        cmd = ' '.join(args)
        raise GcamRuntimeError('gcamWrapper failed to run command: %s (%s)' % (cmd, e))

    pattern = re.compile('(.*(BaseXException|Model did not solve).*)')

    gcamOut = gcamProc.stdout
    while True:
        line = gcamOut.readline()
        if line == '':
            break

        sys.stdout.write(line)
        if not buffered:            # unbuffered is useful for debugging; otherwise, use buffering
            sys.stdout.flush()

        match = re.search(pattern, line)
        if match:
            gcamProc.terminate()
            reason = match.group(0)
            raise GcamRuntimeError('GCAM reported error: ' + reason)

    _logger.debug('gcamWrapper found EOF. Waiting for GCAM to exit...')
    status = gcamProc.wait()
    _logger.debug('gcamWrapper: GCAM exited with status %s', status)
    return status


def runGCAM(args):
    scenario  = args.scenario
    workspace = args.workspace or os.path.join(getParam('GCAM.SandboxDir'), scenario)

    # Setup now occurs in setup.py
    # setupWorkspace(workspace, forceCreate=args.forceCreate)

    exeDir = getExeDir(workspace, chdir=True)
    setJavaPath(exeDir)     # required for Windows; a no-op otherwise

    if not (getParamAsBoolean('GCAM.RunQueriesInGCAM') or
            getParamAsBoolean('GCAM.InMemoryDatabase')):    # this implies RunQueriesInGCAM
        # Write a "no-op" XMLDBDriver.properties file
        writeXmldbDriverProperties(inMemory=False, outputDir=exeDir)

    if scenario:
        # Translate scenario name into config file path, assuming scenario FOO
        # lives in {scenariosDir}/FOO/config.xml
        scenariosDir = os.path.abspath(args.scenariosDir or getParam('GCAM.ScenariosDir') or '.')
        configFile   = os.path.join(scenariosDir, scenario, "config.xml")
    else:
        configFile = os.path.abspath(args.configFile or os.path.join(exeDir, 'configuration.xml'))

    gcamPath = os.path.abspath(getParam('GCAM.Executable'))
    gcamArgs = [gcamPath, '-C%s' % configFile]  # N.B. GCAM doesn't allow space between -C and filename

    command = ' '.join(gcamArgs)
    _logger.info('Running: %s', command)

    noWrapper = IsWindows or args.noWrapper     # never use the wrapper on Windows
    exitCode = subprocess.call(gcamArgs, shell=False) if noWrapper else gcamWrapper(gcamArgs)

    if exitCode != 0:
        raise ProgramExecutionError(command, exitCode)


class GcamCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Run GCAM for the indicated configFile, scenario, or workspace.'''}
        super(GcamCommand, self).__init__('gcam', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('-C', '--configFile',
                            help='''Specify the one or more GCAM configuration filenames, separated by commas.
                            If multiple configuration files are given, the are run in succession in the
                            same "job" on the cluster.''')

        parser.add_argument('-f', '--forceCreate', action='store_true',
                            help='''Re-create the workspace, even if it already exists.''')

        parser.add_argument('-s', '--scenario', default='',
                            help='''The scenario to run.''')

        parser.add_argument('-S', '--scenariosDir', default='',
                            help='''Specify the directory holding scenarios. Default is the value of config
                            file param GCAM.ScenariosDir, if set, otherwise it's the current directory.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

        parser.add_argument('-w', '--workspace',
                            help='''Specify the path to the GCAM workspace to use. If it doesn't exist, the named
                            workspace will be created. If not specified on the command-line, the value of config
                            file parameter GCAM.Workspace is used, i.e., the "standard" workspace.''')

        parser.add_argument('-W', '--noWrapper', action='store_true',
                            help='''Do not run gcam within a wrapper that detects errors as early as possible
                            and terminates the model run. By default, the wrapper is used.''')
        return parser

    def run(self, args, tool):
        runGCAM(args)
