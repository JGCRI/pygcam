#!/usr/bin/env python
"""
.. "new" sub-command (creates a new project)

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
import os
import shutil
from .config import getParam, USR_CONFIG_FILE
from .utils import mkdirs, copyResource
from .error import CommandlineError
from .subcommand import SubcommandABC
from .log import getLogger

_logger = getLogger(__name__)


def driver(args, tool):
    projectName = args.name
    projectRoot = args.root or getParam('GCAM.ProjectRoot')
    projectDir  = os.path.join(projectRoot, projectName)

    try:
        os.chdir(projectRoot)
    except Exception as e:
        raise CommandlineError("Can't change dir to '%s': %s" % (projectRoot, e))

    try:
        os.mkdir(projectDir)
    except Exception as e:
        raise CommandlineError("Can't create to '%s': %s" % (projectDir, e))

    try:
        os.chdir(projectDir)
    except Exception as e:
        raise CommandlineError("Can't chdir to '%s': %s" % (projectDir, e))

    dirsToCreate  = ['etc', 'queries', 'plugins', 'xmlsrc/baseline/xml']
    filesToCreate = ['__init__.py', 'xmlsrc/__init__.py']

    for name in dirsToCreate:
        _logger.debug('Creating %s/%s/', projectDir, name)
        mkdirs(name)

    for name in filesToCreate:  # create empty files
        _logger.debug('Creating %s/%s', projectDir, name)
        open(name, 'a').close() # append just in case it exists already

    # Copy scenarios.py template to serve as a starting point
    dst = 'xmlsrc/scenarios.py'
    _logger.debug('Creating %s/%s', projectDir, dst)
    copyResource('etc/scenarios-template.py', dst, overwrite=False)

    # Provide example XML files
    xmlFilesToCopy = ['rewriteSets', 'project', 'protection', 'queries']
    for name in xmlFilesToCopy:
        src = 'etc/%s-example.xml' % name       # e.g., pygcam/etc/project-example.xml
        dst = 'etc/%s.xml' % name               # e.g., <projectDir>/etc/project.xml
        _logger.debug('Creating %s/%s', projectDir, dst)
        copyResource(src, dst, overwrite=False)

    if args.addToConfig:
        _logger.debug('Adding [%s] to %s', projectName, USR_CONFIG_FILE)

        cfgFile = os.path.join(getParam('Home'), USR_CONFIG_FILE)

        # Create backup copy of config file
        shutil.copyfile(cfgFile, cfgFile + '~')

        # If projectRoot defaulted to the value of GCAM.ProjectRoot, reference
        # the variable; otherwise use the pathname verbatim.
        dirName = projectDir if args.root else '%(GCAM.ProjectRoot)s/' + projectName

        # Add a project section to the .pygcam.cfg file
        with open(cfgFile, 'a') as f:
            f.write('\n[%s]\n' % projectName)
            f.write('# Added by gt new\n')
            f.write('GCAM.ProjectDir = %s\n' % dirName)


class NewProjectCommand(SubcommandABC):
    __version__ = '0.1'

    def __init__(self, subparsers):
        kwargs = {'help' : '''Create the structure and files required for a new pygcam project.'''}
        super(NewProjectCommand, self).__init__('new', subparsers, kwargs)

    def addArgs(self, parser):
        # Positional args
        parser.add_argument('name',
                            help='''Create the structure for the named project.''')

        parser.add_argument('-c', '--addToConfig', action='store_true',
                            help='''Add a section for the new project to $HOME/.pygcam.cfg after
                            making a backup of the file in $HOME/.pygcam.cfg~''')

        parser.add_argument('-r', '--projectRoot', dest='root', metavar='PATH',
                            help='''The directory in which to create the a subdirectory for the named project.
                            Default is the value of config variable GCAM.ProjectRoot''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + self.__version__)

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
