#!/usr/bin/env python

'''
.. The "gcamtool" commandline program

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import argparse
import pipes
import subprocess
import time
from glob import glob
from .utils import loadModuleFromPath, getTempFile, mkdirs
from .error import PygcamException, ProgramExecutionError, ConfigFileError, CommandlineError
from .chart import ChartCommand
from .config import ConfigCommand, setSection
from .constraints import GenConstraintsCommand, DeltaConstraintsCommand
from .diff import DiffCommand
from .project import ProjectCommand
from .landProtection import ProtectLandCommand
from .query import QueryCommand
from .runGCAM import GcamCommand
from .workspace import WorkspaceCommand
from .setup import SetupCommand
from .config import getConfig, getParam
from .log import getLogger, setLogLevel, configureLogs

_logger = getLogger(__name__)

PROGRAM = 'gcamtool'
__version__ = '0.1'

BuiltinSubcommands = [ChartCommand, ConfigCommand, DiffCommand,
                      DeltaConstraintsCommand, GenConstraintsCommand,
                      GcamCommand, ProjectCommand, ProtectLandCommand,
                      QueryCommand, SetupCommand, WorkspaceCommand]

def _writeScript(args, delete=False):
    """
    Create a shell script in a temporary file which calls gcamtool.py
    with the given `args`.
    :param args: (list of str) arguments to gcamtool.py to write into
        a script to be executed as a batch job
    :param delete: (bool) if True, mark the tmp file for deletion.
    :return: (str) the pathname of the script
    """
    tmpDir = getParam('GCAM.UserTempDir')
    mkdirs(tmpDir)

    scriptFile  = getTempFile(suffix='.pygcam.sh', tmpDir=tmpDir, delete=delete)
    _logger.info("Creating batch script '%s'", scriptFile)

    with open(scriptFile, 'w') as f:
        shellArgs = map(pipes.quote, args)
        f.write("#!/bin/bash\n")
        f.write("rm -f %s\n" % pipes.quote(scriptFile))       # file removes itself
        f.write("gcamtool.py %s\n" % ' '.join(shellArgs))

    os.chmod(scriptFile, 0755)
    return scriptFile

# def _randomSleep(minSleep, maxSleep):
#     '''
#     Sleep for a random number of seconds between minSleep and maxSleep.
#     '''
#     import random
#     import time
#
#     delay = minSleep + random.random() * (maxSleep - minSleep)
#     _logger.debug('randomSleep: sleeping %.1f seconds', delay)
#     time.sleep(delay)
#
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
#             exists = True
#             break
#
#         _randomSleep(minSleep, maxSleep)
#
#     if not exists:
#         raise PygcamException("Failed to read args file after %d tries" % maxTries)

# From https://gist.github.com/sampsyo/471779
class AliasedSubParsersAction(argparse._SubParsersAction):
    """
    Adds an "aliases" keyword when adding subparsers, allowing
    sub-command aliases.
    """
    class _AliasedPseudoAction(argparse.Action):
        def __init__(self, name, aliases, help):
            dest = name
            if aliases:
                dest += ' (%s)' % ','.join(aliases)
            sup = super(AliasedSubParsersAction._AliasedPseudoAction, self)
            sup.__init__(option_strings=[], dest=dest, help=help)

    def add_parser(self, name, **kwargs):
        if 'aliases' in kwargs:
            aliases = kwargs['aliases']
            del kwargs['aliases']
        else:
            aliases = []

        parser = super(AliasedSubParsersAction, self).add_parser(name, **kwargs)

        # Make the aliases work.
        for alias in aliases:
            self._name_parser_map[alias] = parser
        # Make the help text reflect them, first removing old help entry.
        if 'help' in kwargs:
            help = kwargs.pop('help')
            self._choices_actions.pop()
            pseudo_action = self._AliasedPseudoAction(name, aliases, help)
            self._choices_actions.append(pseudo_action)

        parser.aliases = aliases    # save these so we can find the plugin, too
        return parser


