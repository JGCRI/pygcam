"""
.. Support for generating renewable energy standards described in an XML file.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2020 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC, clean_help

class ZEVCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help': clean_help('''Generate an CSV template file that can be used to implement a
            ZEV policy on the sectors, transSubsectors and technologies as described on the command-line.''')}

        super(ZEVCommand, self).__init__('zev', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        parser.add_argument('-i', '--include', action='append', default=None,
                            help=clean_help('''A colon (":") delimited list of comma-delimited sectors, 
                                tranSubsectors, and technologies to include in the CSV template file.
                                Example: "--include trn_pass_road_LDV_4W::BEV,FCEV" means include only two 
                                technologies (BEV,FCEV), but for any tranSubsector under the specified sector. 
                                Multiple -I arguments are allowed.'''))

        defaultCSV = 'zev_policy.csv'
        parser.add_argument('-o', '--outputCSV', default=defaultCSV,
                            help=clean_help('''The directory into which to write the generated CSV template.
                                    Default is "{}". If set to a relative pathname, it is assumed to 
                                    be relative to %%(GCAM.ProjectDir)s/etc.'''.format(defaultCSV)))

        parser.add_argument('-r', '--regions', default=None,
                            help=clean_help('''A comma-delimited list of regions to include in the generated template. 
                             By default all regions are included. '''))

        parser.add_argument('-S', '--scenario', default=None,
                            help=clean_help('''The name of the scenario for which to generate the policy 
                                    implementation XML file. Required if no argument is given
                                    to the "-o/--outputXML" flag, or if the argument is a
                                    relative pathname.'''))

        parser.add_argument('-t', '--tag', default='transportation',
                            help=clean_help('''The config file tag identifying the transportation file to operate on.'''))

        parser.add_argument('-u', '--GCAM-USA', action="store_true",
                            help=clean_help('''If set, produce output compatible with GCAM-USA regions.'''))

        parser.add_argument('-y', '--years', default='2015-2100',
                            help=clean_help('''A hyphen-separated range of timestep years to include in the generated template.
                            Default is "2015-2100"'''))

        return parser

    def run(self, args, tool):
        from ..ZEVPolicy import zevPolicyMain
        zevPolicyMain(args)
