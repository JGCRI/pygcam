'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2017 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
import itertools
import os
from six.moves import input

from ..config import getHomeDir
from ..subcommand import SubcommandABC

class AbortInput(Exception):
    pass

DefaultProjectDir = '~/GCAM/projects'

def defaultSandboxDir(projectRoot):
    from ..utils import pathjoin
    path = pathjoin(os.path.dirname(projectRoot), 'sandboxes')
    return path

Template = '''[DEFAULT]
GCAM.DefaultProject  = {dfltProject}
GCAM.RefWorkspace    = {gcamDir}
GCAM.ProjectRoot     = {projectRoot}
GCAM.SandboxRoot     = {sandboxRoot}
GCAM.RewriteSetsFile = %(GCAM.ProjectDir)s/etc/rewriteSets.xml

[{dfltProject}]
# Set GCAM.LogLevel to DEBUG for more diagnostic messages 
# or to WARN, ERROR, or FATAL for progressively less info. 
GCAM.LogLevel = INFO

# Setup generated config files to not write large extraneous 
# output files. Move these statements to the [DEFAULT] section 
# if you want this to be the default for all projects.
GCAM.WriteDebugFile     = False
GCAM.WriteXmlOutputFile = False
'''

def expandTilde(path):
    """
    Similar to os.path.expanduser() but uses our getHomeDir() function,
    which produces consistent results regards of whether user is running
    a standard Windows command window or a Cygwin bash shell. Also, we
    have no need to expand '~user', just '~'.
    """
    from ..utils import unixPath

    if path.startswith('~/'):
        path = getHomeDir() + path[1:]
    return unixPath(path)

def findGCAM():
    import platform
    from ..utils import unixPath

    home = getHomeDir()

    versions = ['gcam-v4.4', 'gcam-v4.3']
    dirs = [home, home + '/GCAM', home + '/gcam']

    system = platform.system()
    if system == 'Darwin':
        release = 'gcam-v4.4-Mac-Release-Package'
    elif system == 'Windows':
        release = 'gcam-v4.4-Windows-Release-Package'
    else:
        release = None

    if release:
        versions.insert(0, release)

    for v, d in itertools.product(versions, dirs):
        path = '%s/%s' % (d, v)
        if os.path.isdir(path):
            return unixPath(path)

    return ''

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


def askString(msg, default):
    value = None
    while value is None:
        value = input(msg + ' (default=%s): ' % default)
        value = value.strip()
        if value == '':
            value = default

    return value

def askDir(msg, default=''):
    from prompt_toolkit import prompt
    from prompt_toolkit.contrib.completers import PathCompleter
    from ..utils import mkdirs

    is_cygwin = isCygwin()

    completer = PathCompleter(only_directories=True, expanduser=True)
    msg     = unicode(msg) + u' '
    default = unicode(default)
    path = None

    while not path:
        # prompt_toolkit doesn't work in cygwin terminal
        path = askString(msg, default) if is_cygwin else prompt(msg, default=default, completer=completer)
        path = expandTilde(path)

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

def isCygwin():
    import sys, platform

    return (platform.system() == 'Windows'
            and os.environ.get('SHELL') == '/bin/bash'
            and not sys.stdin.isatty())

def rerunForCygwin(args):
    """
    CygWin buffers stdin unless PYTHONUNBUFFERED is set, so we
    set it and re-run the 'gt init' command with the given args.
    A bit of an unfortunate work-around, but it works.
    """
    import subprocess as subp

    os.environ['PYTHONUNBUFFERED'] = '1'

    argList = ['gt', 'init']

    if args.createProject == True:
        argList.append('-c')
    elif args.createProject == False:
        argList.append('-C')

    if args.overwrite:
        argList.append('--overwrite')

    if args.gcamDir:
        argList += ['-g', args.gcamDir]

    if args.defaultProject:
        argList += ['-P', args.defaultProject]

    if args.projectDir:
        argList += ['-p', args.projectDir]

    if args.sandboxDir:
        argList += ['-s', args.sandboxDir]

    command = ' '.join(argList)
    # print('Re-running for cygwin: %s' % command)
    subp.call(argList, shell=False)


class InitCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Initialize key variables in the  ~/.pygcam.cfg
            configuration file. Values not provided on the command-line are
            requested interactively.'''}

        super(InitCommand, self).__init__('init', subparsers, kwargs, group='utils')

    def addArgs(self, parser):
        group = parser.add_mutually_exclusive_group()

        group.add_argument('-c', '--create-project',    dest='createProject', action='store_true',
                            default=None,
                            help='''Create the project structure for the given default project. If 
                            neither -c/--create-project nor -C/--no-create-project is specified, the
                            user is queried interactively.''')

        group.add_argument('-C', '--no-create-project', dest='noCreateProject', action='store_true',
                            default=None,
                           help='''Do not create the project structure for the given default project.
                           Mutually exclusive with -c / --create-project option.''')

        parser.add_argument('-g', '--gcamDir',
                            help='''The directory that is a GCAM v4.3 or v4.4
                            workspace. Sets config var GCAM.RefWorkspace. By default,
                            looks for gcam-v4.4 (then v4.3) in ~, ~/GCAM, and ~/gcam, 
                            where "~" indicates your home directory.''')

        parser.add_argument('--overwrite', action='store_true',
                            help='''Overwrite an existing config file. (Makes
                            a backup first in ~/.pygcam.cfg~.)''')

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
        from ..utils import pathjoin, deleteFile, mkdirs

        # Detect cygwin terminals, which quite lamely cannot handle interactive input
        if (isCygwin() and not os.environ.get('PYTHONUNBUFFERED')):
            rerunForCygwin(args)
            return

        configPath = pathjoin(getHomeDir(), USR_CONFIG_FILE)

        try:
            dfltProject = args.defaultProject or askString('Default project name?', 'tutorial')
            gcamDir     = args.gcamDir or askDir('Where is GCAM installed?', default=findGCAM())
            projectDir  = args.projectDir or askDir('Directory in which to create pygcam projects?',
                                                    default=expandTilde(DefaultProjectDir))
            sandboxDir  = args.sandboxDir or askDir('Directory in which to create pygcam run-time sandboxes?',
                                                    default=defaultSandboxDir(projectDir))

            # make backup of configuration file if it exists and is not zero length
            if os.path.lexists(configPath) and os.stat(configPath).st_size > 0:
                overwrite = args.overwrite or askYesNo('Overwrite %s' % configPath, default='n')
                if not overwrite:
                    raise AbortInput("Quitting to avoid overwriting %s" % configPath)

                backup = configPath + '~'
                deleteFile(backup)
                os.rename(configPath, backup)
                print('Moved %s to %s' % (configPath, backup))

        except AbortInput as e:
            print(e)
            return

        # initialize configuration file
        text = Template.format(dfltProject=dfltProject, gcamDir=gcamDir,
                               projectRoot=projectDir, sandboxRoot=sandboxDir)

        with open(configPath, 'w') as f:
            f.write(text)

        print("Created %s with contents:\n\n%s" % (configPath, text))

        for path in (projectDir, sandboxDir):
            if not os.path.isdir(path):
                mkdirs(path)

        # These args default to None so we can test for explicit settings
        createProj = True if args.createProject == True else (False if args.noCreateProject == True else None)
        if createProj is None:
            createProj = askYesNo('Create the project structure for "%s"' % dfltProject, default='y')

        if createProj:
            newProjectDir = pathjoin(projectDir, dfltProject)
            overwrite = askYesNo('Overwrite existing project dir %s' % newProjectDir, 'n') if os.path.lexists(newProjectDir) else False

            argList = ['new', dfltProject, '-r', projectDir] + (['--overwrite'] if overwrite else [])

            args = tool.parser.parse_args(args=argList)
            tool.run(args=args)
            print('Created project "%s" in %s' % (dfltProject, newProjectDir))

PluginClass = InitCommand
