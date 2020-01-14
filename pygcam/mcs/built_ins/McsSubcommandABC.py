# Copyright (c) 2017  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from pygcam.subcommand import SubcommandABC, clean_help

class McsSubcommandABC(SubcommandABC):
    def __init__(self, name, subparsers, kwargs, label=None, guiSuppress=False):
        help = kwargs.get('help')
        prefix = '(MCS) '       # add prefix to all MCS subcommands if not already there
        if help:
            if not help.startswith(prefix):
                help = prefix + help
                
            kwargs['help'] = clean_help(help)

        super(McsSubcommandABC, self).__init__(name, subparsers, kwargs, group='mcs',
                                               label=None, guiSuppress=guiSuppress)
