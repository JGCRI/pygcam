#!/usr/bin/env python

'''
.. Main driver for pygcam tools, which are accessed as sub-commands.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import argparse
import pygcam.windows
from pygcam.config import DEFAULT_SECTION, getConfig, getParam
from pygcam.plugin import PluginManager
from pygcam.log import getLogger, getLevel

_logger = getLogger(__name__)

PROGRAM = 'gcamtool'
VERSION = '0.1'



# Defined as plugins: ProjectCommand, ProtectCommand, ChartCommand

class GcamTool(object):

    verbose = 0
    subcommands = {}   # subcommand (plugin) instances keyed by sub-command name

    def __init__(self):
        self.project = None
        self.parser = parser = argparse.ArgumentParser(prog=PROGRAM)

        # Note that the "main_" prefix is significant; see _is_main_arg() above
        # parser.add_argument('-V', '--main_verbose', action='store_true', default=False,
        #                     help='Causes log messages to be printed to console.')

        parser.add_argument('-l', '--logLevel', dest='main_logLevel', default=None,
                            choices=['notset', 'debug', 'info', 'warning', 'error', 'critical'],
                            help='Sets the log level of the program.')

        # TBD: add a 'main' argument for config section to use, default to [DEFAULT]?
        parser.add_argument('-p', '--project', dest='main_project', type=str, default=None,
                            help='''The name of the project to run.''')

        # TBD: make verbose a main argument, passed to all sub-commands
        parser.add_argument('-v', '--verbose', dest='main_verbose', action='store_true',
                            help='''Show diagnostic output''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)

        self.subparsers = self.parser.add_subparsers(dest='subcommand', title='Subcommands',
                                                     description='''For help on subcommands, use the "-h"
                                                                    flag after the subcommand name''')
        pluginPath = getParam('GCAM.PluginPath')
        mgr = PluginManager(path=pluginPath)
        mgr.loadPlugins(self.subparsers)

    def run(self, args=None, argList=None):
        """
        Parse the script's arguments and invoke the run() method of the
        designated sub-command.

        :param args: an argparse.Namespace of parsed arguments
        :param recursive: (bool) True when called recursively (e.g., from project.py)
        :return: none
        """
        assert args or argList, "gcamtool.run requires either args or argList"

        if argList:
            # called recursively
            args = self.parser.parse_args(args=argList)
        else:
            # top-level call
            self.verbose  = args.main_verbose  # may be deprecated
            self.project  = args.main_project
            self.logLevel = args.main_logLevel

            # Remove so sub-command doesn't see these
            del args.main_verbose
            del args.main_project
            del args.main_logLevel

        cmd = args.subcommand
        del args.subcommand

        # Run the sub-command
        obj = PluginManager.getPlugin(cmd)
        obj.run(args, self)

def _getMainParser():
    '''Used to generate documentation by sphinx' argparse'''
    getConfig(DEFAULT_SECTION)
    return GcamTool().parser


if __name__ == '__main__':
    import sys
    import pygcam.log

    # Use default section to read plugin path initially.
    # It's a chicken-and-egg problem since we can't parse args
    # until we've loaded all the plugins. Thus we can't use
    # the 'project' arg until we've already loaded them.
    getConfig(DEFAULT_SECTION)
    pygcam.log.configure()

    try:
        obj = GcamTool()
        args = obj.parser.parse_args()

        if args.main_project:
            getConfig(section=args.main_project, reload=True)
            pygcam.log.configure(force=True)

        obj.run(args=args)

    except Exception, e:
        print "%s failed: %s" % (PROGRAM, e)

        if getLevel() == 'DEBUG':
            import traceback
            traceback.print_exc()

        sys.exit(1)
