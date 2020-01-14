#! /usr/bin/env python
'''
Created on 4/26/15

@author: rjp
'''
from ..subcommand import SubcommandABC, clean_help

DefaultName  = 'cellulosic ethanol'
DefaultTag   = 'cell-etoh'
DefaultType  = 'subsidy'

class DeltaConstraintsCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {#'aliases' : ['delta'],
                  'help' : clean_help('''Specify incremental values to add to the production of a given fuel,
                              by year, and generate the corresponding constraint file.''')}

        super(DeltaConstraintsCommand, self).__init__('deltaConstraint', subparsers, kwargs)

    def addArgs(self, parser):
        from ..constraints import PolicyChoices, DefaultCellulosicCoefficients, DefaultYears

        parser.add_argument('-c', '--coefficients',
                            help=clean_help('''A comma-separated string of year:coefficient pairs. This
                            sets the cellulosic ethanol conversion coefficients. Defaults to
                            standard GCAM values: %s.''' % DefaultCellulosicCoefficients))

        parser.add_argument('-b', '--baseline', required=True,
                            help=clean_help('The baseline on which the policy scenario is based'))

        parser.add_argument('-B', '--biomassPolicyType', choices=PolicyChoices, default=None,
                            help=clean_help('Regional biomass policy type. Default is None.'))

        parser.add_argument('-f', '--fuelName', default=DefaultName,
                            help=clean_help("The fuel to generate constraints for. Default is %s" % DefaultName))

        parser.add_argument('-l', '--defaultDelta', type=float, default=0.0,
                            help=clean_help('''Default increment to add to each year (EJ). All or individual
                            years values can be set (overriding -l flag values) using the -L flag.'''))

        parser.add_argument('-L', '--annualDeltas', default='',
                            help=clean_help('''Optional production increments by year. Value must be a
                            comma-delimited string of year:level pairs, where level in is EJ.
                            If -l is not used to set default for all years, you must specify
                            values for all years using this option.'''))

        # parser.add_argument('-m', '--fromMCS', action='store_true',
        #                      help=clean_help("Used when calling from gcammcs so correct pathnames are computed."))

        parser.add_argument('-p', '--policy', required=True,
                            help=clean_help('The policy scenario name'))

        parser.add_argument('-P', '--purposeGrownPolicyType', choices=PolicyChoices, default=None,
                             help=clean_help('Purpose-grown biomass policy type. Default is None.'))

        parser.add_argument('-R', '--resultsDir', default='.',
                            help=clean_help('The parent directory holding the GCAM output workspaces'))

        parser.add_argument('-S', '--subdir', default='',
                             help=clean_help('Sub-directory for local-xml files, if any'))

        parser.add_argument('-t', '--fuelTag', default=DefaultTag,
                             help=clean_help("The fuel tag to generate constraints for. Default is %s" % DefaultTag))

        parser.add_argument('-T', '--policyType', choices=PolicyChoices, default=DefaultType,
                             help=clean_help('Type of policy to use for the fuel. Default is %s.' % DefaultType))

        parser.add_argument('-x', '--xmlOutputDir',
                             help=clean_help('''The directory into which to generate XML files.
                             Defaults to policy name in the current directory.'''))

        parser.add_argument('-y', '--years', default=DefaultYears,
                            help=clean_help('''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "%s"''' % DefaultYears))
        return parser


    def run(self, args, tool):
        from ..constraints import genDeltaConstraints

        genDeltaConstraints(**vars(args))
