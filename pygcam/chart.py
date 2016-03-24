'''
.. Created on: 2/12/15
   Common functions and data

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import argparse
import numpy as np
from .log import getLogger
from .error import PygcamException
from .query import readConfigFiles, dropExtraCols, readCsv
from .subcommand import SubcommandABC
from .config import DEFAULT_SECTION

_logger = getLogger(__name__)

TIMESTEP = 5            # 5 year time-step
VERSION  = "0.3"

#%matplotlib inline


def setupPalette(count, pal=None):
    import seaborn as sns

    # See http://xkcd.com/color/rgb/. These were chose mainly to be different "enough".
    colors = ['grass green', 'canary yellow', 'dirty pink', 'azure', 'tangerine', 'strawberry',
              'yellowish green', 'gold', 'sea blue', 'lavender', 'orange brown', 'turquoise',
              'royal blue', 'cranberry', 'pea green', 'vermillion', 'sandy yellow', 'greyish brown',
              'magenta', 'silver', 'ivory', 'carolina blue', 'very light brown']

    #palette = sns.color_palette(pal, count) if pal else sns.hls_palette(count, l=.5, s=.6)
    palette = sns.color_palette(pal, count) if pal else sns.xkcd_palette(colors)
    sns.set_palette(palette, n_colors=count)

# For publications, call setupPlot("paper", font_scale=1.5)
def setupPlot(context="talk", style="white", font_scale=1.0):
    sns.set_context(context, font_scale=font_scale)
    sns.set_style(style)

def plotUnstackedRegionComparison(df, categoryCol=None, valueCol=None, region='USA',
                                  otherRegion='Rest of world', box=False, title='', ncol=3,
                                  xlabel='', ylabel='', ygrid=False, yticks=False,
                                  ymin=None, ymax=None, legendY=None, palette=None):
    '''
    Plot unstacked bars showing the values for 'categoryCol', summed across years,
    for one region, for everything else, and the totals of the two.
    '''
    count = len(df[categoryCol].unique())     # categoryCol = 'land-allocation'
    setupPalette(count, pal=palette)

    fig, ax = plt.subplots(1, 1, figsize=(8, 4))

    yearCols = filter(str.isdigit, df.columns)
    if valueCol:
        df['total'] = df[valueCol]
    else:
        df['total'] = df[yearCols].sum(axis=1)

    df = df.drop(yearCols, axis=1)          # copy to not affect caller's df

    USA = ['US', 'USA', 'United States']
    reg = df.query('region in %s' % USA)
    other = df.query('region not in %s' % USA)

    grp = other.groupby(categoryCol)
    otherSums = grp.sum()
    otherSums.reset_index(inplace=True)
    otherSums['region'] = otherRegion

    grp = reg.groupby(categoryCol)
    regSum = grp.sum()
    regSum.reset_index(inplace=True)
    regSum['region'] = region

    totals = regSum.set_index(categoryCol) + otherSums.set_index(categoryCol)
    totals['region'] = 'Total'
    totals.reset_index(inplace=True)
    world = regSum.append(otherSums).append(totals)

    ax = sns.barplot(x="region", y="total", hue=categoryCol, data=world, ci=None)

    sns.axlabel(xlabel, ylabel)
    legendY = -0.45 if legendY is None else legendY
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, legendY), ncol=ncol)

    if box == False:
        sns.despine(left=True)

    if yticks:
        plt.tick_params(axis='y', direction='out', length=5, width=.75,
                        colors='k', left='on', right='off')

    if ygrid:
        ax.yaxis.grid(color='lightgrey', linestyle='solid')

    #plt.xticks(rotation=rotation)

    if title:
        ax.set_title(title, y=1.05)

    if ymin is not None or ymax is not None:
        ax.set_autoscale_on(False)
        ax.set_ylim(ymin, ymax)

    return (fig, ax)


def plotStackedBarChartScalar(df, indexCol=None, columns=None, values=None, box=False, rotation=90,
                              zeroLine=False, title="", xlabel='', ylabel='', ncol=5, ygrid=False,
                              yticks=False, ymin=None, ymax=None, barWidth=0.5, legendY=None, palette=None):
    '''
    Plot a stacked bar plot using data in df, given the index column, the
    column holding the values to pivot to columns, and the column holding
    the values. The argument 'ncol' specifies the number of columns with
    which to render the legend.
    '''
    # TBD: this needs work to handle year values as columns to plot
    df2 = df[[indexCol, columns, values]].pivot(index=indexCol, columns=columns, values=values)

    setupPalette(len(df2.columns), pal=palette)

    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    df2.plot(kind='bar', stacked=True, ax=ax, grid=False, width=barWidth)

    if box == False:
        sns.despine(left=True)

    if yticks:
        plt.tick_params(axis='y', direction='out', length=5, width=.75,
                        colors='k', left='on', right='off')

    lines = ax.get_lines()
    if lines:
        lines[0].set_visible(False)    # get rid of ugly dashed line

    if zeroLine:
        ax.axhline(0, color='k', linewidth=0.75, linestyle='-')

    if ygrid:
        ax.yaxis.grid(color='lightgrey', linestyle='solid')

    sns.axlabel(xlabel, ylabel)
    legendY = -0.6 if legendY is None else legendY
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, legendY), ncol=ncol)

    plt.xticks(rotation=rotation)

    if title:
        ax.set_title(title, y=1.05)

    if ymin is not None or ymax is not None:
        ax.set_autoscale_on(False)
        ax.set_ylim(ymin, ymax)

    return (fig, ax)


def plotStackedTimeSeries(df, index='region', xlabel='', ylabel='', ncol=5, box=False,
                          zeroLine=False, title="", ygrid=False, yticks=False,
                          ymin=None, ymax=None, barWidth=0.5, legendY=None, yearStep=5,
                          palette=None):

    df = dropExtraCols(df, inplace=False)
    grouped = df.groupby(index)
    df2 = grouped.aggregate(np.sum)
    df3 = df2.transpose()

    setupPalette(len(df3.columns), pal=palette)
    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    df3.plot(kind='bar', stacked=True, ax=ax, grid=False, width=barWidth)

    # space out year labels to every 5 years
    locs, labels = plt.xticks()
    yearCols = filter(str.isdigit, df.columns)
    plt.xticks(locs[::yearStep], yearCols[::yearStep])

    if box == False:
        sns.despine(left=True)

    if yticks:
        plt.tick_params(axis='y', direction='out', length=5, width=.75,
                        colors='k', left='on', right='off')

    lines = ax.get_lines()
    if lines:
        lines[0].set_visible(False)    # get rid of ugly dashed line

    if zeroLine:
        ax.axhline(0, color='k', linewidth=0.75, linestyle='-')

    if ygrid:
        ax.yaxis.grid(color='lightgrey', linestyle='solid')

    if ymin is not None or ymax is not None:
        ax.set_autoscale_on(False)
        ax.set_ylim(ymin, ymax)

    sns.axlabel(xlabel, ylabel)
    legendY = -0.2 if legendY is None else legendY
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, legendY), ncol=ncol)

    if title:
        ax.set_title(title, y=1.05)

    return (fig, ax)


def plotStackedSums(df, indexCol=None, columns=None, xlabel='', ylabel='', rotation=90,
                    ncol=5, box=False, zeroLine=False, ygrid=False, yticks=False,
                    ymin=None, ymax=None, barWidth=0.5, legendY=None, title="", palette=None):
    df = df.copy()
    yearCols = filter(str.isdigit, df.columns)
    df['total'] = df[yearCols].sum(axis=1)

    return plotStackedBarChartScalar(df, indexCol=indexCol, columns=columns, values='total',
                                     box=box, zeroLine=zeroLine, title=title, xlabel=xlabel, ylabel=ylabel,
                                     ygrid=ygrid, yticks=yticks, ymin=ymin, ymax=ymax, rotation=rotation,
                                     ncol=ncol, barWidth=barWidth, legendY=legendY, palette=palette)


def plotTimeSeries(df, xlabel='', ylabel='', box=False, zeroLine=False, title="", ygrid=False,
                   yticks=False, ymin=None, ymax=None, legend=False, legendY=None, yearStep=5):

    fig, ax = plt.subplots(1, 1, figsize=(8, 4))

    yearCols = filter(str.isdigit, df.columns)
    x = map(int, yearCols)
    y = list(df[yearCols].iloc[0])
    plt.plot(x, y)

    # space out year labels to every 5 years
    #locs, labels = plt.xticks()
    #plt.xticks(locs[::yearStep], yearCols[::yearStep])

    if box == False:
        sns.despine(left=True)

    if yticks:
        plt.tick_params(axis='y', direction='out', length=5, width=.75,
                        colors='k', left='on', right='off')

    #lines = ax.get_lines()
    #if lines:
    #    lines[0].set_visible(False)    # get rid of ugly dashed line

    if zeroLine:
        ax.axhline(0, color='k', linewidth=0.75, linestyle='-')

    if ygrid:
        ax.yaxis.grid(color='lightgrey', linestyle='solid')

    if ymin is not None or ymax is not None:
        ax.set_autoscale_on(False)
        ax.set_ylim(ymin, ymax)

    sns.axlabel(xlabel, ylabel)
    if legend:
        legendY = -0.2 if legendY is None else legendY
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, legendY))
    else:
        ax.legend([], frameon=False)

    if title:
        ax.set_title(title, y=1.05)

    return (fig, ax)


def amendFilename(filename, suffix):
    '''
    Insert the given suffix into filename before the extension.
    '''
    base, ext = os.path.splitext(filename)
    return base + '-' + suffix + ext


def chartGCAM(args, num=None, negate=False, fuelEJ=None):
    csvFile    = args.csvFile
    indexCol   = args.indexCol or None
    columns    = args.columns
    sumYears   = args.sumYears
    outFile    = args.outFile
    outputDir  = args.outputDir
    multiplier = args.multiplier
    title      = args.title
    yearStep   = args.yearStep
    legendY    = args.legendY
    ygrid      = args.ygrid
    yticks     = args.yticks
    ylabel     = args.ylabel
    xlabel     = args.xlabel
    rotation   = args.rotation
    box        = args.box
    zeroLine   = args.zeroLine
    ncol       = args.ncol
    barWidth   = args.barWidth
    ymin       = args.ymin
    ymax       = args.ymax
    byRegion   = args.byRegion
    constraint = args.constraint
    timeseries = args.timeseries
    unstacked  = args.unstacked
    palette    = args.palette
    yFormat    = args.format
    valueCol   = args.valueCol

    if not os.path.lexists(outputDir):
        os.mkdir(outputDir, 0o755)

    # use dirname if user provided one; else use outputDir
    if not os.path.dirname(outFile):
        if outFile:
            imgFile = outFile
        else:
            # otherwise compute output filename using outputDir and suffix
            suffix = args.suffix or '.png'
            suffix = '-' + suffix if suffix[0] not in ['.', '-', '_'] else suffix
            filename = os.path.basename(csvFile)
            root, ext = os.path.splitext(filename)
            prefix = "%d-" % num if num else ""
            imgFile = prefix + root + suffix

        outFile = os.path.join(outputDir, imgFile)

    _logger.debug("Generating %s", os.path.abspath(outFile))

    if args.years:
        yearStrs = args.years.split('-')
        assert len(yearStrs) == 2, "Year range must be given as YYYY-YYYY"
    else:
        yearStrs = None

    # e.g., "/Users/rjp/ws-ext/new-reference/batch-new-reference/LUC_Emission_by_Aggregated_LUT_EM-new-reference." % scenario
    df = readCsv(csvFile, skiprows=args.skiprows, years=yearStrs, interpolate=args.interpolate)

    if constraint:
        try:
            df = df.query(constraint)
        except Exception, e:
            raise Exception("Failed to apply constraint: %s\n  -- %s" % (constraint, e))

    yearCols = filter(str.isdigit, df.columns)

    if multiplier:
        _logger.debug("Multiplying all values by %.3f for %s", multiplier, os.path.basename(csvFile))
        df[yearCols] *= multiplier

    # TBD: this is application specific. Move it where?
    if fuelEJ:
        df[yearCols] /= fuelEJ
        sumYears = True         # dividing by total fuel makes sense only for totals

    if negate:
        outFile = amendFilename(outFile, 'negated')
        imgFile = amendFilename(imgFile, 'negated')
        df[yearCols] *= -1

    # If region is None, it's treated as not by region, allowing loop to handle both cases
    regions = df.region.unique() if byRegion else [None]

    outFileOrig = outFile
    imgFileOrig = imgFile

    for region in regions:

        setupPlot(context="talk", style="white")

        if unstacked:
            region = 'USA'
            otherRegion = 'Rest of world'
            fig, ax = plotUnstackedRegionComparison(df, categoryCol=unstacked, valueCol=valueCol, region=region,
                                                    otherRegion=otherRegion, box=box, title=title, ncol=ncol,
                                                    xlabel=xlabel, ylabel=ylabel, ygrid=ygrid, yticks=yticks,
                                                    ymin=ymin, ymax=ymax, legendY=legendY, palette=palette)

        elif region:
            slice = df.query('region == "%s"' % region)
            sliceTitle = title + " (%s)" % region
            outFile = amendFilename(outFileOrig, region)
            imgFile = amendFilename(imgFileOrig, region)

            fig, ax = plotStackedTimeSeries(slice, index=indexCol, yearStep=yearStep, ygrid=ygrid, yticks=yticks,
                                            ymin=ymin, ymax=ymax, zeroLine=zeroLine, title=sliceTitle, legendY=legendY,
                                            box=box, xlabel=xlabel, ylabel=ylabel, ncol=ncol, barWidth=barWidth,
                                            palette=palette)
        elif sumYears:
            fig, ax = plotStackedSums(df, indexCol=indexCol, columns=columns, ygrid=ygrid, yticks=yticks,
                                      rotation=rotation, zeroLine=zeroLine, title=title, legendY=legendY,
                                      box=box, xlabel=xlabel, ylabel=ylabel, ymin=ymin, ymax=ymax,
                                      ncol=ncol, barWidth=barWidth, palette=palette)
        elif timeseries:
            fig, ax = plotTimeSeries(df, xlabel=xlabel, ylabel=ylabel, box=box, zeroLine=zeroLine, title=title, ygrid=ygrid,
                                     yticks=yticks, ymin=ymin, ymax=ymax, legend=False, legendY=legendY, yearStep=yearStep)

        else:
            fig, ax = plotStackedTimeSeries(df, index=indexCol, yearStep=yearStep, ygrid=ygrid, yticks=yticks,
                                            ymin=ymin, ymax=ymax, zeroLine=zeroLine, title=title, legendY=legendY,
                                            box=box, xlabel=xlabel, ylabel=ylabel, ncol=ncol, barWidth=barWidth,
                                            palette=palette)

        if yFormat:
            func = (lambda x, p: format(int(x), ',')) if yFormat == ',' else (lambda x, p: yFormat % x)
            formatter = tkr.FuncFormatter(func)

            ax.get_yaxis().set_major_formatter(formatter)

        labelColor = args.labelColor or 'lightgrey'

        # add the filename to the plot
        if args.label or args.labelColor:
            fig.text(1, 0.5, imgFile, color=labelColor, weight='ultralight', fontsize='xx-small', va='center', ha='right', rotation=270)

        if fig:
            fig.savefig(outFile, bbox_inches='tight', transparent=args.transparent)

        plt.close(fig)

        if args.open:
            from subprocess import call
            import platform

            if platform.system() == 'Windows':
                call(['start', os.path.abspath(outFile)], shell=True)
            else:
                # "-g" => don't bring app to the foreground
                call(['open', '-g', outFile], shell=False)

def getFuelEJ(fuelFile):
    fuelEJ = 0
    if fuelFile:
        with open(fuelFile) as f:
            fuelEJ = float(f.readline())

    return fuelEJ

def driver(mainArgs, tool, parser):
    # Do these slow imports after parseArgs so "-h" responds quickly
    import matplotlib.pyplot as plt
    import matplotlib.ticker as tkr
    import pandas as pd
    import seaborn as sns
    global plt, pd, sns, tkr

    readConfigFiles(mainArgs.configSection)

    if not mainArgs.fromFile and mainArgs.csvFile == '*null*':
        raise PygcamException("Must specify a CSV file or use -f flag to read arguments from a file")

    os.chdir(mainArgs.workingDir)

    # Process these separately
    negate = mainArgs.negate
    del mainArgs.negate

    if mainArgs.fromFile:
        import shlex

        del mainArgs.csvFile    # whatever is passed, e.g., "-", is ignored

        enumerate = mainArgs.enumerate
        num = 1

        with open(mainArgs.fromFile) as f:
            lines = f.readlines()

        # Set up dictionary for substitution into lines as they're read
        substDict = {'scenario'  : None,    # set to current scenario below
                     'reference' : mainArgs.reference,
                     'years'     : mainArgs.years}

        scenarios = mainArgs.scenario.split(',')

        for scenario in scenarios:
            substDict['scenario'] = scenario
            argDict = vars(mainArgs)
            argDict['scenario'] = scenario  # for each call, pass the current scenario only

            # Merge command-line args with those from the file,
            # allowing the ones from the file to override.
            for line in lines:
                # ignore comment lines
                line = line.strip()
                if not line or line[0] == '#':
                    continue

                if line == 'exit':
                    return

                line = line.format(**substDict)
                fileArgs = shlex.split(line)

                argsNS = argparse.Namespace(**argDict)
                # for key, value in argDict.iteritems():
                #     setattr(argsNS, key, value)

                allArgs = parser.parse_args(args=fileArgs, namespace=argsNS)
                fuelEJ = getFuelEJ(allArgs.fuelFile)

                # do this in addition to standard figure. Don't *also* negate since fuelEJ may be + or -.
                chartGCAM(allArgs, num=(num if enumerate else None), fuelEJ=fuelEJ)

                if negate:
                    # do this in addition to standard figure
                    chartGCAM(allArgs, num=(num if enumerate else None), fuelEJ=fuelEJ, negate=True)

                num += 1
    else:
        fuelEJ = getFuelEJ(mainArgs.fuelFile)
        chartGCAM(mainArgs, fuelEJ=fuelEJ)


class ChartCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Generate charts from CSV files generated by GCAM batch queries''',
                  'description' : '''Generate plots from GCAM-style ".csv" files.
                   Two types of plots are currently supported: (i) stacked bar plots based on summing values
                   over all years (with optional interpolation of annual values), by the given 'indexCol'
                   (default is 'region'), and (ii) stacked bar plots by year for some data column, where the data
                   are grouped by and summed across elements with the indicated 'indexCol'. The first option is
                   indicated by using the '-S' ('--sumYears') option. Numerous options allow the appearance to
                   be customized.'''}

        super(ChartCommand, self).__init__('chart', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('csvFile', nargs='?',
                            help='''The file containing the data to plot.''')

        parser.add_argument('-a', '--configSection', default=DEFAULT_SECTION,
                            help='''The name of the section in the config file to read from.
                            Defaults to %s''' % DEFAULT_SECTION)

        parser.add_argument('-b', '--box', action="store_true",
                            help='''Draw a box around the plot. Default is no box.''')

        parser.add_argument('-B', '--byRegion', action="store_true",
                            help='''Generate one plot per region. Region names are read from the CSV file,
                            so they reflect any regional aggregation produced by the query.''')

        parser.add_argument('-c', '--columns', default="output",
                            help='''Specify the column whose values identify the segments in the stacked
                            bar chart. (These appear in the legend.)''')

        parser.add_argument('-C', '--constraint',
                            help='''Apply a constraint to limit the rows of data to plot. The constraint
                            can be any constraint string that is valid for the DataFrame.query() method,
                            e.g., -C 'input == "biomass"'
                            ''')

        parser.add_argument('-d', '--outputDir', default=".",
                            help='''The directory into which to write image files. Default is "."''')

        parser.add_argument('-D', '--workingDir', default='.',
                            help='''The directory to change to before performing any operations''')

        parser.add_argument('-e', '--enumerate', action="store_true",
                            help='''Prefix image filenames with sequential number for easy reference.
                            Used only with --fromFile''')

        parser.add_argument('-f', '--fromFile',
                            help='''A file from which to read argument strings, one per line.
                            These are read as if chartGCAM.py were called on each line individually,
                            but avoiding the ~2 sec startup time for the bigger python packages.''')

        parser.add_argument('-F', '--fuelFile',
                            help='''A file containing the number of EJ of fuel that constitute the shock
                            the differences represent. If provided, the difference values are divided by
                            the quantity given.''')

        parser.add_argument('--format',
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

        parser.add_argument('-L', '--labelColor',
                            help='''Color for the text label, which defaults to lightgrey. Some users may
                            prefer "black", for example. (Implies -l)''')

        parser.add_argument('-m', '--multiplier', type=float,
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
                            help="Open the plot file after generating it.")

        parser.add_argument('-p',  '--palette', # "hls",
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

        parser.add_argument('-u', '--unstacked',
                            help='''Draw an unstacked bar plot for the column given as an argument to this
                            option, showing three groups of bars: the region, all other regions, and the total.''')

        parser.add_argument('-v', '--valueCol',
                            help='''Identify a column to plot for unstacked bar plots. If not specified,
                            values are summed across years.''')

        parser.add_argument('-x', '--suffix',
                            help='''A suffix to append to the basename of the input csv file to create the
                            name for the output file. For example, if processing my_data.csv, indicating
                            -x '-by-region.pdf' results in an output file named my_data-by-region.pdf.''')

        parser.add_argument('-X', '--xlabel', default="",
                            help='''Defines a label for the X-axis; defaults to blank. LaTeX math language
                            is supported. (See the -T flag for more info.)''')

        parser.add_argument('-Y', '--ylabel', default="EJ",
                            help='''Label for the Y-axis; defaults to "EJ". LaTeX math language
                            is supported. (See the -T flag for more info.)''')

        parser.add_argument('-y', '--years', default="",
                            help='''Takes a parameter of the form XXXX-YYYY, indicating start and end
                            years of interest. Data for all other years are dropped.''')

        parser.add_argument('--ymax', type=float,
                            help='''Set the scale of a figure by indicating the value to show as the
                            maximum Y value. (By default, scale is set according to the data.)''')

        parser.add_argument('--ymin', type=float,
                            help='''Set the scale of a figure by indicating the value (given as abs(value),
                            but used as -value) to show as the minimum Y value''')

        parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + VERSION)

        parser.add_argument('-z', '--zeroLine', action="store_true",
                                help='''Whether to show a line at Y=0''')
        #
        # For manually tweaking figure layout
        #
        parser.add_argument('--legendY', type=float,
                            help='''The Y position of the legend. Useful for fixing poorly formatted figures.
                            Note that to pass a negative value, use the syntax --legendY="-xxx.xxx", otherwise
                            the hyphen is interpreted as indicating a command-line argument.''')

        parser.add_argument('--barWidth', type=float, default=0.5,
                            help='''The relative width of bars. Helpful when plotting only 1 or 2 bar, so they
                            aren't obnoxiously wide. Default is 0.5''')

        return parser


    def run(self, args, tool):
        driver(args, tool, self.parser)
