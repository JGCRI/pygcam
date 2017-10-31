'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
from ..subcommand import SubcommandABC
from ..log import getLogger

_logger = getLogger(__name__)


class MCSCommand(SubcommandABC):

    def __init__(self, subparsers, showTerminal=True):
        kwargs = {'help' : '''Enable or disable pygcam Monte Carlo Simulation sub-commands.'''}

        super(MCSCommand, self).__init__('mcs', subparsers, kwargs, group='utils', label='MCS',
                                         showTerminal=showTerminal)

    def addArgs(self, parser):
        parser.add_argument('mode', choices=['on', 'off', 'status'],
                            help='''Turn MCS mode on or off, or report current setting''')
        return parser

    def run(self, args, tool):
        import os
        from ..config import mcsSentinelFile, usingMCS

        sentinelFile = mcsSentinelFile()

        if args.mode == 'on':
            # Touch the file
            open(sentinelFile, 'w').close()

        elif args.mode == 'off':
            # remove it if it exists
            try:
                os.remove(sentinelFile)
            except:
                pass
        else:
            # Report current mode
            mode = 'on' if usingMCS() else 'off'
            print("MCS mode is %s" % mode)

PluginClass = MCSCommand
