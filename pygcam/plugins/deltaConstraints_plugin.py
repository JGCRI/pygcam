from pygcam.plugin import PluginBase
from pygcam.config import DEFAULT_SECTION
from pygcam.log import getLogger
from pygcam.constraints import (DefaultCellulosicCoefficients, DefaultName, PolicyChoices,
                                DefaultTag, DefaultYears, genDeltaConstraints)

_logger = getLogger(__name__)

VERSION = "0.1"

class Plugin(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Specify incremental values to add to the production of a given fuel,
                              by year, and generate the corresponding constraint file.''',
                  'description' : '''Longer description for sub-command'''}

        super(Plugin, self).__init__('deltaConstraint', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('-a', '--configSection', type=str, default=DEFAULT_SECTION,
                            help='''The name of the section in the config file to read from.
                            Defaults to %s''' % DEFAULT_SECTION)

        parser.add_argument('-c', '--coefficients', type=str, default=None,
                            help='''A comma-separated string of year:coefficient pairs. This
                            sets the cellulosic ethanol conversion coefficients. Defaults to
                            standard GCAM values: %s.''' % DefaultCellulosicCoefficients)

        parser.add_argument('-b', '--biomassPolicyType', choices=PolicyChoices, default='subsidy',
                            help='Regional biomass policy type. Default is subsidy.')

        parser.add_argument('-B', '--baseline', required=True,
                            help='The baseline on which the policy scenario is based')

        parser.add_argument('-f', '--fuelName', default=DefaultName,
                            help="The fuel to generate constraints for. Default is %s" % DefaultName)

        parser.add_argument('-l', '--defaultDelta', type=float, default=0.0,
                            help='''Default increment to add to each year (EJ). All or individual
                            years values can be set (overriding -l flag values) using the -L flag.''')

        parser.add_argument('-L', '--annualDeltas', default='',
                            help='''Optional production increments by year. Value must be a
                            comma-delimited string of year:level pairs, where level in is EJ.
                            If -l is not used to set default for all years, you must specify
                            values for all years using this option.''')

        parser.add_argument('-m', '--fromMCS', action='store_true',
                             help="Used when calling from gcammcs so correct pathnames are computed.")

        parser.add_argument('-p', '--purposeGrownPolicyType', choices=PolicyChoices, default='subsidy',
                             help='Purpose-grown biomass policy type. Default is subsidy.')

        parser.add_argument('-P', '--policy', required=True,
                            help='The policy scenario name')

        parser.add_argument('-R', '--resultsDir', default='.',
                            help='The parent directory holding the GCAM output workspaces')

        parser.add_argument('-S', '--subdir', default='',
                             help='Sub-directory for local-xml files, if any')

        parser.add_argument('-t', '--fuelTag', default=DefaultTag,
                             help="The fuel tag to generate constraints for. Default is %s" % DefaultTag)

        parser.add_argument('-T', '--policyType', choices=PolicyChoices, default='tax',
                             help='Type of policy to use for the fuel. Default is tax.')

        parser.add_argument('-v', '--verbose', action='store_true',
                             help="Show diagnostic messages")

        parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + VERSION)

        parser.add_argument('-x', '--xmlOutputDir', default=None,
                             help='''The directory into which to generate XML files.
                             Defaults to policy name in the current directory.''')

        parser.add_argument('-y', '--years', default=DefaultYears,
                            help='''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "%s"''' % DefaultYears)
        return parser


    def run(self, args, tool):
        genDeltaConstraints(**vars(args))

# Alternative to naming class 'Plugin':
# PluginClass = MyPluginClassName
