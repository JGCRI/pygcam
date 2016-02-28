from pygcam.plugin import PluginBase

# from pygcam.log import getLogger
# _logger = getLogger(__name__)

VERSION = "0.2"

class DiffCommand(PluginBase):
    def __init__(self, subparsers):
        helptext = 'Compute differences between CSV files generated by GCAM batch queries.'
        desc = '''
            The csvDiff.py script computes the differences between results from two or
            more CSV files generated from batch queries run on a GCAM database, saving
            the results in either a CSV or XLSX file, according to the extension given to
            the output file. If not provided, the output filename defaults to differences.csv.
            If multiple otherFiles are given (i.e., the referenceFile plus 2 or more other
            files named on the command-line), the resulting CSV file will contain one difference
            matrix for each otherFile, with a label indicating which pair of files were used
            to produce each result. When the output file is in XLSX format, each result is
            written to a separate worksheet. If the -c flag is specified, no differences are
            computed; rather, the .csv file contents are combined into a single .xlsx file.
            '''
        kwargs = {'help' : helptext,
                  'description' : desc}
        super(DiffCommand, self).__init__('diff', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('csvFiles', nargs='+',
                    help='''The files to process. For difference operations, the first file is treated
                    as the reference file whose time-series data is subtracted from that of each other
                    file. If missing, ".csv" suffixes are added to all arguments (the ".csv" is optional).''')

        # parser.add_argument('-c', '--configSection', type=str, default=DEFAULT_SECTION,
        #                     help='''The name of the section in the config file to read from.
        #                     Defaults to %s''' % DEFAULT_SECTION)

        parser.add_argument('-D', '--workingDir', default='.',
                            help='''The directory to change to before performing any operations''')

        parser.add_argument('-g', '--groupSum', type=str, default="",
                            help='''Group data for each timestep (or interpolated annual values) by the
                            given column, and sum all members of each group to produce a timeseries for
                            each group. Takes precedence over the simpler "-S" ("--sum") option.''')

        parser.add_argument('-i', '--interpolate', action="store_true",
                            help="Interpolate (linearly) annual values between timesteps.")

        parser.add_argument('-o', '--outFile', default='differences.csv',
                            help='''The name of the ".csv" or ".xlsx" file containing the differences
                            between each scenario and the reference. Default is "differences.csv".''')

        parser.add_argument('-c', '--convertOnly', default=False, action="store_true",
                            help='''Convert the given CSV files into an Excel workbook, one sheet per CSV file.''')

        parser.add_argument('-p', '--percentage', default=False, action="store_true",
                            help='''Compute the difference on a percentage basis, i.e.,
                                    (X minus reference)/reference.''')

        parser.add_argument('-q', '--queryFile', default='',
                            help='''A file from which to take the names of queries to process. When --queryFile
                            is specified, the two positional arguments are the names of the baseline and policy
                            scenarios, in that order.''')

        parser.add_argument('-S', '--sum', default=False, action="store_true",
                            help='''Sum all timestep (or interpolated annual values) to produce a single time-series.''')

        parser.add_argument('-s', '--skiprows', type=int, default=1,
                            help='''The number of rows to skip. Default is 1, which works for GCAM batch query output.
                            Use -s0 for outFile.csv''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)

        parser.add_argument('-y', '--years', type=str, default="",
                            help='''Takes a parameter of the form XXXX-YYYY, indicating start and end years of interest.
                            Other years are dropped (except for annual outputs.)''')

        parser.add_argument('-Y', '--startYear', type=int, default=0,
                            help='''The year at which to begin interpolation''')

        return parser   # for auto-doc generation


    def run(self, args):
        pass


PluginClass = DiffCommand
