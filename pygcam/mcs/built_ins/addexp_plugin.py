# Copyright (c) 2016-2021  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
#

from pygcam.log import getLogger
from .McsSubcommandABC import McsSubcommandABC

_logger = getLogger(__name__)

def driver(args, tool):
    '''
    Set up the base coremcs database. Must call startDb() before calling this.

    '''
    from ..Database import getDatabase

    db = getDatabase()
    expId = db.createExp(args.expName, parent=args.parent, description=args.description)
    _logger.debug("Added experiment '%s' with id=%d" % (args.expName, expId))


class AddExpCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Adds the named experiment to the database, with an optional description.'''}
        super(AddExpCommand, self).__init__('addexp', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('expName', type=str,
                            help='Add the named experiment to the database.')

        parser.add_argument('-d', '--description', type=str, required=False,
                            default='No description',
                            help='Add the named experiment to the database.')

        parser.add_argument('-p', '--parent', type=str, required=False,
                            default=None,
                            help='''Set the "parent" of this experiment. If adding a policy scenario,
                            the parent should be the name of the baseline. If adding a baseline, do not
                            specify a parent.''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
