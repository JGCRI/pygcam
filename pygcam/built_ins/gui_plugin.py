'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
from ..subcommand import SubcommandABC

class GUICommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Run the Graphical User Interface generated from the command-line interface.'''}

        super(GUICommand, self).__init__('gui', subparsers, kwargs, group='utils', guiSuppress=True)

    def addArgs(self, parser):
        parser.add_argument('-d', '--debug', action='store_true',
                            help='''Set the dash (flask) debug flag.''')
        return parser

    def run(self, args, tool):
        from ..gui.command_line import driver
        driver(args)


PluginClass = GUICommand
