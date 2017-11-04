'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2017 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
import itertools
import os
from six.moves import input

from ..subcommand import SubcommandABC

class AbortInput(Exception):
    pass


DefaultGcamDir    = '~/GCAM/gcam-v4.3'
DefaultProjectDir = '~/GCAM/projects'

def defaultSandboxDir(projectRoot):
    path = os.path.join(os.path.dirname(projectRoot), 'sandboxes')
    return path

Template = '''[DEFAULT]
GCAM.DefaultProject = {dfltProject}
GCAM.Root           = {gcamRoot}
GCAM.ProjectRoot    = {projectRoot}
GCAM.SandboxRoot    = {sandboxRoot}

[{dfltProject}]
GCAM.LogLevel = INFO
'''

def findGCAM():
    versions = ('v4.4', 'v4.3')
    dirs = ('~', '~/GCAM', '~/gcam')
    for v, d in itertools.product(versions, dirs):
        path = os.path.expanduser('%s/gcam-%s' % (d, v))
        if os.path.isdir(path):
            return path

    return None

def askYesNo(msg, default=None):
    default = default and default.lower()
    y = 'Y' if default == 'y' else 'y'
    n = 'N' if default == 'n' else 'n'
    prompt = msg + ' (%s/%s)? ' % (y, n)

    value = None
    while value is None:
        value = input(prompt).lower()
        if value == '' and default:
            return default == 'y'

        if value not in ('y', 'n', 'yes', 'no'):
            value = None

    return value in ('y', 'yes')

def askDir(msg, default=''):
    from ..utils import mkdirs

    path = None
    while not path:
        path = input(msg + ' (default=%s)? ' % default)
        if path == '':
            path = default

        path = os.path.expanduser(path)

        if path and not os.path.isdir(path):
            if os.path.lexists(path):
                print('Path %s exists, but is not a directory. Try again.' % path)
                path = ''
                continue

            create = askYesNo("Path %s does not exist. Create it" % path, default='y')
            if not create:
                path = ''
                continue

            mkdirs(path)
            print('Created %s' % path)

    return path

def askString(msg, default):
    value = None
    while value is None:
        value = input(msg + ' (default=%s)? ' % default)
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
        parser.add_argument('-c', '--create-project',    dest='createProject', action='store_true',
                            help='''Create the project structure for the given default project. If 
                            neither -c/--create-project nor -C/--no-create-project is specified, the
                            user is queried interactively.''')

        parser.add_argument('-C', '--no-create-project', dest='createProject', action='store_false')

        parser.set_defaults(createProject=None) # so that if no value is provide, we ask interactively


        parser.add_argument('-g', '--gcamDir',
                            help='''The directory holding a GCAM v4.3 or v4.4
                            workspace. Sets config var GCAM.RefWorkspace. By default,
                            looks for gcam-v4.4 (then v4.3) in ~, ~/GCAM, and ~/gcam, 
                            where "~" indicates your home directory.''')

        parser.add_argument('--overwrite', action='store_true',
                            help='''Overwrite an existing config file. (Makes
                            a backup first in ~/.pygcam.cfg~, but user is required to
                            confirm overwriting the file.)''')

        parser.add_argument('-P', '--defaultProject',
                            help='''Set the value of config var GCAM.DefaultProject to
                                    the given value.''')

        parser.add_argument('-p', '--projectDir',
                            help='''The directory in which to create pygcam project
                            directories. Sets config var GCAM.ProjectRoot. Default
                            is "%s".''' % DefaultProjectDir)

        parser.add_argument('-s', '--sandboxDir',
                            help='''The directory in which to create pygcam project
                            directories. Sets config var GCAM.SandboxRoot. Default
                            is "%s".''' % defaultSandboxDir(DefaultProjectDir))

        return parser

    def run(self, args, tool):
        from ..config import USR_CONFIG_FILE

        home = os.path.expanduser('~')
        configPath = os.path.join(home, USR_CONFIG_FILE)

        try:
            dfltProject = args.defaultProject or askString('Enter default project name?', 'ctax')
            gcamDir     = args.gcamDir or askDir('Where is GCAM installed?',
                                                 default=(findGCAM() or os.path.expanduser(DefaultGcamDir)))
            projectDir  = args.projectDir or askDir('Directory in which to create pygcam projects?',
                                                    default=os.path.expanduser(DefaultProjectDir))
            sandboxDir  = args.sandboxDir or askDir('Directory in which to create pygcam run-time sandboxes?',
                                                    default=defaultSandboxDir(projectDir))

            # make backup of configuration file if it exists and is not zero length
            if os.path.lexists(configPath) and os.stat(configPath).st_size > 0:
                overwrite = args.overwrite or askYesNo('Overwrite %s' % configPath, default='n')
                if not overwrite:
                    raise AbortInput()

                backup = configPath + '~'
                os.rename(configPath, backup)
                print('Moved %s to %s' % (configPath, backup))

        except AbortInput:
            print('Aborting "init" command')
            return

        # initialize configuration file
        text = Template.format(dfltProject=dfltProject, gcamRoot=gcamDir,
                               projectRoot=projectDir, sandboxRoot=sandboxDir)

        with open(configPath, 'w') as f:
            f.write(text)

        print("Created %s with contents:\n\n%s" % (configPath, text))

        createProj = args.createProject
        if createProj is None:
            createProj = askYesNo('Create the project structure for "%s"' % dfltProject, default='y')

        if createProj:
            newProjectDir = os.path.join(projectDir, dfltProject)
            overwrite = askYesNo('Overwrite existing project dir %s' % newProjectDir, 'n') if os.path.lexists(newProjectDir) else False

            argList = ['new', dfltProject, '-r', projectDir] + (['--overwrite'] if overwrite else [])

            args = tool.parser.parse_args(args=argList)
            tool.run(args=args)
            print('Created project "%s" in %s' % (dfltProject, newProjectDir))

PluginClass = InitCommand
