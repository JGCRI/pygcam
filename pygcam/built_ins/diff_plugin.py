from ..subcommand import SubcommandABC, clean_help

class DiffCommand(SubcommandABC):
    def __init__(self, subparsers):
        helptext = 'Compute differences between CSV files generated by GCAM batch queries.'
        desc = '''

            '''
        kwargs = {'help' : helptext,
                  'description' : desc}
        super(DiffCommand, self).__init__('diff', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        parser.add_argument('csvFiles', nargs='+',
                    help=clean_help('''The files to process. For difference operations, the first file is treated
                    as the reference file whose time-series data is subtracted from that of each other
                    file. If missing, ".csv" suffixes are added to all arguments (the ".csv" is optional).'''))

        parser.add_argument('-D', '--workingDir', default='.',
                            help=clean_help('''The directory to change to before performing any operations'''))

        parser.add_argument('-g', '--groupSum', default="",
                            help=clean_help('''Group data for each timestep (or interpolated annual values) by the
                            given column, and sum all members of each group to produce a timeseries for
                            each group. Takes precedence over the simpler "-S" ("--sum") option.'''))

        parser.add_argument('-i', '--interpolate', action="store_true",
                            help=clean_help("Interpolate (linearly) annual values between timesteps."))

        parser.add_argument('-o', '--outFile', default='differences.csv',
                            help=clean_help('''The name of the ".csv" or ".xlsx" file containing the differences
                            between each scenario and the reference. Default is "differences.csv".'''))

        parser.add_argument('-c', '--convertOnly', default=False, action="store_true",
                            help=clean_help('''Convert the given CSV files into an Excel workbook, one sheet per CSV file.'''))

        parser.add_argument('-p', '--asPercentChange', default=False, action="store_true",
                            help=clean_help('''Compute percent change rather than simple difference.'''))

        parser.add_argument('-q', '--queryFile', default='',
                            help=clean_help('''If the extension is ".xml" (case insensitive), the argument must be an XML file
                            holding a list of queries to run, with optional mappings specified to rewrite output.
                            This file has the same structure as the <queries> element in project.xml. If the file
                            doesn't end in ".xml", it must be a text file listing the names of queries to process,
                            one per line. NOTE: When --queryFile is specified, the two positional arguments are
                            required: the names of the baseline and policy scenarios, in that order.'''))

        parser.add_argument('-r', '--rewriteSetsFile',
                            help=clean_help('''An XML file defining query maps by name (default taken from
                            config parameter "GCAM.RewriteSetsFile")'''))

        parser.add_argument('-S', '--sum', default=False, action="store_true",
                            help=clean_help('''Sum all timestep (or interpolated annual values) to produce a single time-series.'''))

        parser.add_argument('-s', '--skiprows', type=int, default=1,
                            help=clean_help('''The number of rows to skip. Default is 1, which works for GCAM batch query output.
                            Use -s0 for outFile.csv'''))

        parser.add_argument('-y', '--years', default="",
                            help=clean_help('''Takes a parameter of the form XXXX-YYYY, indicating start and end years of interest.
                            Other years are dropped (except for annual outputs.)'''))

        parser.add_argument('-Y', '--startYear', type=int, default=0,
                            help=clean_help('''The year at which to begin interpolation'''))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ..diff import diffMain
        diffMain(args)
