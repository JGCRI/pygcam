from pygcam.subcommand import SubcommandABC
from pygcam.log import getLogger

_logger = getLogger(__name__)

VERSION = "0.0"

class MyNewCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Short help text for main driver''',
                  'description' : '''Longer description for sub-command'''}

        super(MyNewCommand, self).__init__('subcmd-name', subparsers, kwargs)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('-n', '--number', type=int, default=0,
                            help='''A number to demonstrate a command line arg''')
        return parser

    def run(self, args, tool):
        pass

# Alternative to naming class 'Plugin' is to assign the class to PluginClass
PluginClass = MyNewCommand
