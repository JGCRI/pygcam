'''
.. Created on: 2/26/15

.. Copyright (c) 2016-2023 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import re
import subprocess

from .config import getParam, getParamAsBoolean, pathjoin
from .error import ProgramExecutionError, GcamError, GcamSolverError, PygcamException, ConfigFileError
from .file_mapper import FileMapper
from .file_utils import pushd
from .log import getLogger
from .utils import writeXmldbDriverProperties
from .windows import IsWindows

_logger = getLogger(__name__)

PROGRAM = os.path.basename(__file__)

_PathVersionPattern = re.compile('.*-v(\d+(\.\d+)*)$')
_VersionFlagPattern = re.compile('GCAM version (\d+(\.\d+)+)')

# TBD: update this to use FileMapper?
def getGcamVersion(exeDir, preferPath=False):
    '''
    Try to get GCAM version by running gcam with --version flag, but if that
    fails, try to extract it from the path.
    '''
    if preferPath:
        # See if the version is explicit in the path, e.g., "...-v6.0"
        gcamDir = os.path.dirname(exeDir)
        m = re.match(_PathVersionPattern, gcamDir)
        if m:
            return m.group(1)

    # Try to run GCAM to have it report the version
    exeName = getParam('GCAM.Executable')
    exePath = pathjoin(exeDir, exeName)

    if not os.path.lexists(exePath):
        gcamDir = os.path.dirname(exeDir)
        _logger.info("GCAM not found at %s; extracting version from path", gcamDir)
        m = re.match(_PathVersionPattern, gcamDir)
        if m:
            return m.group(1)
        else:
            raise PygcamException(f'Failed to extract version number from path {gcamDir}')

    setJavaPath(exeDir)
    with pushd(exeDir):
        try:
            cmd = [exePath, '--version']
            versionStr = subprocess.check_output(cmd, shell=False).strip().decode('utf-8')

        except subprocess.CalledProcessError:
            raise ConfigFileError(
                f"Attempt to run '{exePath} --version' failed. Versions of GCAM before v5.2 are no longer supported by pygcam")

    m = re.match(_VersionFlagPattern, versionStr)
    if m:
        return m.group(1)
    else:
        raise ConfigFileError(f'GCAM --version returned "{versionStr}", which is not the expected format. Should start with "GCAM version "')

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
            classpath = getParam('GCAM.MI.ClassPath')
            command = f'java -cp "{classpath}" XMLDBDriver --print-java-home'
            msg_cmd = 'XMLDBDriver --print-java-home'

            try:
                output = subprocess.check_output(str(command), shell=True)
                javaHome = output.decode('utf-8').strip()
            except Exception as e:
                raise PygcamException(f"Cannot get java home dir: {e}")

        os.environ['JAVA_HOME'] = javaHome

        if not javaHome:
            raise PygcamException(f"JAVA_HOME not set and failed to read java home directory from '{msg_cmd}'")

    if not os.path.isdir(javaHome):
        raise PygcamException(f'Java home ({javaHome}) is not a directory')

    # Update the PATH to be able to find the Java dlls
    # SET PATH=%PATH%;%JAVA_HOME%\bin;%JAVA_HOME%\bin\server"
    javaBin = pathjoin(javaHome, 'bin')
    javaBinServer = pathjoin(javaBin, 'server')
    envPath = os.environ.get('PATH', '')
    os.environ['PATH'] = path = f"{envPath};{javaBin};{javaBinServer}"
    _logger.debug('PATH=%s', path)

    envClasspath = os.environ.get('CLASSPATH', '')
    envClasspath = ".;" + envClasspath if envClasspath else "."

    miClasspath = getParam('GCAM.MI.ClassPath')
    os.environ['CLASSPATH'] = classpath = f"{envClasspath};{javaBinServer};{miClasspath}"
    _logger.debug('CLASSPATH=%s', classpath)

def _wrapperFilter(line):
    """
    Default filter for GCAM wrapper. Return True if process should be terminated.

    :param line: (str) a single line of text emitted by GCAM to stdout.
    :return: (GcamError or None): If not None, caller raises the given error
        and terminates the GCAM process.
    """
    modelDidNotSolve = 'Model did not solve'
    pattern = re.compile(f'(.*(BaseXException|({modelDidNotSolve})).*)')

    match = re.search(pattern, line)

    if match:
        msg = 'GCAM error: ' + match.group(0)
        if match.group(2) == modelDidNotSolve:
            raise GcamSolverError(msg)
        else:
            raise GcamError(msg)

def _loadWrapperFilter(spec):
    """
    Load a user's GCAM output filter function from the specification given in
    configuration parameter GCAM.WrapperFilterFunction.
    :param spec: (str) of the form /path/to/moduleDirectory:module.functionName
    :return: the function
    """
    try:
        modPath, dotSpec = spec.split(';', 1)
    except (ValueError, Exception):
        raise ConfigFileError(f'GCAM.WrapperFilterFunction should be of the form "/path/to/moduleDirectory:module.functionName", got "{spec}"')

    try:
        import sys
        from .utils import importFromDotSpec
        sys.path.insert(0, modPath)
        func = importFromDotSpec(dotSpec)

    except PygcamException as e:
        raise ConfigFileError(f"Can't load wrapper filter function '{dotSpec}' from '{modPath}': {e}")

    return func

def _gcamWrapper(args):
    try:
        _logger.debug('Starting gcam with wrapper')
        gcamProc = subprocess.Popen(args, bufsize=0, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, close_fds=True)

    except Exception as e:
        cmd = ' '.join(args)
        msg = f'gcamWrapper failed to run command: {cmd} ({e})'
        raise PygcamException(msg)

    filterSpec = getParam('GCAM.WrapperFilterFunction')
    wrapperFilter = _loadWrapperFilter(filterSpec) if filterSpec else _wrapperFilter

    gcamOut = gcamProc.stdout

    while True:
        line = gcamOut.readline().decode('utf-8')
        if line == '':
            break

        _logger.info(line.rstrip())          # see if this ends up in worker.log

        error = wrapperFilter(line)
        if error:
            gcamProc.terminate()
            raise error

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
# have an Oracle provided JDK. They each take slightly different
# approaches to where libraries live and how to reference them, so
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
        raise PygcamException(f'Could not find Java install location using "{cmd}"')

    # If javaHome contains "1.6", use the Apple supplied version of java 1.6
    libPath = 'lib-stub' if '1.6' in javaHome else javaHome + '/jre/lib/server'

    owd = os.getcwd()
    refWorkspace = getParam('GCAM.RefWorkspace')
    os.chdir(refWorkspace)

    try:
        # Create a symlink to satisfy @rpath searches
        linkName = 'libs/java/lib'
        if not os.path.islink(linkName):
            cmd = f"ln -s {libPath} {linkName}"
            status = subp.call(cmd, shell=True)
            if status != 0:
                raise PygcamException(f'Failed to create link using "{cmd}"')
    finally:
        os.chdir(owd)


def runGCAM(mapper : FileMapper, noRun=False, noWrapper=False):
    """
    :param mapper: (FileMapper) contains file and directory information
    :param scenario: (str) the scenario to run
    :param group: (str) the name of the scenario group to use
    :param configFile: (str) if scenario is not given, the name of a configuration
       file to run. If scenario is given, this parameter is ignored.
    :param noRun: (bool) if True, don't run the model, just create the sandbox and
       display the command that would be executed.
    :param noWrapper: (bool) if True, don't run GCAM inside a "wrapper" that reads
        output and kills the model run as soon as an error is detected.
    :return: none
    :raises ProgramExecutionError: if GCAM exits with non-zero status
    """
    import platform
    from .constants import FileVersions

    if platform.system() == 'Darwin':
        linkToMacJava()

    sandbox_scenario_dir = mapper.sandbox_scenario_dir

    if not os.path.lexists(sandbox_scenario_dir):
        raise PygcamException(f"Sandbox '{sandbox_scenario_dir}' does not exist.")

    exeDir = mapper.sandbox_exe_dir
    setJavaPath(exeDir)     # required for Windows; a no-op otherwise

    # InMemoryDatabase implies RunQueriesInGCAM
    if not (getParamAsBoolean('GCAM.RunQueriesInGCAM') or getParamAsBoolean('GCAM.InMemoryDatabase')):
        # Write a "no-op" XMLDBDriver.properties file
        writeXmldbDriverProperties(inMemory=False, outputDir=exeDir)

    gcam_args = [mapper.sandbox_exe_path, '-C', mapper.get_config_version(FileVersions.FINAL)]

    command = ' '.join(gcam_args)
    if noRun:
        print(command)
    else:
        _logger.info('Running: %s', command)

        noWrapper = IsWindows or noWrapper     # don't use the wrapper on Windows
        with pushd(exeDir):
            exitCode = subprocess.call(gcam_args, shell=False) if noWrapper else _gcamWrapper(gcam_args)

        if exitCode != 0:
            raise ProgramExecutionError(command, exitCode)
