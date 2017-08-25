# Copyright (c) 2017  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from pygcam.subcommand import SubcommandABC

class McsSubcommandABC(SubcommandABC):
    def __init__(self, name, subparsers, kwargs):
        help = kwargs.get('help')
        prefix = '(MCS) '       # add prefix to all MCS subcommands
        if help and not help.startswith(prefix):
            kwargs['help'] = prefix + help

        super(McsSubcommandABC, self).__init__(name, subparsers, kwargs, group='mcs')
