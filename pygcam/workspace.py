#!/usr/bin/env python
"""
.. Workspace sub-command

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
import os
import shutil
import subprocess
from .config import getParam
from .error import CommandlineError
from .subcommand import SubcommandABC
from .log import getLogger
from .runGCAM import setupWorkspace

_logger = getLogger(__name__)

def driver(args, tool):
    project = args.configSection or getParam('GCAM.DefaultProject')

    if not project:
        raise CommandlineError("ws: must specify project name")

    workspace = getParam('GCAM.SandboxDir')
    if args.scenario:
        workspace += '/' + args.scenario

    workspace = os.path.normpath(os.path.abspath(os.path.expanduser(workspace)))     # handle ~ in pathname

    if args.path:
        print(workspace)

    if args.delete:
        _logger.info('removing ' + workspace)
        try:
            if not args.noExecute:
                if os.path.islink(workspace):
                    os.remove(workspace)
                else:
                    shutil.rmtree(workspace)
        except Exception as e:
            _logger.warn("Can't remove '%s': %s" % (workspace, e))

    if args.create:
        setupWorkspace(workspace)

    if args.run:
        cmdStr = 'cd ' + workspace + '; ' + args.run
        if args.noExecute:
            print cmdStr
        else:
            _logger.info(cmdStr)
            os.chdir(workspace)
            subprocess.call(args.run, shell=True)


class WorkspaceCommand(SubcommandABC):
    __version__ = '0.2'

    def __init__(self, subparsers):
        kwargs = {'help' : '''Perform operations on a workspace.'''}
        super(WorkspaceCommand, self).__init__('ws', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('--create', action='store_true',
                            help='''Create the identified workspace. If used with --delete,
                            the deletion occurs first.''')

        parser.add_argument('--delete', action='store_true',
                            help='''Delete the identified workspace' If used with --create, the
                            deletion occurs first.''')

        parser.add_argument('-n', '--noExecute', action='store_true',
                            help='''Print the command that would be executed by --run, but
                            don't execute it.''')

        parser.add_argument('-p', '--path', action='store_true',
                            help='''Print the absolute path to the identified workspace.''')

        parser.add_argument('-r', '--run',
                            help='''Run the given command in the identified workspace.''')

        parser.add_argument('-s', '--scenario', default="",
                            help='''The scenario for the computed workspace root.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + self.__version__)

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
