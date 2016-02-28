from pygcam.plugin import PluginBase
from pygcam.config import DEFAULT_SECTION
from pygcam.log import getLogger
from pygcam.chart import driver

_logger = getLogger(__name__)

TIMESTEP = 5            # 5 year time-step

VERSION = "0.3"

class ChartCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Generate charts from CSV files generated by GCAM batch queries''',
                  'description' : '''Generate plots from GCAM-style ".csv" files.
                   Two types of plots are currently supported: (i) stacked bar plots based on summing values
                   over all years (with optional interpolation of annual values), by the given 'indexCol'
                   (default is 'region'), and (ii) stacked bar plots by year for some data column, where the data
                   are grouped by and summed across elements with the indicated 'indexCol'. The first option is
                   indicated by using the '-S' ('--sumYears') option. Numerous options allow the appearance to
                   be customized.'''}

        super(ChartCommand, self).__init__('chart', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('csvFile', nargs='?', default=None,
                            help='''The file containing the data to plot.''')

        parser.add_argument('-a', '--configSection', type=str, default=DEFAULT_SECTION,
                            help='''The name of the section in the config file to read from.
                            Defaults to %s''' % DEFAULT_SECTION)

        parser.add_argument('-b', '--box', action="store_true",
                            help='''Draw a box around the plot. Default is no box.''')

        parser.add_argument('-B', '--byRegion', action="store_true",
                            help='''Generate one plot per region. Region names are read from the CSV file,
                            so they reflect any regional aggregation produced by the query.''')

        parser.add_argument('-c', '--columns', type=str, default="output",
                            help='''Specify the column whose values identify the segments in the stacked
                            bar chart. (These appear in the legend.)''')

        parser.add_argument('-C', '--constraint', type=str, default=None,
                            help='''Apply a constraint to limit the rows of data to plot. The constraint
                            can be any constraint string that is valid for the DataFrame.query() method,
                            e.g., -C 'input == "biomass"'
                            ''')

        parser.add_argument('-d', '--outputDir', type=str, default=".",
                            help='''The directory into which to write image files. Default is "."''')

        parser.add_argument('-D', '--workingDir', default='.',
                            help='''The directory to change to before performing any operations''')

        parser.add_argument('-e', '--enumerate', action="store_true",
                            help='''Prefix image filenames with sequential number for easy reference.
                            Used only with --fromFile''')

        parser.add_argument('-f', '--fromFile', default=None,
                            help='''A file from which to read argument strings, one per line.
                            These are read as if chartGCAM.py were called on each line individually,
                            but avoiding the ~2 sec startup time for the bigger python packages.''')

        parser.add_argument('-F', '--fuelFile', default=None,
                            help='''A file containing the number of EJ of fuel that constitute the shock
                            the differences represent. If provided, the difference values are divided by
                            the quantity given.''')

        parser.add_argument('--format', default=None,
                            help='''Specify a format for the Y-axis. Possible values are '.' for float,
                            ',' for int with commas, or any format recognized by print, e.g., "%%.2f" to
                            Y values as floats with 2 decimal places.''')

        parser.add_argument('-g', '--ygrid', action="store_true",
                            help="Show light grey horizontal lines at the major Y-axis ticks. Default is no grid.")

        parser.add_argument('-i', '--interpolate', action="store_true",
                            help="Interpolate (linearly) annual values between timesteps.")

        parser.add_argument('-I', '--indexCol', default="region",
                            help='''A column to use as the index column, or blank for None. Default is "region".''')

        parser.add_argument('-k', '--yticks', action="store_true",
                            help="Show tick marks on Y-axis. Default is no tick marks.")

        parser.add_argument('-l', '--label', action="store_true",
                            help="Add text along the right side of the figure showing the filename.")

        parser.add_argument('-L', '--labelColor', default=None,
                            help='''Color for the text label, which defaults to lightgrey. Some users may
                            prefer "black", for example. (Implies -l)''')

        parser.add_argument('-m', '--multiplier', type=float, default=None,
                            help='''A value to multiply results by before generating the plot.
                            This is useful for unit conversions, e.g., "-m 3.667" converts Tg C to Tg CO2.
                            Be sure to set Y axis label.''')

        parser.add_argument('-n', '--ncol', type=int, default=5,
                            help='''The number of columns with which to display the legend. Default is 5.''')

        parser.add_argument('-N', '--scenario', default="",
                            help='''When using the '--fromFile' option, this argument is used to specify one
                            or more scenario names (delimited by commas if more than one). These are substituted
                            into each line read from the file as the value for "{scenario}" wherever it appears
                            on each line read from the 'fromFile'.''')

        parser.add_argument('--negate', action="store_true",
                            help="""Multiply data by -1 before plotting, which can make interpretation
                            of some figures more intuitive. The string "-negated" is added to the file
                            label, displayed if the "-l" or "-L" flag is specified.""")

        parser.add_argument('-o',  '--outFile', default="",
                            help='''The name of the image file to create. Format is determined from
                            filename extension. All common formats are allowed, e.g., png, pdf, tif,
                            and gif. Try it; it probably works. Default is the name of the data file
                            substituting ".png" for ".csv"''')

        parser.add_argument('-O', '--open', action="store_true",
                            help="Open the plot file after generating it. (Works on Mac, maybe on other platforms.)")

        parser.add_argument('-p',  '--palette', default=None, # "hls",
                            help='''The name of a color palette to use. Some good options include hls, husl, and Paired.
                            See http://stanford.edu/~mwaskom/software/seaborn/tutorial/color_palettes.html''')

        parser.add_argument('-r', '--rotation', type=int, default=90,
                            help='''Set the rotation angle for X-axis labels. Defaults to 90 degrees (vertical).
                            Use 0 for horizontal labels.''')

        parser.add_argument('-R', '--reference', default="reference",
                            help='''When using the '--fromFile' option, this argument is used to specify the
                            name of the reference scenario. The "other" scenario is given using the "-N" option.
                            These are substituted into each line read from the file as the value for "{scenario}"
                            and "{reference}" (without the quotes) wherever they appear on each line read
                            from the 'fromFile'. Defaults to "reference"''')

        parser.add_argument('-s', '--skiprows', type=int, default=1,
                            help='''The number of rows of the CSV file to skip before reading the data (starting
                            with a header row with column names.) Default is 1, which works for GCAM batch
                            query output.''')

        parser.add_argument('-S', '--sumYears', action="store_true",
                            help='''Sum across the time horizon, typically by region. This results
                            in a stacked bar plot. When not summed over years (the default) a stacked area
                            plot is generated showing values grouped and summed by indexCol (-I) and
                            presented by year.''')

        parser.add_argument('-t', '--yearStep', type=int, default=TIMESTEP,
                            help='''The spacing of year labels on X-axis for time-series plots.
                            Defaults to %d.''' % TIMESTEP)

        parser.add_argument('-T', '--title', default="",
                            help='''Adds a title to the plot. Default is no title. The string can have
                            LaTeX math language in it, e.g., 'CO$_2$' causes the 2 to be subscripted, and
                            'MJ$^{-1}$' results in "MJ" with a superscripted exponent of -1. The string
                            '$\Delta$' results in a capital Greek delta. See LaTeX documentation for more
                            options. Be sure to enclose the title in single quotes so the "$" is not
                            (mis)interpreted by the shell.''')

        parser.add_argument('--timeseries', action='store_true',
                            help='''Plot the data as a time series.''')

        parser.add_argument('--transparent', action='store_true',
                            help='''Save the plot with a transparent background. (Default is white.)''')

        parser.add_argument('-u', '--unstacked', default=None,
                            help='''Draw an unstacked bar plot for the column given as an argument to this
                            option, showing three groups of bars: the region, all other regions, and the total.''')

        parser.add_argument('-v', '--valueCol', type=str, default=None,
                            help='''Identify a column to plot for unstacked bar plots. If not specified,
                            values are summed across years.''')

        parser.add_argument('-x', '--suffix', default=None,
                            help='''A suffix to append to the basename of the input csv file to create the
                            name for the output file. For example, if processing my_data.csv, indicating
                            -x '-by-region.pdf' results in an output file named my_data-by-region.pdf.''')

        parser.add_argument('-X', '--xlabel', type=str, default="",
                            help='''Defines a label for the X-axis; defaults to blank. LaTeX math language
                            is supported. (See the -T flag for more info.)''')

        parser.add_argument('-Y', '--ylabel', type=str, default="EJ",
                            help='''Label for the Y-axis; defaults to "EJ". LaTeX math language
                            is supported. (See the -T flag for more info.)''')

        parser.add_argument('-y', '--years', type=str, default="",
                            help='''Takes a parameter of the form XXXX-YYYY, indicating start and end
                            years of interest. Data for all other years are dropped.''')

        parser.add_argument('--ymax', type=float, default=None,
                            help='''Set the scale of a figure by indicating the value to show as the
                            maximum Y value. (By default, scale is set according to the data.)''')

        parser.add_argument('--ymin', type=float, default=None,
                            help='''Set the scale of a figure by indicating the value (given as abs(value),
                            but used as -value) to show as the minimum Y value''')

        parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + VERSION)

        parser.add_argument('--verbose', action='store_true', help='Show diagnostic output')

        parser.add_argument('-z', '--zeroLine', action="store_true",
                                help='''Whether to show a line at Y=0''')
        #
        # For manually tweaking figure layout
        #
        parser.add_argument('--legendY', type=float, default=None,
                            help='''The Y position of the legend. Useful for fixing poorly formatted figures.
                            Note that to pass a negative value, use the syntax --legendY="-xxx.xxx", otherwise
                            the hyphen is interpreted as indicating a command-line argument.''')

        parser.add_argument('--barWidth', type=float, default=0.5,
                            help='''The relative width of bars. Helpful when plotting only 1 or 2 bar, so they
                            aren't obnoxiously wide. Default is 0.5''')

        return parser


    def run(self, args):
        driver(args)


PluginClass = ChartCommand
