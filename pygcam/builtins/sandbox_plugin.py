#!/usr/bin/env python
"""
.. Workspace sub-command

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""

from ..log import getLogger
from ..subcommand import SubcommandABC

_logger = getLogger(__name__)

def driver(args, tool):
    # lazy imports to avoid loading anything that's not used by gcamtool
    import os
    import shutil
    import subprocess

    from ..config import getParam
    from ..error import CommandlineError
    from ..setup import createSandbox

    project = args.configSection or getParam('GCAM.DefaultProject')

    if not project:
        raise CommandlineError("sandbox: must specify project name or set config parameter GCAM.DefaultProject")

    if not (args.scenario or args.groupDir):
        raise CommandlineError("sandbox: must specify scenario and/or group name")

    sandboxProjectDir = getParam('GCAM.SandboxProjectDir')
    sandbox = os.path.join(sandboxProjectDir, args.groupDir, args.scenario)

    sandbox = os.path.normpath(os.path.abspath(os.path.expanduser(sandbox)))     # handle ~ in pathname

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
                    shutil.rmtree(sandbox)
            else:
                print("Would remove %s" % sandbox)
        except Exception as e:
            _logger.warn("Can't remove '%s': %s" % (sandbox, e))

    if args.create:
        if execute:
            _logger.info('Creating ' + sandbox)
            createSandbox(sandbox)
        else:
            print("Would create %s" % sandbox)

    if args.run:
        cmdStr = 'cd ' + sandbox + '; ' + args.run
        if execute:
            _logger.info(cmdStr)
            os.chdir(sandbox)
            subprocess.call(args.run, shell=True)
        else:
            print("Would run: %s" % cmdStr)

class SandboxCommand(SubcommandABC):
    __version__ = '0.2'

    def __init__(self, subparsers):
        kwargs = {'help' : '''Perform operations on a sandbox.'''}
        super(SandboxCommand, self).__init__('sandbox', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('--create', action='store_true',
                            help='''Create the identified sandbox. If used with --delete,
                            the deletion occurs first.''')

        parser.add_argument('--delete', action='store_true',
                            help='''Delete the identified sandbox' If used with --create, the
                            deletion occurs first.''')

        parser.add_argument('--recreate', action='store_true',
                            help='''Recreate the identified sandbox. Equivalent to using the
                            --delete and --create options together.''')

        parser.add_argument('-g', '--groupDir', default='',
                            help='''The name of the scenario group subdir''')

        parser.add_argument('-n', '--noExecute', action='store_true',
                            help='''Print the command that would be executed by --run, but
                            don't execute it.''')

        parser.add_argument('-p', '--path', action='store_true',
                            help='''Print the absolute path to the identified sandbox.''')

        parser.add_argument('-r', '--run',
                            help='''Run the given command in the identified sandbox.''')

        parser.add_argument('-s', '--scenario', default='',
                            help='''The scenario for the computed sandbox root.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + self.__version__)

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
