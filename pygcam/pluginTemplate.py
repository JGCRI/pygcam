from pygcam.subcommand import SubcommandABC
from pygcam.log import getLogger

_logger = getLogger(__name__)

__version__ = "0.0"

class MyNewCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Short help text for main driver''',
                  'description' : '''Longer description for sub-command'''}

        # The first argument is the name of the new sub-command
        super(MyNewCommand, self).__init__('XXX', subparsers, kwargs)

    # process command-line arguments for this sub-command
    def addArgs(self):
        parser = self.parser

        parser.add_argument('-n', '--number', type=int, default=0,
                            help='''A number to demonstrate a command line arg''')

        parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)

        return parser

    # implement the sub-command
    def run(self, args, tool):
        pass

# An alternative to naming the class 'Plugin' is to assign the class to PluginClass
PluginClass = MyNewCommand
