'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2017 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import itertools
import os

from ..config import getConfig, getHomeDir, pathjoin, unixPath, mkdirs, USR_CONFIG_FILE
from ..subcommand import SubcommandABC, clean_help

class AbortInput(Exception):
    pass

DefaultProjectDir = '~/GCAM/projects'

def defaultSandboxDir(projectRoot):
    path = pathjoin(os.path.dirname(projectRoot), 'sandboxes')
    return path

Template = '''[DEFAULT]
GCAM.DefaultProject  = {dfltProject}
GCAM.RefWorkspace    = {gcamDir}
GCAM.VersionNumber   = {versionNum}
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
    if path.startswith('~/'):
        path = getHomeDir() + path[1:]
    return unixPath(path)

def findGCAM():
    import platform

    home = getHomeDir()

    versions = ['gcam-v' + num for num in ('6.0', '5.4', '5.3', '5.2')]
    dirs = [home, home + '/GCAM', home + '/gcam', home + '/Documents/GCAM', home + '/Documents/gcam']

    system = platform.system()
    if system == 'Darwin':
        pkgName = '-Mac-Release-Package'
    elif system == 'Windows':
        pkgName = '-Windows-Release-Package'
    else:
        pkgName = None

    all = sorted([version + pkgName for version in versions] + versions, reverse=True) if pkgName else versions

    for v, d in itertools.product(all, dirs):
        path = f'{d}/{v}'
        if os.path.isdir(path):
            return unixPath(path)

    return ''

def askYesNo(msg, default=None):
    default = default and default.lower()
    y = 'Y' if default == 'y' else 'y'
    n = 'N' if default == 'n' else 'n'
    prompt = msg + f' ({y}/{n})? '

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
        value = input(msg + f' (default={default}): ')
        value = value.strip()
        if value == '':
            value = default

    return value

def askDir(msg, default=''):
    from prompt_toolkit import prompt
    try:
        # prompt_toolkit 1
        from prompt_toolkit.contrib.completers import PathCompleter
    except Exception:
        # prompt_toolkit 2
        from prompt_toolkit.completion import PathCompleter

    is_cygwin = isCygwin()

    completer = PathCompleter(only_directories=True, expanduser=True)
    msg += ' '
    path = None

    while not path:
        # prompt_toolkit doesn't work in cygwin terminal or in PyCharm debugger
        # path = askString(msg, default) if is_cygwin else prompt(msg, default=default, completer=completer)
        if is_cygwin:
            path = askString(msg, default)
        else:
            try:
                path = prompt(msg, default=default, completer=completer)
            except AssertionError:  # stdout.isatty() fails in PyCharm debugger
                path = askString(msg, default)

        path = expandTilde(path)

        if path and not os.path.isdir(path):
            if os.path.lexists(path):
                print(f'Path {path} exists, but is not a directory. Try again.')
                path = ''
                continue

            create = askYesNo(f"Path {path} does not exist. Create it", default='y')
            if not create:
                path = ''
                continue

            mkdirs(path)
            print('Created', path)

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
    from ..utils import shellCommand

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

    shellCommand(argList, shell=False)


class InitCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : clean_help('''Initialize key variables in the  ~/.pygcam.cfg
            configuration file. Values not provided on the command-line are
            requested interactively.''')}

        super(InitCommand, self).__init__('init', subparsers, kwargs, group='utils')

    def addArgs(self, parser):
        group = parser.add_mutually_exclusive_group()

        group.add_argument('-c', '--create-project',    dest='createProject', action='store_true',
                            default=None,
                            help=clean_help('''Create the project structure for the given default project. If 
                            neither -c/--create-project nor -C/--no-create-project is specified, the
                            user is queried interactively.'''))

        group.add_argument('-C', '--no-create-project', dest='noCreateProject', action='store_true',
                            default=None,
                           help=clean_help('''Do not create the project structure for the given default project.
                           Mutually exclusive with -c / --create-project option.'''))

        parser.add_argument('-g', '--gcamDir',
                            help=clean_help('''The directory that is a GCAM v5.x or 4.x
                            workspace. Sets config var GCAM.RefWorkspace. By default,
                            looks for gcam-v5.4 (then known older versions) in ~, ~/GCAM, and ~/gcam,
                            ~/Documents/GCAM, and ~/Documents/gcam,  
                            where "~" indicates your home directory.'''))

        parser.add_argument('--overwrite', action='store_true',
                            help=clean_help('''Overwrite an existing config file. (Makes
                            a backup first in ~/.pygcam.cfg~).'''))

        parser.add_argument('-P', '--defaultProject',
                            help=clean_help('''Set the value of config var GCAM.DefaultProject to
                                    the given value.'''))

        parser.add_argument('-p', '--projectDir',
                            help=clean_help('''The directory in which to create pygcam project
                            directories. Sets config var GCAM.ProjectRoot. Default
                            is "%s".''' % DefaultProjectDir))

        parser.add_argument('-s', '--sandboxDir',
                            help=clean_help('''The directory in which to create pygcam project
                            directories. Sets config var GCAM.SandboxRoot. Default
                            is "%s".''' % defaultSandboxDir(DefaultProjectDir)))

        return parser

    def run(self, args, tool):
        from ..file_utils import deleteFile
        from ..gcam import getGcamVersion

        # Detect cygwin terminals, which quite lamely cannot handle interactive input
        if (isCygwin() and not os.environ.get('PYTHONUNBUFFERED')):
            rerunForCygwin(args)
            return

        configPath = pathjoin(getHomeDir(), USR_CONFIG_FILE)

        try:
            dfltProject = args.defaultProject or askString('Default project name?', 'ctax')
            gcamDir     = args.gcamDir or askDir('Where is GCAM installed?', default=findGCAM())

            projectDir  = args.projectDir or askDir('Directory in which to create pygcam projects?',
                                                    default=expandTilde(DefaultProjectDir))

            sandboxDir  = args.sandboxDir or askDir('Directory in which to create pygcam run-time sandboxes?',
                                                    default=defaultSandboxDir(str(projectDir)))

            # make backup of configuration file if it exists and is not zero length
            if os.path.lexists(configPath) and os.stat(configPath).st_size > 0:
                overwrite = args.overwrite or askYesNo(f'Overwrite {configPath}', default='n')
                if not overwrite:
                    raise AbortInput(f"Quitting to avoid overwriting {configPath}")

                backup = configPath + '~'
                deleteFile(backup)
                os.rename(configPath, backup)
                print(f'Moved {configPath} to {backup}')

        except AbortInput as e:
            print(e)
            return

        except Exception as e:
            raise(e)

        # initialize configuration file
        versionNum = getGcamVersion(pathjoin(gcamDir, 'exe'), preferPath=True)
        text = Template.format(dfltProject=dfltProject, gcamDir=gcamDir, versionNum=versionNum,
                               projectRoot=projectDir, sandboxRoot=sandboxDir)

        with open(configPath, 'w') as f:
            f.write(text)

        print(f"Created {configPath} with contents:\n\n{text}")

        # reload the config info in case we use it below
        getConfig(reload=False)

        for path in (projectDir, sandboxDir):
            if not os.path.isdir(path):
                mkdirs(path)

        # These args default to None, so we can test for explicit settings
        createProj = True if args.createProject is True else (False if args.noCreateProject is True else None)
        if createProj is None:
            createProj = askYesNo(f'Create the project structure for "{dfltProject}"', default='y')

        if createProj:
            newProjectDir = pathjoin(projectDir, dfltProject)
            overwrite = askYesNo(f'Overwrite existing project dir {newProjectDir}', 'n') if os.path.lexists(newProjectDir) else False

            argList = ['new', dfltProject, '-r', projectDir] + (['--overwrite'] if overwrite else [])

            args = tool.parser.parse_args(args=argList)
            tool.run(args=args)
            print(f'Created project "{dfltProject}" in {newProjectDir}')

PluginClass = InitCommand
