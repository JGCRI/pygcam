# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from pygcam.log import getLogger
from .McsSubcommandABC import McsSubcommandABC, clean_help

_logger = getLogger(__name__)

# TBD: Database initialization now occurs in getDatabase() if needed. This
# TBD: command is semantically more like "delsim", which both deletes and
# TBD: recreates the database schema and removes the simulation directory

def driver(args, tool):
    import os
    '''
    Set up the SQL database. Must call startDb() before calling this.

    '''
    import shutil

    from pygcam.config import getParam
    from ..Database import getDatabase
    from ..error import PygcamMcsSystemError

    if args.deleteSims:
        # Remove the whole sims dir and remake it
        runSimsDir = getParam('MCS.RunSimsDir')
        if os.path.exists(runSimsDir):
            try:
                shutil.rmtree(runSimsDir)
                os.mkdir(runSimsDir)
            except Exception as e:
                raise PygcamMcsSystemError('Failed to recreate sim dir %s: %s' % (runSimsDir, e))

    db = getDatabase()

    # reinitialize the db
    db.initDb(args=args)

    if not (args.empty):
        from ..XMLResultFile import XMLResultFile
        XMLResultFile.addOutputs()


class DelSimCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Initialize the database for the given user application. 
            This is done automatically by the sub-command "new" and should be used only to 
            recreate the database from scratch.'''}
        super(DelSimCommand, self).__init__('delsim', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('-r', '--deleteSims', action='store_true', default=False,
                            help=clean_help('Delete all simulations from the run directory.'))

        parser.add_argument('-e', '--empty', action='store_true', default=False,
                            help=clean_help('''Create the database schema but don't add any data.
                            Useful when restoring from a dumped database.'''))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
