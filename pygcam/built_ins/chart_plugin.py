'''
.. Created on: 2/12/15
   Common functions and data

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from ..constants import DEFAULT_TIMESTEP
from ..subcommand import SubcommandABC, clean_help

class ChartCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Generate charts from CSV files generated by GCAM batch queries'''}

        super(ChartCommand, self).__init__('chart', subparsers, kwargs, group='project')

    def addArgs(self, parser):

        # argparse type checker/converter to handle symbolic unit conversions
        def floatOrConversion(string):
            import argparse
            from ..units import getUnits

            u = getUnits()
            try:
                return u.convert(string)
            except:
                raise argparse.ArgumentTypeError("%r is not a float or a known unit conversion" % string)

        # --byRegion and --region are mutually exclusive
        group1 = parser.add_mutually_exclusive_group()

        # --divisorFile and --divisor are mut. excl.
        group2 = parser.add_mutually_exclusive_group()

        # --sumYears and --valueCol are mut. excl.
        group3 = parser.add_mutually_exclusive_group()

        parser.add_argument('csvFile', nargs='?',
                            help=clean_help('''The file containing the data to plot.'''))

        parser.add_argument('-b', '--box', action="store_true",
                            help=clean_help('''Draw a box around the plot. Default is no box.'''))

        group1.add_argument('-B', '--byRegion', action="store_true",
                            help=clean_help('''Generate one plot per region. Region names are read from the CSV file,
                            so they reflect any regional aggregation produced by the query.'''))

        parser.add_argument('-c', '--columns', default="output",
                            help=clean_help('''Specify the column whose values identify the segments in the stacked
                            bar chart. (These appear in the legend.)'''))

        parser.add_argument('-C', '--constraint',
                            help=clean_help('''Apply a constraint to limit the rows of data to plot. The constraint
                            can be any constraint string that is valid for the DataFrame.query() method,
                            e.g., -C 'input == "biomass"'
                            '''))

        parser.add_argument('-d', '--outputDir', default=".",
                            help=clean_help('''The directory into which to write image files. Default is "."'''))

        parser.add_argument('-D', '--workingDir', default='.',
                            help=clean_help('''The directory to change to before performing any operations'''))

        parser.add_argument('-e', '--enumerate', action="store_true",
                            help=clean_help('''Prefix image filenames with sequential number for easy reference.
                            Used only with --fromFile'''))

        parser.add_argument('-f', '--fromFile',
                            help=clean_help('''A file from which to read argument strings, one per line.
                            These are read as if chartGCAM.py were called on each line individually,
                            but avoiding the ~2 sec startup time for the bigger python packages.'''))

        group2.add_argument('-F', '--divisorFile',
                            help=clean_help('''A file containing a floating point value to divide data by
                            before plotting. See also -V.'''))

        parser.add_argument('--format',
                            help=clean_help('''Specify a format for the Y-axis. Possible values are '.' for float,
                            ',' for int with commas, or any format recognized by print, e.g., "%%.2f" to
                            Y values as floats with 2 decimal places.'''))

        parser.add_argument('-g', '--ygrid', action="store_true",
                            help=clean_help("Show light grey horizontal lines at the major Y-axis ticks. Default is no grid."))

        parser.add_argument('-i', '--interpolate', action="store_true",
                            help=clean_help("Interpolate (linearly) annual values between timesteps."))

        parser.add_argument('-I', '--indexCol', default="region",
                            help=clean_help('''A column to use as the index column, or blank for None. This column
                            is displayed on the X-axis of stacked barcharts. Default value is "region".'''))

        parser.add_argument('-k', '--yticks', action="store_true",
                            help=clean_help("Show tick marks on Y-axis. Default is no tick marks."))

        parser.add_argument('-l', '--label', action="store_true",
                            help=clean_help("Add text along the right side of the figure showing the filename."))

        parser.add_argument('-L', '--labelColor',
                            help=clean_help('''Color for the text label, which defaults to lightgrey. Some users may
                            prefer "black", for example. (Implies -l)'''))

        parser.add_argument('-m', '--multiplier', type=floatOrConversion,
                            help=clean_help('''A value to multiply data by before generating the plot. The argument can
                            be a floating point number or the name of any variable in pygcam.unitConversion.py.
                            For example, "-m 3.667" and "-m C_to_CO2" are equivalent, and effectively convert
                            values from Tg C to Tg CO2. Be sure to adjust the Y axis label. See also -M.'''))

        parser.add_argument('-M', '--multiplierFile',
                            help=clean_help('''A file containing a floating point value to multiply data
                            by before plotting. See also -m.'''))

        parser.add_argument('-n', '--ncol', type=int, default=5,
                            help=clean_help('''The number of columns with which to display the legend. Default is 5.'''))

        parser.add_argument('-N', '--scenario', default="",
                            help=clean_help('''When using the '--fromFile' option, this argument is used to specify one
                            or more scenario names (delimited by commas if more than one). These are substituted
                            into each line read from the file as the value for "{scenario}" wherever it appears
                            on each line read from the 'fromFile'.'''))

        parser.add_argument('--negate', action="store_true",
                            help=clean_help("""Multiply data by -1 before plotting, which can make interpretation
                            of some figures more intuitive. The string "-negated" is added to the file
                            label, displayed if the "-l" or "-L" flag is specified."""))

        parser.add_argument('-o',  '--outFile', default="",
                            help=clean_help('''The name of the image file to create. Format is determined from
                            filename extension. All common formats are allowed, e.g., png, pdf, tif,
                            and gif. Try it; it probably works. Default is the name of the data file
                            substituting ".png" for ".csv"'''))

        parser.add_argument('-O', '--open', action="store_true",
                            help=clean_help("Open the plot file after generating it."))

        parser.add_argument('-p',  '--palette', # "hls",
                            help=clean_help('''The name of a color palette to use. Some good options include hls, husl, and Paired.
                            See http://stanford.edu/~mwaskom/software/seaborn/tutorial/color_palettes.html'''))

        parser.add_argument('-r', '--rotation', type=int, default=90,
                            help=clean_help('''Set the rotation angle for X-axis labels. Defaults to 90 degrees (vertical).
                            Use 0 for horizontal labels.'''))

        parser.add_argument('-R', '--reference', default="reference",
                            help=clean_help('''When using the '--fromFile' option, this argument is used to specify the
                            name of the reference scenario. The "other" scenario is given using the "-N" option.
                            These are substituted into each line read from the file as the value for "{scenario}"
                            and "{reference}" (without the quotes) wherever they appear on each line read
                            from the 'fromFile'. Defaults to "reference"'''))

        group1.add_argument('--region',
                            help=clean_help('''Plot values only for the given region.'''))

        parser.add_argument('-s', '--skiprows', type=int, default=1,
                            help=clean_help('''The number of rows of the CSV file to skip before reading the data (starting
                            with a header row with column names.) Default is 1, which works for GCAM batch
                            query output.'''))

        group3.add_argument('-S', '--sumYears', action="store_true",
                            help=clean_help('''Sum across the time horizon, typically by region. This results
                            in a stacked bar plot. When not summed over years (the default) a stacked area
                            plot is generated showing values grouped and summed by indexCol (-I) and
                            presented by year.'''))

        parser.add_argument('-t', '--yearStep', type=int, default=DEFAULT_TIMESTEP,
                            help=clean_help('''The spacing of year labels on X-axis for time-series plots.
                            Defaults to %d.''' % DEFAULT_TIMESTEP))

        parser.add_argument('-T', '--title', default="",
                            help=clean_help('''Adds a title to the plot. Default is no title. The string can have
                            LaTeX math language in it, e.g., 'CO$_2$' causes the 2 to be subscripted, and
                            'MJ$^{-1}$' results in "MJ" with a superscripted exponent of -1. The string
                            '$\Delta$' results in a capital Greek delta. See LaTeX documentation for more
                            options. Be sure to enclose the title in single quotes so the "$" is not
                            (mis)interpreted by the shell.'''))

        parser.add_argument('--timeseries', action='store_true',
                            help=clean_help('''Plot the data as a time series.'''))

        parser.add_argument('--transparent', action='store_true',
                            help=clean_help('''Save the plot with a transparent background. (Default is white.)'''))

        parser.add_argument('-u', '--unstackedCol',
                            help=clean_help('''Draw an unstacked bar plot for the column given as an argument to this
                            option, showing three groups of bars: the region, all other regions, and the total.'''))

        parser.add_argument('-U', '--unstackedRegion',
                            help=clean_help('''The region to plot separately from Rest of World in an unstacked plot.
                            Ignored if --byRegion is specified, in which case a plot is created for all regions.'''))

        group3.add_argument('-v', '--valueCol',
                            help=clean_help('''Identify a single column (e.g., a year) to plot for bar plots.'''))

        group2.add_argument('-V', '--divisor', type=floatOrConversion,
                            help=clean_help('''A value to divide year column values by before plotting. The argument can
                            be a floating point number or the name of any variable in pygcam.unitConversion.py.
                            See also -F.'''))

        parser.add_argument('-x', '--suffix',
                            help=clean_help('''A suffix to append to the basename of the input csv file to create the
                            name for the output file. For example, if processing my_data.csv, indicating
                            -x '-by-region.pdf' results in an output file named my_data-by-region.pdf.'''))

        parser.add_argument('-X', '--xlabel', default="",
                            help=clean_help('''Defines a label for the X-axis; defaults to blank. LaTeX math language
                            is supported. (See the -T flag for more info.)'''))

        parser.add_argument('-Y', '--ylabel', default="EJ",
                            help=clean_help('''Label for the Y-axis; defaults to "EJ". LaTeX math language
                            is supported. (See the -T flag for more info.)'''))

        parser.add_argument('-y', '--years', default="",
                            help=clean_help('''Takes a parameter of the form XXXX-YYYY, indicating start and end
                            years of interest. Data for all other years are dropped.'''))

        parser.add_argument('--ymax', type=float,
                            help=clean_help('''Set the scale of a figure by indicating the value to show as the
                            maximum Y value. (By default, scale is set according to the data.)'''))

        parser.add_argument('--ymin', type=float,
                            help=clean_help('''Set the scale of a figure by indicating the value (given as abs(value),
                            but used as -value) to show as the minimum Y value'''))

        parser.add_argument('-z', '--zeroLine', action="store_true",
                                help=clean_help('''Whether to show a line at Y=0'''))
        #
        # For manually tweaking figure layout
        #
        parser.add_argument('--legendY', type=float,
                            help=clean_help('''The Y position of the legend. Useful for fixing poorly formatted figures.
                            Note that to pass a negative value, use the syntax --legendY="-xxx.xxx", otherwise
                            the hyphen is interpreted as indicating a command-line argument.'''))

        parser.add_argument('--barWidth', type=float, default=0.5,
                            help=clean_help('''The relative width of bars. Helpful when plotting only 1 or 2 bar, so they
                            aren't obnoxiously wide. Default is 0.5'''))

        return parser


    def run(self, args, tool):
        from ..chart import chartMain    # avoid importing matplotlib and seaborn until needed

        chartMain(args, tool, self.parser)
