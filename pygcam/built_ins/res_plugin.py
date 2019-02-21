"""
.. Support for generating renewable energy standards described in an XML file.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2019 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC

class RESCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help': '''Generate an XML file that implements a RES policy on the electricity
                             sector as described in the given XML input file.'''}

        super(RESCommand, self).__init__('res', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        parser.add_argument('-i', '--inputFile', default=None,
                            help='''A CSV or XML file defining the RES policy. Default is the value of
                            configuration file parameter GCAM.RESDescriptionFile. If set to a
                            relative pathname (i.e., not starting with "/", "\\", or drive specifier
                            "[a-zA-Z]:"), it is assumed to be relative to %%(GCAM.ProjectDir)s/etc.
                            If a CSV file is given, it is converted to an intermediate RES policy XML 
                            file before translation to GCAM-readable input.''')

        parser.add_argument('-o', '--outputXML', default=None,
                            help='''The directory into which to write the modified files.
                                    Default is the value of configuration file parameter 
                                    GCAM.RESImplementationXmlFile. If set to a relative pathname,
                                    it is assumed to be relative to 
                                    %%(GCAM.SandboxRefWorkspace)s/local-xml/{scenario}, in which
                                    case, the "-s/--scenario" argument is required.''')

        parser.add_argument('-S', '--scenario', default=None,
                            help='''The name of the scenario for which to generate the policy 
                                    implementation XML file. Required if no argument is given
                                    to the "-o/--outputXML" flag, or if the argument is a
                                    relative pathname.''')

        parser.add_argument('-d', '--display', action="store_true",
                            help='''If set, the result of the RES policy is displayed in tabular format,
                                    and the program exits. ''')
        return parser

    def run(self, args, tool):
        from ..RESPolicy import resPolicyMain

        resPolicyMain(args)
