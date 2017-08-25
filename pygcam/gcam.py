'''
.. Created on: 2/26/15

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
import os
import re
import subprocess

from .config import getParam, getParamAsBoolean, getParamAsFloat
from .error import ProgramExecutionError, GcamError, GcamSolverError, PygcamException
from .log import getLogger
from .scenarioSetup import createSandbox
from .utils import writeXmldbDriverProperties, getExeDir, pushd
from .windows import IsWindows

_logger = getLogger(__name__)

PROGRAM = os.path.basename(__file__)

def setJavaPath(exeDir):
    '''
    Update the PATH to be able to find the Java dlls.
    Modeled on run-gcam.bat in the GCAM distribution.
    '''
    if not IsWindows:
        return

    javaHome = os.environ.get('JAVA_HOME', None)

    if not javaHome:
        # Use WriteLocalBaseXDB (v4.2) or XMLDBDriver (v4.3) to print the java.home property
        # of the Java Runtime used to run it. Note if the runtime is not 64-bit it will only
        # print an error.
        with pushd(exeDir):
            if getParamAsFloat('GCAM.VersionNumber') > 4.2:
                classpath = getParam('GCAM.MI.ClassPath')
                command = 'java -cp "%s" XMLDBDriver --print-java-home' % classpath
            else:
                command = 'java WriteLocalBaseXDB'

            try:
                output = subprocess.check_output(str(command), shell=True)
            except Exception as e:
                raise PygcamException("Cannot get java home dir: %s" % e)

        os.environ['JAVA_HOME'] = javaHome = output and output.strip()

        if not javaHome:
            raise PygcamException("JAVA_HOME not set and failed to read java home directory from WriteLocalBaseXDB")

    if not os.path.isdir(javaHome):
        raise PygcamException('Java home (%s) is not a directory' % javaHome)

    # Update the PATH to be able to find the Java dlls
    # SET PATH=%PATH%;%JAVA_HOME%\bin;%JAVA_HOME%\bin\server"
    javaBin = os.path.join(javaHome, 'bin')
    javaBinServer = os.path.join(javaBin, 'server')
    envPath = os.environ.get('PATH', '')
    os.environ['PATH'] = path = envPath + ';' + javaBin + ';' + javaBinServer
    _logger.debug('PATH=%s', path)

    envClasspath = os.environ.get('CLASSPATH', '')
    envClasspath = ".;" + envClasspath if envClasspath else "."

    miClasspath = getParam('GCAM.MI.ClassPath')
    os.environ['CLASSPATH'] = classpath = envClasspath + ';' + javaBinServer + ';' + miClasspath
    _logger.debug('CLASSPATH=%s', classpath)

def _gcamWrapper(args):
    try:
        _logger.debug('Starting gcam with wrapper')
        gcamProc = subprocess.Popen(args, bufsize=0, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, close_fds=True)

    except Exception as e:
        cmd = ' '.join(args)
        raise ProgramExecutionError('gcamWrapper failed to run command: %s (%s)' % (cmd, e))

    modelDidNotSolve = 'Model did not solve'
    pattern = re.compile('(.*(BaseXException|%s).*)' % modelDidNotSolve)

    gcamOut = gcamProc.stdout
    while True:
        line = gcamOut.readline()
        if line == '':
            break

        _logger.info(line.rstrip())          # see if this ends up in worker.log

        match = re.search(pattern, line)
        if match:
            gcamProc.terminate()
            msg = 'GCAM error: ' + match.group(0)
            if match.group(1) == modelDidNotSolve:
                raise GcamSolverError(msg)
            else:
                raise GcamError(msg)

    _logger.debug('gcamWrapper found EOF. Waiting for GCAM to exit...')
    status = gcamProc.wait()
    _logger.debug('gcamWrapper: GCAM exited with status %s', status)
    return status


def runGCAM(scenario, workspace=None, refWorkspace=None, scenariosDir=None, groupDir='',
            configFile=None, forceCreate=False, noRun=False, noWrapper=False):
    """

    :param scenario: (str) the scenario to run
    :param workspace: (str) path to the workspace to run in, or None, in which
       case the model is run in {GCAM.SandboxDir}/{scenario} if scenario is given
       otherwise, the default scenario in the configuration.xml in the GCAM.RefWorkspace
       is run.
    :param refWorkspace: (str) a workspace to copy files from to create the sandbox,
       if the workspace is not given, or doesn't exist.
    :param scenariosDir: (str) the directory in which the config.xml file for the
       given scenario is found. Defaults to GCAM.ScenariosDir, if given, or "."
    :param groupDir: (str) the name of the scenario group if group sub-directories
       are to be used when computing the location of the scenario's config.xml.
    :param configFile: (str) if scenario is not given, the name of a configuration
       file to run. If scenario is given, this parameter is ignored.
    :param forceCreate: (bool) if True, recreate the sandbox even if it already exists.
    :param noRun: (bool) if True, don't run the model, just create the sandbox and
       display the command that would be executed.
    :param noWrapper: (bool) if True, don't run GCAM inside a "wrapper" that reads
        output and kills the model run as soon as an error is detected.
    :return: none
    :raises ProgramExecutionError: if GCAM exits with non-zero status
    """
    workspace = workspace or (os.path.join(getParam('GCAM.SandboxDir'), scenario)
                                       if scenario else getParam('GCAM.RefWorkspace'))

    if not os.path.lexists(workspace) or forceCreate:
        createSandbox(workspace, srcWorkspace=refWorkspace, forceCreate=forceCreate)

    exeDir = getExeDir(workspace, chdir=True)
    setJavaPath(exeDir)     # required for Windows; a no-op otherwise
    version = getParamAsFloat('GCAM.VersionNumber')

    # These features didn't exist in version 4.2
    if version > 4.2 and not (getParamAsBoolean('GCAM.RunQueriesInGCAM') or
                              getParamAsBoolean('GCAM.InMemoryDatabase')):    # this implies RunQueriesInGCAM
        # Write a "no-op" XMLDBDriver.properties file
        writeXmldbDriverProperties(inMemory=False, outputDir=exeDir)

    if scenario:
        # Translate scenario name into config file path, assuming that for scenario
        # FOO, the configuration file is {scenariosDir}/{groupDir}/FOO/config.xml
        scenariosDir = os.path.abspath(scenariosDir or getParam('GCAM.ScenariosDir') or '.')
        configFile   = os.path.join(scenariosDir, groupDir, scenario, "config.xml")
    else:
        configFile = os.path.abspath(configFile or os.path.join(exeDir, 'configuration.xml'))

    gcamPath = os.path.abspath(getParam('GCAM.Executable'))
    gcamArgs = [gcamPath, '-C%s' % configFile]  # N.B. GCAM (< 4.2) doesn't allow space between -C and filename

    command = ' '.join(gcamArgs)
    if noRun:
        print(command)
    else:
        _logger.info('Running: %s', command)

        noWrapper = IsWindows or noWrapper     # never use the wrapper on Windows
        exitCode = subprocess.call(gcamArgs, shell=False) if noWrapper else _gcamWrapper(gcamArgs)

        if exitCode != 0:
            raise ProgramExecutionError(command, exitCode)


def gcamMain(args):
    runGCAM(args.scenario, workspace=args.workspace, refWorkspace=args.refWorkspace,
            scenariosDir=args.scenariosDir, groupDir=args.groupDir, configFile=args.configFile,
            forceCreate=args.forceCreate, noRun=args.noRun, noWrapper=args.noWrapper)
