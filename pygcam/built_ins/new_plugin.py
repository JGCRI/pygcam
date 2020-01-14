#!/usr/bin/env python
"""
.. "new" sub-command (creates a new project)

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from datetime import datetime

from ..subcommand import SubcommandABC, clean_help

def driver(args, tool):
    import os
    import re
    import shutil
    from ..config import getParam, USR_CONFIG_FILE, pathjoin, unixPath
    from ..utils import mkdirs, copyResource, getResource
    from ..error import CommandlineError
    from ..log import getLogger

    _logger = getLogger(__name__)

    projectName = args.name
    projectRoot = unixPath(args.root, abspath=True) if args.root else getParam('GCAM.ProjectRoot')
    projectDir  = pathjoin(projectRoot, projectName)
    overwrite   = args.overwrite

    try:
        os.chdir(projectRoot)
    except Exception as e:
        raise CommandlineError("Can't change dir to '%s': %s" % (projectRoot, e))

    try:
        mkdirs(projectDir)
    except OSError as e:
        if e.errno == 17:   # already exists; ignore
            pass
    except Exception as e:
        raise CommandlineError("Can't create to '%s': %s" % (projectDir, e))

    try:
        os.chdir(projectDir)
    except Exception as e:
        raise CommandlineError("Can't chdir to '%s': %s" % (projectDir, e))

    dirsToCreate  = ['etc', 'queries', 'plugins', 'xmlsrc']
    initsToCreate = ['__init__.py', 'xmlsrc/__init__.py']

    for name in dirsToCreate:
        _logger.debug('Creating %s/%s/', projectDir, name)
        mkdirs(name)

    for name in initsToCreate:  # create empty files
        _logger.debug('Creating %s/%s', projectDir, name)
        open(name, 'a').close() # append just in case it exists already

    etcDir = 'etc'
    exampleDir = pathjoin(etcDir, 'examples')
    projectEtc = pathjoin(projectDir, 'etc')

    # Provide example XML files and instructions by extracting these
    # as resources from the pygcam package.
    filesToCopy = ['project.xml', 'protection.xml',  'rewriteSets.xml', 'scenarios.xml',
                   'scenarios-iterator.xml', 'project2.xml', 'Instructions.txt',
                   'project-schema.xsd', 'protection-schema.xsd', 'queries-schema.xsd', 'RES-schema.xsd',
                   'rewriteSets-schema.xsd', 'scenarios-schema.xsd', 'comment.xsd','conditional.xsd']

    for filename in filesToCopy:
        srcDir = etcDir if filename.endswith('.xsd') else exampleDir
        src = pathjoin(srcDir, filename)
        dst = pathjoin(projectEtc, filename)
        _logger.debug('Creating %s', dst)

        if filename == 'project.xml':
            # For project.xml, we change the project name to the name given by user
            if not overwrite and os.path.lexists(dst):
                raise CommandlineError("Refusing to overwrite '%s'" % unixPath(dst, abspath=True))

            oldText = getResource(src)
            newText = re.sub('<project name="(\w*)">', '<project name="%s">' % projectName, oldText)
            with open(dst, 'w') as fp:
                fp.write(newText)
        else:
            copyResource(src, dst, overwrite=overwrite)

    if args.addToConfig:
        _logger.debug('Adding [%s] to %s', projectName, USR_CONFIG_FILE)

        cfgFile = pathjoin(getParam('Home'), USR_CONFIG_FILE)

        # Create backup copy of config file
        shutil.copyfile(cfgFile, cfgFile + '~')

        # If projectRoot defaulted to the value of GCAM.ProjectRoot, reference
        # the variable; otherwise use the pathname verbatim.
        dirName = projectDir if args.root else '%(GCAM.ProjectRoot)s/' + projectName

        # Add a project section to the .pygcam.cfg file
        with open(cfgFile, 'a') as f:
            f.write('\n[%s]\n' % projectName)
            f.write('# Added by "new" sub-command %s\n' % datetime.now().ctime())
            f.write('GCAM.ProjectDir = %s\n' % dirName)
            f.write('GCAM.ScenarioSetupFile = %(GCAM.ProjectDir)s/etc/scenarios.xml\n')
            f.write('GCAM.RewriteSetsFile   = %(GCAM.ProjectDir)s/etc/rewriteSets.xml\n')


class NewProjectCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Create the structure and files required for a new pygcam project.'''}
        super(NewProjectCommand, self).__init__('new', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        # Positional args
        parser.add_argument('name',
                            help=clean_help('''Create the structure for the named project, and copy example
                            XML files into the "etc" directory.'''))

        parser.add_argument('-c', '--addToConfig', action='store_true',
                            help=clean_help('''Add a section for the new project to $HOME/.pygcam.cfg after
                            making a backup of the file in $HOME/.pygcam.cfg~'''))

        parser.add_argument('--overwrite', action='store_true',
                            help=clean_help('''If files that are to be copied to the project directory exist, overwrite them.
                            By default, existing files are not overwritten.'''))

        parser.add_argument('-r', '--projectRoot', dest='root', metavar='PATH',
                            help=clean_help('''The directory in which to create a subdirectory for the named
                            project. Default is the value of config variable GCAM.ProjectRoot'''))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
