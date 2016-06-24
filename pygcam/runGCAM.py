'''
.. Created on: 2/26/15

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import sys
import subprocess
import platform
import shutil
from lxml import etree as ET
from .error import ProgramExecutionError, GcamRuntimeError
from .utils import mkdirs
from .config import getParam, getParamAsBoolean
from .log import getLogger
from .windows import setJavaPath, removeSymlink
from .subcommand import SubcommandABC

_logger = getLogger(__name__)

PROGRAM = os.path.basename(__file__)
__version__ = "0.2"

PlatformName = platform.system()

def readScenarioName(configFile):
    """
    Read the file `configFile` and extract the scenario name.

    :param configFile: (str) the path to a GCAM configuration file
    :return: (str) the name of the scenario defined in `configFile`
    """
    parser = ET.XMLParser(remove_blank_text=True)
    tree   = ET.parse(configFile, parser)
    scenarioName = tree.find('//Strings/Value[@name="scenarioName"]')
    return scenarioName.text

def setupWorkspace(runWorkspace):
    refWorkspace = getParam('GCAM.RefWorkspace')

    if os.path.lexists(runWorkspace) and os.path.samefile(runWorkspace, refWorkspace):
        _logger.info("setupWorkspace: run workspace is reference workspace; no setup performed")
        return

    copyAllFiles = getParamAsBoolean('GCAM.CopyAllFiles')

    def tryLink(src, dst):
        try:
            os.symlink(src, dst)
        except Exception:
            pass

    def workspaceSymlink(src, isDir=False):
        '''
        Create a link (or copy) in the new workspace to the
        equivalent file in the main GCAM workspace.
        '''
        dstPath = os.path.join(runWorkspace, src)
        dirName = dstPath if isDir else os.path.dirname(dstPath)
        mkdirs(dirName)

        if not os.path.lexists(dstPath):
            srcPath = os.path.join(refWorkspace, src)

            if copyAllFiles:
                # for Windows users without symlink permission
                _logger.warn('Copying %s to %s' % (srcPath, dstPath))
                if os.path.isdir(srcPath):
                    shutil.copytree(srcPath, dstPath)
                else:
                    shutil.copy2(srcPath, dstPath)
            else:
                os.symlink(srcPath, dstPath)

    # Create the workspace if needed
    if not os.path.isdir(runWorkspace):
        _logger.info("Creating GCAM workspace '%s'", runWorkspace)

    # Create a local output dir
    outDir = os.path.join(runWorkspace, 'output')
    mkdirs(outDir)

    logPath = os.path.join(runWorkspace, 'exe', 'logs')
    mkdirs(logPath)

    # Create link in the new workspace "exe" dir to the executable program and other required files/dirs
    exeName = getParam('GCAM.Executable')
    exeName = exeName[2:] if exeName[:2] == './' else exeName   # trim leading './' if present
    exePath = os.path.join('exe', exeName)                      # expressed as relative to the exe dir
    workspaceSymlink(exePath)

    # No need for this, and it's confusing...
    # workspaceSymlink(os.path.join('exe', 'configuration.xml'))  # link to default configuration file

    workspaceSymlink(os.path.join('exe', 'log_conf.xml'))       # and log configuration file
    workspaceSymlink('input')
    workspaceSymlink('libs')

    # Add links to libs for basex and xerces-c_3_1.dll (Windows)
    for filename in ['WriteLocalBaseXDB.class', 'xerces-c_3_1.dll']:
        if os.path.lexists(os.path.join(refWorkspace, 'exe', filename)):
            workspaceSymlink(os.path.join('exe', filename))

    # Add symlinks to dirs holding files generated by "setup" scripts
    def linkXmlDir(varName, xmlDir):
        src = getParam(varName)
        dst = os.path.abspath(os.path.join(runWorkspace, xmlDir))

        if os.path.lexists(dst):
            if os.path.islink(dst):
                removeSymlink(dst)
            else:
                shutil.rmtree(dst)

        if copyAllFiles:
            # for Windows users without symlink permission
            _logger.warn('Copying %s to %s' % (src, dst))
            shutil.copytree(src, dst)
        else:
            os.symlink(src, dst)

    linkXmlDir('GCAM.LocalXml', 'local-xml')
    linkXmlDir('GCAM.DynXml',   'dyn-xml')

def gcamWrapper(args):
    import subprocess as subp
    import re

    buffered = getParamAsBoolean('GCAM.BufferedWrapperOutput')
    buff = 'buffered' if buffered else 'unbuffered'
    _logger.debug('running gcamWrapper (%s)', buff)

    try:
        gcamProc = subp.Popen(args, bufsize=0, stdout=subp.PIPE, close_fds=True)

    except Exception as e:
        cmd = ' '.join(args)
        raise GcamRuntimeError('gcamWrapper failed to run command: %s (%s)' % (cmd, e))

    pattern = re.compile('(org.basex.core.BaseXException:.*|Model did not solve .*)')

    gcamOut = gcamProc.stdout
    while True:
        line = gcamOut.readline()
        if line == '':
            break

        sys.stdout.write(line)
        if not buffered:
            sys.stdout.flush()

        match = re.search(pattern, line)
        if match:
            gcamProc.terminate()
            reason = match.group(0)
            raise GcamRuntimeError('GCAM failed: ' + reason)

    status = gcamProc.poll()
    return status

CONFIG_FILE_DELIM = ':'

def runGCAM(args):
    scenarios = args.scenario.split(',') if args.scenario else None
    workspace = args.workspace  or getParam('GCAM.SandboxDir')
    workspace = os.path.abspath(os.path.expanduser(workspace))     # handle ~ in pathname

    if not os.path.lexists(workspace) or args.forceCreate:         # TBD: maybe rmtree first?
        setupWorkspace(workspace)

    exeDir = os.path.join(workspace, 'exe')
    setJavaPath(exeDir)     # required for Windows; a no-op otherwise

    if scenarios:
        # Translate scenario names into config file paths, assuming scenario FOO lives in
        # {scenariosDir}/FOO/config.xml
        scenariosDir = os.path.abspath(args.scenariosDir or getParam('GCAM.ScenariosDir') or '.')
        configFiles  = map(lambda name: os.path.join(scenariosDir, name, "config.xml"), scenarios)
    else:
        configFiles = map(os.path.abspath, args.configFile.split(',')) \
                        if args.configFile else [os.path.join(exeDir, 'configuration.xml')]

    _logger.info("cd %s", exeDir)
    os.chdir(exeDir)        # if isQsubbed, this is redundant but harmless

    gcamPath = os.path.abspath(getParam('GCAM.Executable'))

    for configFile in configFiles:
        gcamArgs = [gcamPath, '-C%s' % configFile]  # N.B. GCAM doesn't allow space between -C and filename

        command = ' '.join(gcamArgs)
        _logger.info('Running: %s', command)

        exitCode = subprocess.call(gcamArgs, shell=False) if args.noWrapper else gcamWrapper(gcamArgs)
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
                            help='''Specify the scenario(s) to run. Can be a comma-delimited list of scenario
                            names. The scenarios will be run serially in a single batch job, with an allocated
                            time = GCAM.Minutes * {the number of scenarios}.''')

        parser.add_argument('-S', '--scenariosDir', default='',
                            help='''Specify the directory holding scenarios. Default is the value of config file
                            param GCAM.ScenariosDir, if set, otherwise it's the current directory.''')

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
