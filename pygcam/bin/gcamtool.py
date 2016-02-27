#!/usr/bin/env python2

'''
.. Main driver for pygcam tools, which are accessed as sub-commands.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import argparse
from pygcam.config import DEFAULT_SECTION, getConfig, getParam
from pygcam.plugin import PluginManager


VERSION = '0.1'

BuiltinSubCommands = []

# Defined as plugins: ProjectCommand, ProtectCommand, ChartCommand

class GcamTool(object):

    def __init__(self):
        self.parser = None
        self.subparsers = None  # set by setupMainParser()
        self.subcommands = {}   # subcommand (plugin) instances keyed by sub-command name

        self.setupMainParser()

        pluginPath = getParam('GCAM.PluginPath')
        mgr = PluginManager(path=pluginPath)
        pluginClasses = mgr.loadPlugins()

        # Instantiate all the plugins
        for cls in BuiltinSubCommands + pluginClasses:
            obj = cls(self.subparsers)
            self.subcommands[obj.name] = obj

    def setupMainParser(self):
        self.parser = argparse.ArgumentParser()
        parser = self.parser

        # Note that the "main_" prefix is significant; see _is_main_arg() above
        # parser.add_argument('-V', '--main_verbose', action='store_true', default=False,
        #                     help='Causes log messages to be printed to console.')

        parser.add_argument('-L', '--log_level', default=None,
                            choices=['notset', 'debug', 'info', 'warning', 'error', 'critical'],
                            help='Sets the log level of the program.')

        # TBD: add a 'main' argument for config section to use, default to [DEFAULT]?

        # TBD: make verbose a main argument, passed to all sub-commands
        parser.add_argument('-v', '--verbose', action='store_true', help='''Show diagnostic output''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)

        self.subparsers = self.parser.add_subparsers(dest='subcommand', title='Subcommands',
                                                     description='''For help on subcommands, use the "-h"
                                                                    flag after the subcommand name''')

    def run(self):
        """
        Parse the script's arguments and invoke the run() method of the
        designated sub-command.

        :return: none
        """
        args = self.parser.parse_args()
        cmd = args.subcommand

        # Remove so sub-command doesn't see this
        del args.subcommand

        # Run the sub-command
        obj = self.subcommands[cmd]
        obj.run(args)


if __name__ == '__main__':
    getConfig(DEFAULT_SECTION)
    GcamTool().run()
