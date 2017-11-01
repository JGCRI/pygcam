'''
.. The "gt" (gcamtool) commandline program

.. Copyright (c) 2016-2017 Richard Plevin and UC Regents
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
import argparse
import os
import pipes
import re
import subprocess
from glob import glob

from .built_ins import BuiltinSubcommands
from .config import (getParam, getConfig, getParamAsBoolean, getParamAsFloat,
                     setParam, getSection, setSection, getSections,
                     DEFAULT_SECTION, usingMCS)
from .error import PygcamException, ProgramExecutionError, ConfigFileError, CommandlineError
from .log import getLogger, setLogLevels, configureLogs
from .project import decacheVariables
from .signals import SignalException, catchSignals
from .utils import loadModuleFromPath, getTempFile, TempFile, mkdirs, pathjoin
from .version import VERSION
from .windows import IsWindows

_logger = getLogger(__name__)

PROGRAM = 'gt'

# For now, these are not offered as command-line options. Needs more testing.
# BioConstraintsCommand, DeltaConstraintsCommand,

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
            pattern = pathjoin(d, '*' + suffix)
            for path in glob(pattern):
                basename = os.path.basename(path)
                command = basename[:-suffixLen]
                cls._pluginPaths[command] = path

    _instance = None

    @classmethod
    def getInstance(cls, loadPlugins=True, reload=False):
        """
        Get the singleton instance of the GcamTool class.

        :param loadPlugins: (bool) If true, plugins are loaded (only
           when first allocated).
        :param reload: (bool) If true, a new GcamTool instance is
           created.
        :return: (GcamTool instance) the new or cached instance.
        """
        if reload:
            GcamTool._instance = None
            GcamTool._plugins = {}
            GcamTool._pluginPaths = {}

        if not GcamTool._instance:
            GcamTool._instance = cls(loadPlugins=loadPlugins)

        return GcamTool._instance

    @classmethod
    def pluginGroup(cls, groupName, namesOnly=False):
        objs = filter(lambda obj: obj.getGroup() == groupName, cls._plugins.values())
        result = sorted(map(lambda obj: obj.name, objs)) if namesOnly else objs
        return result

    def __init__(self, loadPlugins=True, loadBuiltins=True):

        # address re-entry issue
        decacheVariables()

        self.mcsMode = ''
        self.shellArgs = None

        self.parser = self.subparsers = None
        self.addParsers()

        # load all built-in sub-commands
        if loadBuiltins:
            map(self.instantiatePlugin, BuiltinSubcommands)

        # If using MCS, load that set of built-ins, too
        if usingMCS():
            from .mcs.built_ins import MCSBuiltins
            map(self.instantiatePlugin, MCSBuiltins)

        # Load external plug-ins found in plug-in path
        if loadPlugins:
            self._cachePlugins()

    def addParsers(self):
        self.parser = parser = argparse.ArgumentParser(prog=PROGRAM, prefix_chars='-+')

        parser.add_argument('+b', '--batch', action='store_true',
                            help='''Run the commands by submitting a batch job using the command
                            given by config variable GCAM.BatchCommand. (Linux only)''')

        parser.add_argument('+B', '--showBatch', action="store_true",
                            help="Show the batch command to be run, but don't run it. (Linux only)")

        parser.add_argument('+e', '--enviroVars',
                            help='''Comma-delimited list of environment variable assignments to pass
                            to queued batch job, e.g., -E "FOO=1,BAR=2". (Linux only)''')

        parser.add_argument('+j', '--jobName', default='gt',
                            help='''Specify a name for the queued batch job. Default is "gt".
                            (Linux only)''')

        logLevel = str(getParam('GCAM.LogLevel'))   # so not unicode
        parser.add_argument('+l', '--logLevel',
                            default=logLevel or 'notset',
                            help='''Sets the log level for modules of the program. A default
                                log level can be set for the entire program, or individual 
                                modules can have levels set using the syntax 
                                "module:level, module:level,...", where the level names must be
                                one of {debug,info,warning,error,fatal} (case insensitive).''')

        parser.add_argument('+L', '--logFile',
                            help='''Sets the name of a log file for batch runs. Default is "gt-%%j.out"
                            where "%%j" (in SLURM) is the jobid. If the argument is not an absolute 
                            pathname, it is treated as relative to the value of GCAM.LogDir.''')

        parser.add_argument('+m', '--minutes', type=float, default=getParamAsFloat('GCAM.Minutes'),
                            help='''Set the number of minutes to allocate for the queued batch job.
                            Overrides config parameter GCAM.Minutes. (Linux only)''')

        parser.add_argument('+M', '--mcs', dest='mcsMode', choices=['trial','gensim'],
                            help='''Used only when running gcamtool from pygcam-mcs.''')

        parser.add_argument('+P', '--projectName', metavar='name', default=getParam('GCAM.DefaultProject'),
                            choices=sorted(getSections()),
                            help='''The project name (the config file section to read from),
                            which defaults to the value of config variable GCAM.DefaultProject''')

        parser.add_argument('+q', '--queueName', default=getParam('GCAM.DefaultQueue'),
                            help='''Specify the name of the queue to which to submit the batch job.
                            Default is given by config variable GCAM.DefaultQueue. (Linux only)''')

        parser.add_argument('+r', '--resources', default='',
                            help='''Specify resources for the queued batch command. Can be a comma-delimited
                            list of assignments of the form NAME=value, e.g., -r 'pvmem=6GB'. (Linux only)''')

        parser.add_argument('+s', '--set', dest='configVars', metavar='name=value', action='append', default=[],
                            help='''Assign a value to override a configuration file parameter. For example,
                            to set batch commands to start after a prior job of the same name completes,
                            use --set "GCAM.OtherBatchArgs=-d singleton". Enclose the argument in quotes if
                            it contains spaces or other characters that would confuse the shell.
                            Use multiple --set flags and arguments to set multiple variables.''')

        parser.add_argument('+v', '--verbose', action='store_true',
                            help='''Show diagnostic output''')

        parser.add_argument('--version', action='version', version='%(prog)s-' + VERSION)   # goes to stderr, handled by argparse

        parser.add_argument('--VERSION', action='store_true')   # goes to stdout, but handled by gt

        self.subparsers = self.parser.add_subparsers(dest='subcommand', title='Subcommands',
                               description='''For help on subcommands, use the "-h" flag after the subcommand name''')

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
        parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False, prefix_chars='-+')
        parser.add_argument('-h', '--help', action='store_true')
        parser.add_argument('+P', '--projectName', metavar='name')

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

        checkWindowsSymlinks()

        if argList is not None:         # might be called with empty list of subcmd args
            # called recursively
            self._loadRequiredPlugins(argList)
            args = self.parser.parse_args(args=argList)

        else:  # top-level call
            if args.batch:
                args.batch = False

            args.projectName = section = args.projectName or getParam('GCAM.DefaultProject')
            if section:
                 setSection(section)

            logLevel = args.logLevel or getParam('GCAM.LogLevel')
            if logLevel:
                setLogLevels(logLevel)

            configureLogs(force=True)

        # Get the sub-command and run it with the given args
        obj = self.getPlugin(args.subcommand)

        obj.run(args, self)

    # Extracted from runBatch() to be callable from the run sub-command
    # to distribute scenario runs.
    @staticmethod
    def runBatch2(shellArgs, jobName='gt', queueName=None, logFile=None, minutes=None,
                  dependsOn=None, run=True):

        queueName = queueName or getParam('GCAM.DefaultQueue')
        logFile   = logFile   or getParam('GCAM.BatchLogFile', raw=False)
        minutes   = minutes   or getParamAsFloat('GCAM.Minutes')

        batchSystem = getParam('GCAM.BatchSystem')
        known = ('SLURM', 'LSF', 'PBS')
        if batchSystem not in known:
            raise ConfigFileError('GCAM.Scheduler value (%s) is not recognized. Must be one of %s.' % (batchSystem, known))

        # The LSF scheduler needs HH:MM; SLURM needs HH:MM:SS
        format = "%02d:%02d" if batchSystem == 'LSF' else "%02d:%02d:00"
        walltime  = format % (minutes / 60, minutes % 60)

        if logFile:
            logDir = getParam('GCAM.BatchLogDir')
            logFile = os.path.normpath(pathjoin(logDir, logFile))
            mkdirs(os.path.dirname(logFile))

        # TBD: make this an expression eval'd with s.format(jobID=dependsOn)
        # TBD: to support other syntaxes
        format = "-w 'done(%s)'" if batchSystem == 'LSF' else "-d afterok:%s"
        dependencies = format % dependsOn if dependsOn else ''

        scriptCommand = "gt " + ' '.join(shellArgs)

        # This dictionary is applied to the string value of GCAM.BatchCommand, via
        # the str.format method, which must specify options using any of the keys.
        batchArgs = {'scriptFile': scriptCommand,
                     'dependencies' : dependencies,
                     'logFile'   : logFile,
                     'minutes'   : minutes,
                     'walltime'  : walltime,
                     'queueName' : queueName,
                     'partition' : queueName,   # synonym for queue name
                     'jobName'   : jobName}

        batchCmd = getParam('GCAM.BatchCommand')

        try:
            command = batchCmd.format(**batchArgs)

        except KeyError as e:
            raise ConfigFileError('Badly formatted batch command (%s) in config file: %s', batchCmd, e)

        if not run:
            print(command)
            return

        _logger.info('Running: %s', command)
        try:
            jobStr = subprocess.check_output(command, shell=True)
            result = re.search('\d+', jobStr)
            jobId = int(result.group(0)) if result else -1
            return jobId

        except subprocess.CalledProcessError as e:
            raise ProgramExecutionError(command, e.returncode)

        except Exception as e:
            raise PygcamException("Error running command '%s': %s" % (command, e))

    def runBatch(self, shellArgs, run=True):
        import platform

        system = platform.system()
        if system in ['Windows']: # , 'Darwin']:
            system = 'Mac OS X' if system == 'Darwin' else system
            raise CommandlineError('Batch commands are not supported on %s' % system)

        shellArgs = map(pipes.quote, shellArgs)
        args = self.parser.parse_args(args=shellArgs)

        return self.runBatch2(shellArgs, jobName=args.jobName, queueName=args.queueName,
                              logFile=args.logFile, minutes=args.minutes, run=run)

def _getMainParser():
    '''
    Used only to generate documentation by sphinx' argparse, in which case
    we don't generate documentation for project-specific plugins.
    '''
    getConfig()
    tool = GcamTool.getInstance(loadPlugins=False)
    return tool.parser


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

def _setDefaultProject(argv):
    parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False, prefix_chars='-+')
    parser.add_argument('+P', '--projectName', metavar='name')

    ns, _otherArgs = parser.parse_known_args(args=argv)

    section = ns.projectName
    if section:
        setParam('GCAM.DefaultProject', section, section=DEFAULT_SECTION)
        setSection(section)

def _main(argv=None):
    getConfig()
    configureLogs()

    _setDefaultProject(argv)

    tool = GcamTool.getInstance()
    tool._loadRequiredPlugins(argv)

    # This parser handles only --VERSION flag.
    parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False, prefix_chars='-+')
    parser.add_argument('--VERSION', action='store_true')
    ns, otherArgs = parser.parse_known_args(args=argv)
    if ns.VERSION:
        import sys
        print(PROGRAM + '-' + VERSION)
        sys.exit(0)

    # This parser handles only --batch, --showBatch, and --projectName args.
    # If --batch is given, we need to create a script and call the GCAM.BatchCommand
    # on it. We grab --projectName so we can set PluginPath by project
    parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False, prefix_chars='-+')

    parser.add_argument('+b', '--batch', action='store_true')
    parser.add_argument('+B', '--showBatch', action="store_true")
    parser.add_argument('+P', '--projectName', dest='projectName', metavar='name')
    parser.add_argument('+s', '--set', dest='configVars', action='append', default=[])
    parser.add_argument('+M', '--mcs', dest='mcsMode', choices=['trial','gensim'])

    ns, otherArgs = parser.parse_known_args(args=argv)

    tool.setMcsMode(ns.mcsMode)

    # Set specified config vars
    for arg in ns.configVars:
        if not '=' in arg:
            raise CommandlineError('-S requires an argument of the form variable=value, got "%s"' % arg)

        name, value = arg.split('=')
        setParam(name, value)

    # showBatch => don't run batch command, but implies --batch
    if ns.showBatch:
        ns.batch = True

    # Catch signals to allow cleanup of TempFile instances, e.g., on ^C
    catchSignals()

    if ns.batch:
        run = not ns.showBatch
        if ns.projectName:        # add these back in for the batch script
            otherArgs = ['+P', ns.projectName] + otherArgs

        tool.runBatch(otherArgs, run=run)
    else:
        tool.shellArgs = otherArgs  # save for project run method to use in "distribute" mode
        args = tool.parser.parse_args(args=otherArgs)
        tool.run(args=args)


def main(argv=None, raiseError=False):
    try:
        _main(argv)
        return 0

    except CommandlineError as e:
        print(e)

    except SignalException as e:
        if raiseError:
            raise

        _logger.error("%s: %s" % (PROGRAM, e))
        return e.signum

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
