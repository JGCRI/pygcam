import os
from argparse import Namespace
from pygcam.plugin import PluginBase
from pygcam.config import getConfig, DEFAULT_SECTION, getParam
from pygcam.log import getLogger

_logger = getLogger(__name__)

VERSION = '0.1'

class Plugin(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Generate carbon intensity plots'''}

        super(Plugin, self).__init__('plotCI', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('-b', '--baseline', type=str, required=True,
                            help='''The name of the baseline scenario''')

        parser.add_argument('-p', '--policy',   type=str, required=True,
                            help='''The name of the policy scenario''')

        parser.add_argument('-y', '--years', type=str, default='', help='''Year range of the form YYYY-YYYY''')

        parser.add_argument('-d', '--diffsDir', type=str,
                            help='''Directory holding differences between CSVs from scenario and baseline''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)

        return parser


    # TODO: TEST

    def run(self, args, tool):
        #getConfig(DEFAULT_SECTION)

        # If not passed on command-line, read from config file
        years = args.years or getParam('GCAM.Years')

        if args.diffsDir:
            os.chdir(args.diffsDir)

        with open('fuelEJ.txt', 'r') as f:
            line = f.readline()
            fuelEJ = float(line.strip())

        multiplier = 1.0 / fuelEJ

        print "Fuel shock: %4.2f, multiplier: %4.2f" % (fuelEJ, multiplier)

        argDict = {
            'csvFile'    : 'Emissions-changes-%s-%s.csv' % (args.policy, args.baseline),
            'title'      : 'Contributions to carbon intensity',
            'outputDir'  : os.path.join('.', 'figures'),
            'years'      : years,
            'labelColor' : 'black',
            'box'        : True,
            'sumYears'   : True,
            'rotation'   : 0,
            'ncol'       : 3,
            'zeroLine'   : True,
            'ylabel'     : 'g CO$_2$e / MJ',
            'legendY'    : -0.2,
            'barWidth'   : 0.25,
            'multiplier' : multiplier
        }

        # TBD: Need to make PluginManager command instances available by name

        self.chartParser = PluginBase.getParser('chart')
        chartArgs = self.chartParser.parse_args(namespace=Namespace(**argDict))
        self.chartCmd.run(chartArgs)
