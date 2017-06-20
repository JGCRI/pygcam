#! /usr/bin/env python
'''
Created on 4/26/15

@author: rjp
'''
from ..subcommand import SubcommandABC

class BioConstraintsCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Bioenergy constraint generator'''}

        super(BioConstraintsCommand, self).__init__('bioConstraint', subparsers, kwargs)

    def addArgs(self, parser):
        from ..constraints import PolicyChoices, DefaultCellulosicCoefficients, DefaultYears

        parser.add_argument('-b', '--baseline', default=None,
                            help='The baseline on which the policy scenario is based')

        parser.add_argument('-B', '--biomassPolicyType', default='tax', choices=PolicyChoices,
                             help='Regional biomass policy type')

        parser.add_argument('-c', '--coefficients',
                            help='''A comma-separated string of year:coefficient pairs. This
                            sets the cellulosic ethanol conversion coefficients. Defaults to
                            standard GCAM values: %s.''' % DefaultCellulosicCoefficients)

        parser.add_argument('-e', '--cellEtohPolicyType', default='tax', choices=PolicyChoices,
                             help='Cellulosic ethanol policy type')

        parser.add_argument('-l', '--defaultLevel', type=float, default=0.0,
                            help='''Target cellulosic biofuel level (EJ). All or individual years
                            values can be set (overriding -l flag values) using the -L flag.''')

        parser.add_argument('-L', '--annualLevels', required=False,
                            help='''Optional cellulosic biofuel production levels by year. Value
                            must be a comma-delimited string of year:level pairs, where level is
                            given in EJ. If -l is not used to set default for all years, you must
                            specify values for all years using this option.''')

        # parser.add_argument('-m', '--fromMCS', action='store_true',
        #                      help="Used when calling from gcammcs so correct pathnames are computed.")

        parser.add_argument('-p', '--policy',
                            help='The policy scenario name')

        parser.add_argument('-P', '--purposeGrownPolicyType', default='subsidy', choices=PolicyChoices,
                             help='Purpose-grown biomass policy type')

        parser.add_argument('-R', '--resultsDir',
                            help='The parent directory holding the GCAM output workspaces')

        parser.add_argument('-s', '--switchgrass', action='store_true',
                             help="Generate constraints for switchgrass")

        parser.add_argument('-S', '--subdir', default='',
                             help='Sub-directory for local-xml files, if any')

        parser.add_argument('-x', '--xmlOutputDir',
                             help='''The directory into which to generate XML files. Defaults to
                             policy name in the current directory.''')

        parser.add_argument('-y', '--years', default=DefaultYears,
                            help='''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "%s"''' % DefaultYears)
        return parser


    def run(self, args, tool):
        from ..constraints import genBioConstraints

        genBioConstraints(**vars(args))