class GcamTool(object):

    _plugins = {}

    @classmethod
    def getPlugin(cls, name):
        return cls._plugins.get(name, None)

    @classmethod
    def addPlugin(cls, plugin):
        cls._plugins[plugin.name] = plugin
        for alias in plugin.parser.aliases:
            cls._plugins[alias] = plugin

    def __init__(self, loadPlugins=True):
        self.parser = parser = argparse.ArgumentParser(prog=PROGRAM)
        self.parser.register('action', 'parsers', AliasedSubParsersAction)

        parser.add_argument('-b', '--batch', action='store_true',
                            help='''Run the commands by submitting a batch job using the command
                            given by config variable GCAM.BatchCommand. (Linux only)''')

        parser.add_argument('-B', '--noBatch', action="store_true",
                            help="Show the batch command to be run, but don't run it. (Linux only)")

        parser.add_argument('-e', '--enviroVars',
                            help='''Comma-delimited list of environment variable assignments to pass
                            to queued batch job, e.g., -E "FOO=1,BAR=2". (Linux only)''')

        parser.add_argument('-j', '--jobName', default='gcamtool',
                            help='''Specify a name for the queued batch job. Default is "gcamtool".
                            (Linux only)''')

        parser.add_argument('-l', '--logLevel', type=str.lower, metavar='level',
                            choices=['notset', 'debug', 'info', 'warning', 'error', 'critical'],
                            help='Sets the log level of the program.')

        parser.add_argument('-L', '--logFile',
                            help='Sets the name of a log file for batch runs.')

        parser.add_argument('-m', '--minutes', type=float,
                            help='''Set the number of minutes to allocate for the queued batch job.
                            Overrides config parameter GCAM.Minutes. (Linux only)''')

        parser.add_argument('-P', '--projectName', dest='configSection', metavar='name',
                            help='''The project name (the config file section to read from),
                            which defaults to the value of config variable GCAM.DefaultProject''')

        parser.add_argument('-q', '--queueName',
                            help='''Specify the name of the queue to which to submit the batch job.
                            Default is given by config variable GCAM.DefaultQueue. (Linux only)''')

        parser.add_argument('-r', '--resources', default='',
                            help='''Specify resources for the queued batch command. Can be a comma-delimited
                            list of assignments of the form NAME=value, e.g., -r 'pvmem=6GB'. (Linux only)''')

        parser.add_argument('-v', '--verbose', action='store_true',
                            help='''Show diagnostic output''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

        self.subparsers = self.parser.add_subparsers(dest='subcommand', title='Subcommands',
                               description='''For help on subcommands, use the "-h" flag after the subcommand name''')

        map(self.instantiatePlugin, BuiltinSubcommands)

        if loadPlugins:
            pluginPath = getParam('GCAM.PluginPath')
            if pluginPath:
                sep = os.path.pathsep           # ';' on Windows, ':' on Unix
                items = pluginPath.split(sep)
                self.loadPlugins(items)

        # moduleDir = os.path.dirname(os.path.abspath(__file__))
        # pluginDir = os.path.join(moduleDir, 'plugins')
        # self.loadPlugins([pluginDir] + items)

    def instantiatePlugin(self, pluginClass):
        plugin = pluginClass(self.subparsers)
        self.addPlugin(plugin)

    def loadPlugin(self, path):
        """
        Load the plugin at `path`.

        :param path: (str) the pathname of a plugin file.
        :param subparsers: instance of argparse.parser.add_subparsers
        :return: an instance of the ``SubcommandABC`` subclass defined in `path`
        """
        def getModObj(mod, name):
            return getattr(mod, name) if name in mod.__dict__ else None

        mod = loadModuleFromPath(path)

        pluginClass = getModObj(mod, 'PluginClass') or getModObj(mod, 'Plugin')
        if not pluginClass:
            raise PygcamException('Neither PluginClass nor class Plugin are defined in %s' % path)

        self.instantiatePlugin(pluginClass)

    def loadPlugins(self, pluginDirs):
        """
        Load plugins from the list of directories calculated in
        ``SubcommandABC.__init__()`` and instantiate them.

        :return: None
        """
        for d in pluginDirs:
            pattern = os.path.join(d, '*_plugin.py')
            for path in glob(pattern):
                self.loadPlugin(path)

    def run(self, args=None, argList=None):
        """
        Parse the script's arguments and invoke the run() method of the
        designated sub-command.

        :param args: an argparse.Namespace of parsed arguments
        :param argList: (list of str) argument list to parse (when called recursively)
        :return: none
        """
        assert args or argList, "gcamtool.run requires either args or argList"

        if argList is not None:         # might be called with empty list of subcmd args
            # called recursively
            args = self.parser.parse_args(args=argList)

        else:  # top-level call
            if args.batch:
                args.batch = False

            # show batch command and exit
            if args.noBatch:
                pass

            args.configSection = section = args.configSection or getParam('GCAM.DefaultProject')
            if section:
                 setSection(section)

            logLevel = args.logLevel or getParam('GCAM.LogLevel')
            if logLevel:
                setLogLevel(logLevel)

            configureLogs(force=True)

        # Get the sub-command and run it with the given args
        obj = self.getPlugin(args.subcommand)
        obj.run(args, self)

    def runBatch(self, shellArgs, run=True):
        import platform

        system = platform.system()
        if system in ['Windows', 'Darwin']:
            system = 'Mac OS X' if system == 'Darwin' else system
            raise CommandlineError('Batch commands are not supported on %s' % system)

        scriptFile = _writeScript(shellArgs, delete=not run)    # delete it if just showing cmd

        args = self.parser.parse_args(args=shellArgs)
        jobName   = args.jobName
        queueName = args.queueName or getParam('GCAM.DefaultQueue')
        logFile   = args.logFile
        minutes   = args.minutes or float(getParam('GCAM.Minutes'))
        walltime  = "%02d:%02d:00" % (minutes / 60, minutes % 60)

        # This dictionary is applied to the string value of GCAM.BatchCommand, via
        # the str.format method, which must specify options using any of the keys.
        batchArgs = {'logFile'   : logFile,
                     'minutes'   : minutes,
                     'walltime'  : walltime,
                     'queueName' : queueName,
                     'jobName'   : jobName}

        batchCmd = getParam('GCAM.BatchCommand')
        batchCmd += ' ' + scriptFile

        try:
            command = batchCmd.format(**batchArgs)
        except KeyError as e:
            raise ConfigFileError('Badly formatted batch command (%s) in config file: %s', batchCmd, e)

        if not run:
            print command
            return

        _logger.info('Running: %s', command)
        time.sleep(3)   # script file isn't visible immediately on compute nodes...
        try:
            exitCode = subprocess.call(command)
            if exitCode != 0:
                raise ProgramExecutionError("Non-zero exit status (%d) from '%s'" % (exitCode, command))
        except Exception as e:
            raise PygcamException("Error running command '%s': %s" % (command, e))


def _getMainParser():
    '''
    Used only to generate documentation by sphinx' argparse, in which case
    we don't generate documentation for project-specific plugins.
    '''
    getConfig()
    tool = GcamTool(loadPlugins=False)
    return tool.parser
