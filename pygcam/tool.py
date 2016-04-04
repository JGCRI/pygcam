#!/usr/bin/env python

'''
.. The "gcamtool" commandline program

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import argparse
import os
from glob import glob
from .utils import loadModuleFromPath
from .error import PygcamException
from .chart import ChartCommand
from .constraints import GenConstraintsCommand, DeltaConstraintsCommand
from .diff import DiffCommand
from .project import ProjectCommand
from .landProtection import ProtectLandCommand
from .query import QueryCommand
from .run import GcamCommand
from .workspace import WorkspaceCommand
from .setup import SetupCommand
from .config import DEFAULT_SECTION, getConfig, getParam
from .log import getLogger, setLogLevel, configureLogs

_logger = getLogger(__name__)

PROGRAM = 'gcamtool'
__version__ = '0.1'

BuiltinSubcommands = [ChartCommand, DiffCommand,
                      DeltaConstraintsCommand, GenConstraintsCommand,
                      GcamCommand, ProjectCommand, ProtectLandCommand,
                      QueryCommand, SetupCommand, WorkspaceCommand]

class GcamTool(object):

    _plugins = {}

    @classmethod
    def getPlugin(cls, name):
        return cls._plugins.get(name, None)

    @classmethod
    def addPlugin(cls, plugin):
        cls._plugins[plugin.name] = plugin

    def __init__(self, loadPlugins=True):
        self.parser = parser = argparse.ArgumentParser(prog=PROGRAM)

        # Note that the "main_" prefix is significant; see _is_main_arg() above
        # parser.add_argument('-V', '--main_verbose', action='store_true', default=False,
        #                     help='Causes log messages to be printed to console.')

        parser.add_argument('-l', '--logLevel', type=str.lower,
                            choices=['notset', 'debug', 'info', 'warning', 'error', 'critical'],
                            help='Sets the log level of the program.')

        parser.add_argument('-s', '--configSection',
                            help='''The name of the config file section to read from.''')

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

        if argList:
            # called recursively
            args = self.parser.parse_args(args=argList)
        else:
            # top-level call

            section = args.configSection or getParam('GCAM.DefaultProject')
            if section:
                getConfig(section=section, reload=True)

            logLevel = args.logLevel or getParam('GCAM.LogLevel')
            if logLevel:
                setLogLevel(logLevel)

            configureLogs(force=True)

        # Get the sub-command and run it with the given args
        obj = self.getPlugin(args.subcommand)
        obj.run(args, self)


def _getMainParser():
    '''
    Used only to generate documentation by sphinx' argparse, in which case
    we don't generate documentation for project-specific plugins.
    '''
    getConfig(DEFAULT_SECTION)
    tool = GcamTool(loadPlugins=False)
    return tool.parser
