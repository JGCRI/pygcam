#!/usr/bin/env python

'''
.. The "gt" (gcamtool) commandline program

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import argparse
import os
import pipes
import signal
import subprocess
from glob import glob

from .builtins.chart_plugin import ChartCommand
from .builtins.config_plugin import ConfigCommand
from .builtins.diff_plugin import DiffCommand
from .builtins.gcam_plugin import GcamCommand
from .builtins.new_plugin import NewProjectCommand
from .builtins.protect_plugin import ProtectLandCommand
from .builtins.query_plugin import QueryCommand
from .builtins.run_plugin import ProjectCommand
from .builtins.sandbox_plugin import SandboxCommand
from .builtins.setup_plugin import SetupCommand

from .config import (getParam, getConfig, getParamAsBoolean, setParam,
                     getSection, setSection, DEFAULT_SECTION)
from .error import PygcamException, ProgramExecutionError, ConfigFileError, CommandlineError
from .log import getLogger, setLogLevel, configureLogs
from .project import decacheVariables
from .utils import loadModuleFromPath, getTempFile, TempFile, mkdirs
from .windows import IsWindows

_logger = getLogger(__name__)

PROGRAM = 'gt'
__version__ = '0.1'

BuiltinSubcommands = [ChartCommand, ConfigCommand, DiffCommand, GcamCommand,
                      NewProjectCommand, ProjectCommand, ProtectLandCommand,
                      QueryCommand, SetupCommand, SandboxCommand]

# For now, these are not offered as command-line options. Needs more testing.
# BioConstraintsCommand, DeltaConstraintsCommand,

def _writeBatchScript(args, delete=False):
    """
    Create a shell script in a temporary file which calls gt with the
    given `args`.
    :param args: (list of str) arguments to "gt" to write into a
        script to be executed as a batch job
    :param delete: (bool) if True, mark the tmp file for deletion.
    :return: (str) the pathname of the script
    """
    tmpDir = getParam('GCAM.UserTempDir')
    mkdirs(tmpDir)

    scriptFile  = getTempFile(suffix='.pygcam.sh', tmpDir=tmpDir, delete=False)
    _logger.info("Creating batch script '%s'", scriptFile)

    with open(scriptFile, 'w') as f:
        f.write("#!%s\n" % os.getenv('SHELL', '/bin/bash'))
        if delete:
            f.write("rm -f %s\n" % pipes.quote(scriptFile)) # file removes itself once running
        else:
            _logger.info('Batch script file will not be deleted.')

        shellArgs = map(pipes.quote, args)
        f.write("gt %s\n" % ' '.join(shellArgs))

    os.chmod(scriptFile, 0o755)
    return scriptFile

def _randomSleep(minSleep, maxSleep):
    '''
    Sleep for a random number of seconds between minSleep and maxSleep.
    '''
    import random
    import time

    delay = minSleep + random.random() * (maxSleep - minSleep)
    _logger.debug('randomSleep: sleeping %.1f seconds', delay)
    time.sleep(delay)

# Deprecated
# def _waitForScript(scriptFile):
#     """
#     It can take a few moments for the script to be visible on a compute node.
#     """
#     maxTries = 4
#     minSleep = 1
#     maxSleep = 4
#
#     exists = False
#     for i in range(maxTries):
#         if os.path.exists(scriptFile):
#             print("%s exists!" % scriptFile)
#             exists = True
#             break
#
#         _randomSleep(minSleep, maxSleep)    # TBD: check if this is still necessary
#
#     if not exists:
#         raise PygcamException("Failed to read args file after %d tries" % maxTries)


class GcamTool(object):

    # plugin instances by command name
    _plugins = {}

    # cached plugin paths by command name
    _pluginPaths = {}

    @classmethod
    def getPlugin(cls, name):
        if name not in cls._plugins:
            cls._loadCachedPlugin(name)

        return cls._plugins.get(name, None)

    @classmethod
    def _loadCachedPlugin(cls, name):
        # see if it's already loaded
        path = cls._pluginPaths[name]
        tool = cls.getInstance()
        tool.loadPlugin(path)

    @classmethod
    def _cachePlugins(cls):
        '''
        Find all plugins via GCAM.PluginPath and create a dict
        of plugin pathnames keyed by command name so the plugin
        can be loaded on-demand.
        :return: none
        '''
        pluginDirs = cls._getPluginDirs()

        suffix = '_plugin.py'
        suffixLen = len(suffix)

        for d in pluginDirs:
            pattern = os.path.join(d, '*' + suffix)
            for path in glob(pattern):
                basename = os.path.basename(path)
                command = basename[:-suffixLen]
                cls._pluginPaths[command] = path

    _instance = None

    @classmethod
    def getInstance(cls, loadPlugins=True):
        if not cls._instance:
            cls._instance = cls(loadPlugins=loadPlugins)

        return cls._instance

    def __init__(self, loadPlugins=True):

        # TODO: This is a patch to so address re-entry issue, prior to proper integration
        decacheVariables()

        self.mcsMode = ''

        self.parser = parser = argparse.ArgumentParser(prog=PROGRAM)

        parser.add_argument('-b', '--batch', action='store_true',
                            help='''Run the commands by submitting a batch job using the command
                            given by config variable GCAM.BatchCommand. (Linux only)''')

        parser.add_argument('-B', '--showBatch', action="store_true",
                            help="Show the batch command to be run, but don't run it. (Linux only)")

        parser.add_argument('-e', '--enviroVars',
                            help='''Comma-delimited list of environment variable assignments to pass
                            to queued batch job, e.g., -E "FOO=1,BAR=2". (Linux only)''')

        parser.add_argument('-j', '--jobName', default='gt',
                            help='''Specify a name for the queued batch job. Default is "gt".
                            (Linux only)''')

        parser.add_argument('-l', '--logLevel', type=str.lower, metavar='level',
                            choices=['notset', 'debug', 'info', 'warning', 'error', 'critical'],
                            help='Sets the log level of the program.')

        parser.add_argument('-L', '--logFile',
                            help='''Sets the name of a log file for batch runs. Default is "gt-$j.out"
                            where "$j" is replaced by "%%j", which (in SLURM) is the jobid. If the
                            argument is not an absolute pathname, it is treated as relative to the
                            value of GCAM.LogDir.''')

        parser.add_argument('-m', '--minutes', type=float,
                            help='''Set the number of minutes to allocate for the queued batch job.
                            Overrides config parameter GCAM.Minutes. (Linux only)''')

        parser.add_argument('--mcs', choices=['trial','gensim'],
                            help='''Used only when running gcamtool from gcammcs.''')

        parser.add_argument('-P', '--projectName', dest='configSection', metavar='name',
                            help='''The project name (the config file section to read from),
                            which defaults to the value of config variable GCAM.DefaultProject''')

        parser.add_argument('-q', '--queueName',
                            help='''Specify the name of the queue to which to submit the batch job.
                            Default is given by config variable GCAM.DefaultQueue. (Linux only)''')

        parser.add_argument('-r', '--resources', default='',
                            help='''Specify resources for the queued batch command. Can be a comma-delimited
                            list of assignments of the form NAME=value, e.g., -r 'pvmem=6GB'. (Linux only)''')

        parser.add_argument('--set', dest='configVars', metavar='name=value', action='append', default=[],
                            help='''Assign a value to override a configuration file parameter. For example,
                            to set batch commands to start after a prior job of the same name completes,
                            use --set "GCAM.OtherBatchArgs=-d singleton". Enclose the argument in quotes if
                            it contains spaces or other characters that would confuse the shell.
                            Use multiple --set flags and arguments to set multiple variables.''')

        parser.add_argument('-v', '--verbose', action='store_true',
                            help='''Show diagnostic output''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

        self.subparsers = self.parser.add_subparsers(dest='subcommand', title='Subcommands',
                               description='''For help on subcommands, use the "-h" flag after the subcommand name''')

        # load all built-in sub-commands
        map(self.instantiatePlugin, BuiltinSubcommands)

        if loadPlugins:
            self._cachePlugins()
            # self.loadPlugins()

    def setMcsMode(self, mode):
        self.mcsMode = mode

    def getMcsMode(self):
        return self.mcsMode

    def instantiatePlugin(self, pluginClass):
        plugin = pluginClass(self.subparsers)
        self._plugins[plugin.name] = plugin

    @staticmethod
    def _getPluginDirs():
        pluginPath = getParam('GCAM.PluginPath')
        if not pluginPath:
            return []

        sep = os.path.pathsep           # ';' on Windows, ':' on Unix
        items = pluginPath.split(sep)
        return items

    def loadPlugin(self, path):
        """
        Load the plugin at `path`.

        :param path: (str) the pathname of a plugin file.
        :return: an instance of the ``SubcommandABC`` subclass defined in `path`
        """
        def getModObj(mod, name):
            return getattr(mod, name) if name in mod.__dict__ else None

        mod = loadModuleFromPath(path)

        pluginClass = getModObj(mod, 'PluginClass') or getModObj(mod, 'Plugin')
        if not pluginClass:
            raise PygcamException('Neither PluginClass nor class Plugin are defined in %s' % path)

        self.instantiatePlugin(pluginClass)

    def _loadRequiredPlugins(self, argv):
        # Create a dummy subparser to allow us to identify the requested
        # sub-command so we can load the module if necessary.
        parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False)
        parser.add_argument('-h', '--help', action='store_true')

        ns, otherArgs = parser.parse_known_args(args=argv)

        # For top-level help, or if no args, load all plugins
        # so the generated help messages includes all subcommands
        if ns.help or not otherArgs:
            map(self._loadCachedPlugin, self._pluginPaths.keys())
        else:
            # Otherwise, load any referenced sub-command
            for command in self._pluginPaths.keys():
                if command in otherArgs:
                    self.getPlugin(command)

    def run(self, args=None, argList=None):
        """
        Parse the script's arguments and invoke the run() method of the
        designated sub-command.

        :param args: an argparse.Namespace of parsed arguments
        :param argList: (list of str) argument list to parse (when called recursively)
        :return: none
        """
        assert args or argList, "GcamTool.run requires either args or argList"

        if argList is not None:         # might be called with empty list of subcmd args
            # called recursively
            self._loadRequiredPlugins(argList)
            args = self.parser.parse_args(args=argList)

        else:  # top-level call
            if args.batch:
                args.batch = False

        # Get the sub-command and run it with the given args
        obj = self.getPlugin(args.subcommand)

        obj.run(args, self)

    def runBatch(self, shellArgs, run=True):
        import platform

        system = platform.system()
        if False and system in ['Windows', 'Darwin']:
            system = 'Mac OS X' if system == 'Darwin' else system
            raise CommandlineError('Batch commands are not supported on %s' % system)

        scriptFile = _writeBatchScript(shellArgs, delete=not run)    # delete it if just showing cmd

        args = self.parser.parse_args(args=shellArgs)
        jobName   = args.jobName
        queueName = args.queueName or getParam('GCAM.DefaultQueue')
        logFile   = args.logFile or getParam('GCAM.BatchLogFile', raw=False)
        minutes   = args.minutes or float(getParam('GCAM.Minutes'))
        walltime  = "%02d:%02d:00" % (minutes / 60, minutes % 60)

        if logFile:
            logDir = getParam('GCAM.BatchLogDir')
            logFile = os.path.normpath(os.path.join(logDir, logFile))
            mkdirs(os.path.dirname(logFile))

        # This dictionary is applied to the string value of GCAM.BatchCommand, via
        # the str.format method, which must specify options using any of the keys.
        batchArgs = {'scriptFile': scriptFile,
                     'logFile'   : logFile,
                     'minutes'   : minutes,
                     'walltime'  : walltime,
                     'queueName' : queueName,
                     'jobName'   : jobName}

        batchCmd = getParam('GCAM.BatchCommand')

        try:
            command = batchCmd.format(**batchArgs)
            # deal with problem "%" chars used by SLURM variables
            if getParam('GCAM.BatchLogFileDollarToPercent'):
                command = command.replace('$', '%')
        except KeyError as e:
            raise ConfigFileError('Badly formatted batch command (%s) in config file: %s', batchCmd, e)

        if not run:
            print(command)
            print("Script file '%s':" % scriptFile)
            with open(scriptFile) as f:
                print(f.read())
            return

        _logger.info('Running: %s', command)
        try:
            exitCode = subprocess.call(command, shell=True)
            if exitCode != 0:
                raise ProgramExecutionError(command, exitCode)

        except Exception as e:
            raise PygcamException("Error running command '%s': %s" % (command, e))


