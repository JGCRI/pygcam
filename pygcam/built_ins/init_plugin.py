'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2017 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
import os

from ..error import PygcamException, CommandlineError
from ..log import getLogger
from ..subcommand import SubcommandABC
from ..utils import mkdirs

_logger = getLogger(__name__)

class AbortInput(Exception):
    pass

Home = os.path.expanduser('~')

DefaultGcamDir    = Home + '/gcam/gcam-v4.3'
DefaultProjectDir = Home + '/gcam/projects'
DefaultSandboxDir = Home + '/gcam/sandboxes'

# TBD
def askYesNo(msg):
    value = None
    while value is None:
        value = raw_input(msg + ' (y/N)?')
        if value == '':
            value = 'n'

        if value not in 'yYnN':
            print("Please answer y or n.")
            value = None

    return value in 'yY'

def askPath(msg, default):
    path = None
    while path is None:
        path = raw_input(msg + ' (default=%s)?' % default)
        if path == '':
            path = default

        if not os.path.lexists(path):
            create = askYesNo("Path %s does not exist. Create it" % path)
            if not create:
                raise AbortInput()

            mkdirs(path)

    return path

def askString(msg, default):
    value = None
    while value is None:
        value = raw_input(msg + ' (default=%s)?' % default)
        if value == '':
            value = default

    return value

class InitCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Initialize key variables in the  ~/.pygcam.cfg
            configuration file. Values not provided on the command-line are
            requested interactively.'''}

        super(InitCommand, self).__init__('init', subparsers, kwargs, group='utils')

    def addArgs(self, parser):
        import os
        parser.add_argument('-P', '--defaultProject', type=str,
                            help='''Set the value of config var GCAM.DefaultProject to
                                    the given value.''')

        parser.add_argument('-g', '--gcamRoot', type=str,
                            help='''The top-level directory holding a GCAM v4.3
                            workspace. Sets config var GCAM.RootDir. Default is
                            "%s".''' % DefaultGcamDir)

        parser.add_argument('--overwrite', action='store_true',
                            help='''Overwrite an existing config file. (Actually, it makes
                            a backup first in ~/.pygcam.cfg-, but user is required to
                            confirm overwrite to avoid surprises.)''')

        parser.add_argument('-p', '--projectRoot', type=str,
                            help='''The directory in which to create pygcam project
                            directories. Sets config var GCAM.ProjectRoot. Default
                            is "%s".''' % DefaultProjectDir)

        parser.add_argument('-s', '--sandboxRoot', type=str,
                            help='''The directory in which to create pygcam project
                            directories. Sets config var GCAM.SandboxRoot. Default
                            is "%s".''' % DefaultSandboxDir)

        return parser

    def run(self, args, tool):
        from ..config import USR_CONFIG_FILE

        configPath = os.path.join(Home, USR_CONFIG_FILE)

        try:
            dfltProject = args.defaultProject or askString('Enter default project name?', 'ctax')
            gcamRoot    = args.gcamRoot       or askPath('GCAM root directory?', DefaultGcamDir)
            projectRoot = args.projectRoot    or askPath('Project root directory?', DefaultProjectDir)
            sandboxRoot = args.sandboxRoot    or askPath('Sandbox root directory?', DefaultSandboxDir)

            # make backup of configuration file if not exists
            if os.path.lexists(configPath):
                overwrite = args.overwrite or askYesNo('Overwrite %s' % configPath)
                if not overwrite:
                    raise AbortInput()

                backup = configPath + '-'
                os.rename(configPath, backup)
                print('Moved %s to %s' % (configPath, backup))

        except AbortInput as e:
            _logger.warn('Aborting "init" command')
            return

        # initialize configuration file

        print('Default project:', dfltProject)
        print('GCAM root:', gcamRoot)
        print('project root:', projectRoot)
        print('sandbox root:', sandboxRoot)

PluginClass = InitCommand
