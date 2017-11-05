'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
from ..subcommand import SubcommandABC


class MCSCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Enable or disable pygcam Monte Carlo Simulation sub-commands.'''}

        super(MCSCommand, self).__init__('mcs', subparsers, kwargs, group='utils', label='MCS')

    def addArgs(self, parser):
        parser.add_argument('mode', choices=['on', 'off', 'status'],
                            help='''Turn MCS mode on or off, or report current setting''')
        return parser

    def run(self, args, tool):
        import os
        from ..config import mcsSentinelFile, usingMCS

        sentinelFile = mcsSentinelFile()

        if args.mode == 'on':
            open(sentinelFile, 'w').close()     # create empty file

        elif args.mode == 'off':
            try:
                os.remove(sentinelFile)         # remove it if it exists
            except:
                pass
        else:
            # Report current mode
            mode = 'on' if usingMCS() else 'off'
            print("MCS mode is %s" % mode)

PluginClass = MCSCommand
