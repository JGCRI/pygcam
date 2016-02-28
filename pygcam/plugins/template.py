from pygcam.plugin import PluginBase
from pygcam.config import DEFAULT_SECTION
from pygcam.log import getLogger

_logger = getLogger(__name__)

VERSION = "0.0"

class Plugin(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Short help text for main driver''',
                  'description' : '''Longer description for sub-command'''}

        super(Plugin, self).__init__('subcmd-name', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('-a', '--configSection', type=str, default=DEFAULT_SECTION,
                            help='''The name of the section in the config file to read from.
                            Defaults to %s''' % DEFAULT_SECTION)
        return parser


    def run(self, args):
        pass

# Alternative to naming class 'Plugin':
# PluginClass = MyPluginClassName
