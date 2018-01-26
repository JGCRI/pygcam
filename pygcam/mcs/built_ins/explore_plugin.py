# Copyright (c) 2017 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from .McsSubcommandABC import McsSubcommandABC

class ExploreCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Run the MCS "explorer" app in dash.'''}
        super(ExploreCommand, self).__init__('explore', subparsers, kwargs,
                                             guiSuppress=True)  # explore runs its own dash server, separate from "gui"

    def addArgs(self, parser):
        parser.add_argument('-d', '--debug', action='store_true',
                            help='''Enable debug mode in the dash server''')
        parser.add_argument('-H', '--host', default='127.0.0.1',
                            help='''Set the host address to serve the application on. Default is localhost (127.0.0.1).''')
        parser.add_argument('-P', '--port', default=8050, type=int,
                            help='''Set the port to serve the application on. Default is 8050.''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ..explorer import main
        main(args)

PluginClass = ExploreCommand
