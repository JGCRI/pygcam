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

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ..explorer import main
        main(args)

PluginClass = ExploreCommand