def _getMainParser():
    '''
    Used only to generate documentation by sphinx' argparse, in which case
    we don't generate documentation for project-specific plugins.
    '''
    getConfig()
    tool = GcamTool.getInstance(loadPlugins=False)
    return tool.parser

# We catch only these 3 signals. Can extend this if needed.
def signame(signum):
    if signum == signal.SIGTERM:
        return 'SIGTERM'

    if signum == signal.SIGQUIT:
        return 'SIGQUIT'

    if signum == signal.SIGALRM:
        return 'SIGALRM'

    return 'signal %d' % signum

class SignalException(Exception):
    pass

def _sigHandler(signum, _frame):
    # msg = "gt process received " + signame(signum)
    raise SignalException(signum)

def catchSignals():
    signals = [signal.SIGTERM, signal.SIGINT]
    signals.append(signal.SIGABRT if IsWindows else signal.SIGQUIT)

    for sig in signals:
        signal.signal(sig, _sigHandler)

# TBD: test on Windows
def checkWindowsSymlinks():
    '''
    If running on Windows and GCAM.CopyAllFiles is not set, and
    we fail to create a test symlink, set GCAM.CopyAllFiles to True.
    '''
    if IsWindows and not getParamAsBoolean('GCAM.CopyAllFiles'):
        src = getTempFile()
        dst = getTempFile()

        try:
            os.symlink(src, dst)
        except:
            _logger.info('No symlink permission; setting GCAM.CopyAllFiles = True')
            setParam('GCAM.CopyAllFiles', 'True')

