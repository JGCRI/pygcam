from pygcam.plugin import PluginBase
from pygcam.config import DEFAULT_SECTION
from pygcam.log import getLogger
from pygcam.constraints import genBioConstraints, DefaultCellulosicCoefficients, DefaultYears

_logger = getLogger(__name__)

VERSION = "0.1"

class Plugin(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Bioenergy constraint generator''',
                  'description' : '''Longer description for sub-command'''}

        super(Plugin, self).__init__('bioConstraint', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('-a', '--configSection', type=str, default=DEFAULT_SECTION,
                            help='''The name of the section in the config file to read from.
                            Defaults to %s''' % DEFAULT_SECTION)

        parser.add_argument('-b', '--biomassPolicyType', default='tax',
                             help='Regional biomass policy type: must be one of {subs, tax}')

        parser.add_argument('-B', '--baseline', default=None,
                            help='The baseline on which the policy scenario is based')

        parser.add_argument('-c', '--coefficients', type=str, default=None,
                            help='''A comma-separated string of year:coefficient pairs. This
                            sets the cellulosic ethanol conversion coefficients. Defaults to
                            standard GCAM values: %s.''' % DefaultCellulosicCoefficients)

        parser.add_argument('-e', '--cellEtohPolicyType', default='tax',
                             help='Cellulosic ethanol policy type: must be one of {subs, tax}')

        parser.add_argument('-l', '--defaultLevel', type=float, default=0.0,
                            help='''Target cellulosic biofuel level (EJ). All or individual years
                            values can be set (overriding -l flag values) using the -L flag.''')

        parser.add_argument('-L', '--annualLevels', required=False,
                            help='''Optional cellulosic biofuel production levels by year. Value
                            must be a comma-delimited string of year:level pairs, where level is
                            given in EJ. If -l is not used to set default for all years, you must
                            specify values for all years using this option.''')

        parser.add_argument('-m', '--fromMCS', action='store_true',
                             help="Used when calling from gcammcs so correct pathnames are computed.")

        parser.add_argument('-p', '--purposeGrownPolicyType', default='subs',
                             help='Purpose-grown biomass policy type: must be one of {subs, tax}')

        parser.add_argument('-P', '--policy', default=None,
                            help='The policy scenario name')

        parser.add_argument('-R', '--resultsDir', default=None,
                            help='The parent directory holding the GCAM output workspaces')

        parser.add_argument('-s', '--switchgrass', action='store_true',
                             help="Generate constraints for switchgrass")

        parser.add_argument('-S', '--subdir', default='',
                             help='Sub-directory for local-xml files, if any')

        parser.add_argument('-v', '--verbose', action='store_true',
                             help="Show diagnostic messages")

        parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + VERSION)

        parser.add_argument('-x', '--xmlOutputDir', default=None,
                             help='''The directory into which to generate XML files. Defaults to
                             policy name in the current directory.''')

        parser.add_argument('-y', '--years', default=DefaultYears,
                            help='''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "%s"''' % DefaultYears)
        return parser


    def run(self, args):
        genBioConstraints(**vars(args))


# PluginClass = MyPluginClassName
