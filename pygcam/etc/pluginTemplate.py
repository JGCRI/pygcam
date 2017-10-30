from pygcam.subcommand import SubcommandABC
from pygcam.log import getLogger

_logger = getLogger(__name__)

class MyNewCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Short help text for main driver''',
                  'description' : '''Longer description for sub-command'''}

        # The first argument is the name of the new sub-command
        super(MyNewCommand, self).__init__('subCmdName', subparsers, kwargs)

    def addArgs(self):
        '''
        Process the command-line arguments for this sub-command
        '''
        parser = self.parser

        parser.add_argument('-n', '--number', type=int, default=0,
                            help='''A number to demonstrate a command line arg.
                            Replace as needed with your own plugin's args.''')

        return parser

    def run(self, args, tool):
        '''
        Implement the sub-command here. "args" is an `argparse.Namespace` instance
        holding the parsed command-line arguments, and "tool" is a reference to
        the running GcamTool instance.
        '''
        pass

# An alternative to naming the class 'Plugin' is to assign the class to PluginClass
PluginClass = MyNewCommand
