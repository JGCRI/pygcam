# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

# TBD: consider merging this into gensim for simplicity?

from pygcam.config import getParam, setParam
from pygcam.log import getLogger
from pygcam.subcommand import SubcommandABC

_logger = getLogger(__name__)


def driver(args, tool):
    '''
    Setup the app and run directories for a given user app.
    '''
    import os
    import shutil
    import pkgutil

    from pygcam.scenarioSetup import copyWorkspace
    import pygcam.utils as U

    from ..Database import getDatabase
    from ..error import PygcamMcsUserError
    from ..util import getRunQueryDir
    from ..XMLResultFile import XMLResultFile

    projectName = args.projectName
    if not projectName:
        _logger.error("The -P flag is required for the sub-command 'new'")
        return

    runRoot = args.runRoot or getParam('MCS.Root', section=projectName)

    if not runRoot:
        raise PygcamMcsUserError("RunRoot was not set on command line or in configuration file")

    # Create the run dir, if needed
    U.mkdirs(runRoot)

    # TBD: replace with call from pygcam.utils?
    def copyDir(srcDir, dstDir):
        '''
        Recursively copy srcDir to dstDir, removing dstDir first in case it's a symlink.
        '''
        if os.path.isdir(dstDir):
            _logger.debug('Removing %s', dstDir)
            shutil.rmtree(dstDir)

        _logger.debug('Copying %s to %s', srcDir, dstDir)
        shutil.copytree(srcDir, dstDir, symlinks=False, ignore=shutil.ignore_patterns('.*'))

    # TBD: need option to write this out as with the "gt new" command
    setParam('MCS.RunDir', os.path.join(runRoot, projectName), section=projectName)

    db = getDatabase()   # ensures database initialization

    srcDir = getParam('GCAM.RefWorkspace')
    dstDir = getParam('MCS.RunWorkspace')

    copyWorkspace(dstDir, refWorkspace=srcDir, forceCreate=True, mcsMode=True)

    # TBD: Verify that this is required (only use of this config var, too.)
    if False:
        runQueryDir = getRunQueryDir()
        userQueryDir = getParam('MCS.UserQueryDir')
        copyDir(userQueryDir, runQueryDir)

    XMLResultFile.addOutputs()

    # Load SQL script to create convenient views
    text = pkgutil.get_data('pygcam', 'mcs/etc/views.sql')
    db.executeScript(text=text)


class NewSimCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '(MCS) Initialize and create the directory structure for a Monte Carlo simulation.'}
        super(NewSimCommand, self).__init__('newsim', subparsers, kwargs)

    def addArgs(self, parser):
        runRoot = getParam('MCS.Root')
        parser.add_argument('-r', '--runRoot', default=None,
                            help='''Root of the run-time directory for running user programs. Defaults to
                            value of config parameter MCS.Root (currently %s)''' % runRoot)

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