# deprecated
def _setupLogging(argv):
    parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False)
    parser.add_argument('-P', '--projectName', dest='configSection', metavar='name')
    parser.add_argument('-l', '--logLevel')

    ns, otherArgs = parser.parse_known_args(args=argv)

    ns.configSection = section = ns.configSection or getParam('GCAM.DefaultProject')
    if section:
        setSection(section)

    logLevel = ns.logLevel or getParam('GCAM.LogLevel')
    if logLevel:
        setLogLevel(logLevel)

    configureLogs(force=True)

def _main(argv=None):
    getConfig()
    configureLogs()
    checkWindowsSymlinks()

    tool = GcamTool.getInstance()
    tool._loadRequiredPlugins(argv)

    # This parser handles only --batch, --showBatch, and --projectName args.
    # If --batch is given, we need to create a script and call the GCAM.BatchCommand
    # on it. We grab --projectName so we can set PluginPath by project
    parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False)

    parser.add_argument('-b', '--batch', action='store_true')
    parser.add_argument('-B', '--showBatch', action="store_true")
    parser.add_argument('-P', '--projectName', dest='configSection', metavar='name')
    parser.add_argument('--set', dest='configVars', action='append', default=[])
    parser.add_argument('--mcs', choices=['trial','gensim'])

    ns, otherArgs = parser.parse_known_args(args=argv)

    tool.setMcsMode(ns.mcs)

    section = ns.configSection
    if section:
        setParam('GCAM.DefaultProject', section, section=DEFAULT_SECTION)
        setSection(section)

    # Set specified config vars
    for arg in ns.configVars:
        if not '=' in arg:
            raise CommandlineError('-S requires an argument of the form variable=value, got "%s"' % arg)

        name, value = arg.split('=')
        setParam(name, value)

    if ns.showBatch:          # don't run batch command; --showBatch implies --batch
        ns.batch = True

    # Catch signals to allow cleanup of TempFile instances, e.g., on ^C
    catchSignals()

    if ns.batch:
        run = not ns.showBatch
        if ns.configSection:        # add these back in for the batch script
            otherArgs = ['-P', ns.configSection] + otherArgs

        tool.runBatch(otherArgs, run=run)
    else:
        args = tool.parser.parse_args(args=otherArgs)
        tool.run(args=args)


def main(argv=None, raiseError=False):
    try:
        _main(argv)
        return 0

    except CommandlineError as e:
        print(e)

    except Exception as e:
        if raiseError:
            raise

        print("%s failed: %s" % (PROGRAM, e))

        if not getSection() or getParamAsBoolean('GCAM.ShowStackTrace'):
            import traceback
            traceback.print_exc()

    finally:
        # Delete any temporary files that were created
        TempFile.deleteAll()

    return 1
