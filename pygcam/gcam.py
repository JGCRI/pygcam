'''
.. Created on: 2/26/15

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
import os
import re
import subprocess
from semver import VersionInfo

from .config import getParam, getParamAsBoolean, parse_version_info, pathjoin, unixPath
from .error import ProgramExecutionError, GcamError, GcamSolverError, PygcamException, ConfigFileError
from .log import getLogger
from .scenarioSetup import createSandbox
from .utils import writeXmldbDriverProperties, getExeDir, pushd
from .windows import IsWindows

_logger = getLogger(__name__)

PROGRAM = os.path.basename(__file__)

_VersionPattern = re.compile('.*-v(\d+(\.\d+)*)$')

def getGcamVersion(exeDir):
    '''
    Try to get GCAM version by running gcam with --versionID flag, but if that
    fails, try to extract it from the path.
    '''
    exeName = getParam('GCAM.Executable')
    exePath = pathjoin(exeDir, exeName)

    if not os.path.lexists(exePath):
        gcamDir = os.path.dirname(exeDir)
        _logger.info("GCAM not found at %s; extracting version from path", gcamDir)
        m = re.match(_VersionPattern, gcamDir)
        if m:
            return m.group(1)
        else:
            raise PygcamException('Failed to extract version number from path {}'.format(gcamDir))

    setJavaPath(exeDir)
    with pushd(exeDir):
        try:
            cmd = [exePath, '--versionID']
            versionStr = subprocess.check_output(cmd, shell=False).strip().decode('utf-8')

        except subprocess.CalledProcessError:
            raise ConfigFileError(
                "Attempt to run '%s --versionID' failed. If you're running GCAM < v4.3, set GCAM.VersionNumber manually" % exePath)

    prefix = 'gcam-v'
    if not versionStr.startswith(prefix):
        raise ConfigFileError('GCAM --versionID "%s" is not the correct format. Should start with "gcam-v"',
                              versionStr)

    versionNum = versionStr[len(prefix):]
    return versionNum

def setJavaPath(exeDir):
    '''
    Update the PATH to be able to find the Java dlls.
    Modeled on run-gcam.bat in the GCAM distribution.
    '''
    if not IsWindows:
        return

    javaHome = getParam('GCAM.JavaHome') or os.environ.get('JAVA_HOME', None)

    if not javaHome:
        # Use WriteLocalBaseXDB (4.2) or XMLDBDriver (>= 4.3) to print the java.home property
        # of the Java Runtime used to run it. Note if the runtime is not 64-bit it will only
        # print an error.
        with pushd(exeDir):
            versionInfo = parse_version_info()
            if versionInfo > VersionInfo(4, 2, 0):
                classpath = getParam('GCAM.MI.ClassPath')
                command = 'java -cp "%s" XMLDBDriver --print-java-home' % classpath
                msg_cmd = 'XMLDBDriver --print-java-home'
            else:
                command = 'java WriteLocalBaseXDB'
                msg_cmd = command

            try:
                output = subprocess.check_output(str(command), shell=True)
                javaHome = output.decode('utf-8').strip()
            except Exception as e:
                raise PygcamException("Cannot get java home dir: %s" % e)

        os.environ['JAVA_HOME'] = javaHome

        if not javaHome:
            raise PygcamException("JAVA_HOME not set and failed to read java home directory from '%s'" % msg_cmd)

    if not os.path.isdir(javaHome):
        raise PygcamException('Java home (%s) is not a directory' % javaHome)

    # Update the PATH to be able to find the Java dlls
    # SET PATH=%PATH%;%JAVA_HOME%\bin;%JAVA_HOME%\bin\server"
    javaBin = pathjoin(javaHome, 'bin')
    javaBinServer = pathjoin(javaBin, 'server')
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
        msg = 'gcamWrapper failed to run command: {} ({})'.format(' '.join(args), e)
        raise PygcamException(msg)

    modelDidNotSolve = 'Model did not solve'
    pattern = re.compile('(.*(BaseXException|%s).*)' % modelDidNotSolve)

    gcamOut = gcamProc.stdout
    while True:
        line = gcamOut.readline().decode('utf-8')
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

#
# Comment taken from exe/run-gcam.command:
#
# We need to find where the Java development kit is installed.
# This could be the Apple supplied version which was provided up
# to 1.6 however was dropped subsequently and instead users may
# have an Oracle provided JDK.  The each take slightly different
# approaches to where libraries live and how to reference them so
# we will have to try to detect the appropriate location.
#
def linkToMacJava():
    import subprocess as subp
    from .error import PygcamException

    cmd = '/usr/libexec/java_home'
    javaHome = ''
    try:
        javaHome = subp.check_output(cmd).strip().decode('utf-8')
    except Exception:
        pass

    if not javaHome:
        raise PygcamException('Could not find Java install location using "%s"' % cmd)

    # If javaHome contains "1.6", use the Apple supplied version of java 1.6
    libPath = 'lib-stub' if '1.6' in javaHome else javaHome + '/jre/lib/server'

    owd = os.getcwd()
    refWorkspace = getParam('GCAM.RefWorkspace')
    os.chdir(refWorkspace)

    try:
        # Create a symlink to satisfy @rpath searches
        linkName = 'libs/java/lib'
        if not os.path.islink(linkName):
            cmd = "ln -s %s %s" % (libPath, linkName)
            status = subp.call(cmd, shell=True)
            if status != 0:
                raise PygcamException('Failed to create link using "%s"' % cmd)
    finally:
        os.chdir(owd)

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
    import platform

    if platform.system() == 'Darwin':
        linkToMacJava()

    workspace = workspace or (pathjoin(getParam('GCAM.SandboxDir'), scenario)
                                  if scenario else getParam('GCAM.RefWorkspace'))

    if not os.path.lexists(workspace) or forceCreate:
        createSandbox(workspace, srcWorkspace=refWorkspace, forceCreate=forceCreate)

    exeDir = getExeDir(workspace, chdir=True)
    setJavaPath(exeDir)     # required for Windows; a no-op otherwise

    version = parse_version_info()

    # These features didn't exist in version 4.2
    if version > VersionInfo(4, 2, 0) and not (getParamAsBoolean('GCAM.RunQueriesInGCAM') or
                                               getParamAsBoolean('GCAM.InMemoryDatabase')):    # this implies RunQueriesInGCAM
        # Write a "no-op" XMLDBDriver.properties file
        writeXmldbDriverProperties(inMemory=False, outputDir=exeDir)

    if scenario:
        # Translate scenario name into config file path, assuming that for scenario
        # FOO, the configuration file is {scenariosDir}/{groupDir}/FOO/config.xml
        scenariosDir = unixPath(scenariosDir or getParam('GCAM.ScenariosDir') or '.', abspath=True)
        configFile   = pathjoin(scenariosDir, groupDir, scenario, "config.xml")
    else:
        configFile = unixPath(configFile or pathjoin(exeDir, 'configuration.xml'), abspath=True)

    gcamPath = unixPath(getParam('GCAM.Executable'), abspath=True)
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
