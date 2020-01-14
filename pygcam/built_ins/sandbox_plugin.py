#!/usr/bin/env python
"""
.. Workspace sub-command

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from __future__ import print_function
from ..subcommand import SubcommandABC, clean_help


def driver(args, tool):
    # lazy imports to avoid loading anything that's not used by gcamtool
    import os
    import subprocess

    from ..config import getParam, pathjoin
    from ..error import CommandlineError
    from ..scenarioSetup import createSandbox
    from ..log import getLogger
    from ..utils import removeTreeSafely

    _logger = getLogger(__name__)

    project = args.projectName or getParam('GCAM.DefaultProject')

    if not project:
        raise CommandlineError("sandbox: must specify project name or set config parameter GCAM.DefaultProject")

    if not (args.scenario or args.groupDir):
        raise CommandlineError("sandbox: must specify scenario and/or group name")

    sandboxProjectDir = getParam('GCAM.SandboxProjectDir')
    sandbox = pathjoin(sandboxProjectDir, args.groupDir, args.scenario)

    # handle ~ in pathname
    sandbox = pathjoin(sandbox, expanduser=True, abspath=True, normpath=True)

    if args.path:
        print(sandbox)

    execute = not args.noExecute

    if args.recreate:
        args.delete = args.create = True

    if args.delete:
        _logger.info('Removing ' + sandbox)
        try:
            if execute:
                if os.path.islink(sandbox):
                    os.remove(sandbox)
                else:
                    removeTreeSafely(sandbox)
            else:
                print("Would remove", sandbox)
        except Exception as e:
            _logger.warn("Can't remove '%s': %s" % (sandbox, e))

    if args.create:
        if execute:
            _logger.info('Creating ' + sandbox)
            createSandbox(sandbox)
        else:
            print("Would create", sandbox)

    if args.run:
        cmdStr = 'cd ' + sandbox + '; ' + args.run
        if execute:
            _logger.info(cmdStr)
            os.chdir(sandbox)
            subprocess.call(args.run, shell=True)
        else:
            print("Would run:", cmdStr)

class SandboxCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Perform operations on a sandbox.'''}
        super(SandboxCommand, self).__init__('sandbox', subparsers, kwargs, group='utils')

    def addArgs(self, parser):
        parser.add_argument('--create', action='store_true',
                            help=clean_help('''Create the identified sandbox. If used with --delete,
                            the deletion occurs first.'''))

        parser.add_argument('--delete', action='store_true',
                            help=clean_help('''Delete the identified sandbox' If used with --create, the
                            deletion occurs first.'''))

        parser.add_argument('--recreate', action='store_true',
                            help=clean_help('''Recreate the identified sandbox. Equivalent to using the
                            --delete and --create options together.'''))

        parser.add_argument('-g', '--groupDir', default='', metavar='NAME',
                            help=clean_help('''The name of the scenario group subdir'''))

        parser.add_argument('-n', '--noExecute', action='store_true',
                            help=clean_help('''Print the command that would be executed by --run, but
                            don't execute it.'''))

        parser.add_argument('-p', '--path', action='store_true',
                            help=clean_help('''Print the absolute path to the identified sandbox.'''))

        parser.add_argument('-r', '--run', metavar='CMD',
                            help=clean_help('''Run the given command in the identified sandbox.'''))

        parser.add_argument('-s', '--scenario', default='',
                            help=clean_help('''The scenario for the computed sandbox root.'''))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
