'''
.. Created on: 2/12/15
   Common functions and data

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import argparse
import os

from .matplotlibFix import plt
from matplotlib.ticker import FuncFormatter

import numpy as np
import seaborn as sns
import shlex

from .config import pathjoin, unixPath
from .error import CommandlineError
from .log import getLogger
from .query import dropExtraCols, readCsv
from .utils import systemOpenFile, digitColumns

_logger = getLogger(__name__)

def setupPalette(count, pal=None):
    # See http://xkcd.com/color/rgb/. These were chosen to be different "enough".
    colors = ['grass green', 'canary yellow', 'dirty pink', 'azure', 'tangerine', 'strawberry',
              'yellowish green', 'gold', 'sea blue', 'lavender', 'orange brown', 'turquoise',
              'royal blue', 'cranberry', 'pea green', 'vermillion', 'sandy yellow', 'greyish brown',
              'magenta', 'silver', 'ivory', 'carolina blue', 'very light brown']

    palette = sns.color_palette(palette=pal, n_colors=count) if pal else sns.xkcd_palette(colors)
    sns.set_palette(palette, n_colors=count)


# For publications, call setupPlot("paper", font_scale=1.5)
def setupPlot(context="talk", style="white", font_scale=1.0):
    sns.set_context(context, font_scale=font_scale)
    sns.set_style(style)


def _getFloatFromFile(filename):
    value = None
    if filename:
        with open(filename) as f:
            value = float(f.readline())

    return value


def _amendFilename(filename, suffix):
    '''
    Insert the given suffix into filename before the extension.
    '''
    base, ext = os.path.splitext(filename)
    return base + '-' + suffix + ext


def _finalizeFigure(fig, ax, outFile=None, yFormat=None, sideLabel=False,
                    labelColor=None, transparent=False, openFile=False, closeFig=True):
    if yFormat:
        func = (lambda x, p: format(int(x), ',')) if yFormat == ',' else (lambda x, p: yFormat % x)
        formatter = FuncFormatter(func)
        ax.get_yaxis().set_major_formatter(formatter)

    if sideLabel:
        labelColor = labelColor or 'lightgrey'
        # add the filename down the right side of the plot
        fig.text(1, 0.5, sideLabel, color=labelColor, weight='ultralight', fontsize=7,
                 va='center', ha='right', rotation=270)

    if outFile:
        fig.savefig(outFile, bbox_inches='tight', transparent=transparent)

    if closeFig:
        plt.close(fig)

    if openFile:
        systemOpenFile(outFile)


def plotUnstackedRegionComparison(df, categoryCol, valueCol=None, region=None,
                                  otherRegion='Rest of world', box=False, title='', ncol=3,
                                  xlabel='', ylabel='', ygrid=False, yticks=False,
                                  ymin=None, ymax=None, legendY=None, palette=None,
                                  outFile=None, sideLabel=False, labelColor=None,
                                  yFormat=None, transparent=False, openFile=False, closeFig=True):
    '''
    Plot unstacked bars showing the values for 'categoryCol', summed across years,
    for one region, for everything else, and the totals of the two.
    '''
    setupPlot()

    count = len(df[categoryCol].unique())     # categoryCol = 'land-allocation'
    setupPalette(count, pal=palette)

    fig, ax = plt.subplots(1, 1, figsize=(8, 4))

    plotCol   = '_value_'
    regionCol = '_region_'

    yearCols = digitColumns(df)

    if valueCol:
        # Copy value col so we can delete all yearCols
        df[plotCol] = df[valueCol]
    else:
        # Create and plot a new column with values summed across years
        df[plotCol] = df[yearCols].sum(axis=1)

    df = df.drop(yearCols, axis=1)          # copy to not affect caller's df

    regions = region.split(',')
    reg   = df.query('region in %s' % regions)
    other = df.query('region not in %s' % regions)

    grp = other.groupby(categoryCol)
    otherSums = grp.sum()
    otherSums.reset_index(inplace=True)
    otherSums[regionCol] = otherRegion

    grp = reg.groupby(categoryCol)
    regSum = grp.sum()
    regSum.reset_index(inplace=True)
    regSum[regionCol] = region

    # combine the data for selected region and Rest of World, and sum these
    # to create a Total bar
    totals = regSum.set_index(categoryCol) + otherSums.set_index(categoryCol)
    totals[regionCol] = 'Total'
    totals.reset_index(inplace=True)
    world = regSum.append(otherSums).append(totals)

    ax = sns.barplot(x=regionCol, y=plotCol, hue=categoryCol, data=world, ci=None)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
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

    _finalizeFigure(fig, ax, outFile=outFile, sideLabel=sideLabel, labelColor=labelColor,
                    yFormat=yFormat, transparent=transparent, openFile=openFile, closeFig=closeFig)

    return (fig, ax)


def plotStackedBarsScalar(df, indexCol, columns, valuesCol, box=False, rotation=90,
                          zeroLine=False, title="", xlabel='', ylabel='', ncol=5, ygrid=False,
                          yticks=False, ymin=None, ymax=None, barWidth=0.5, legendY=None,
                          palette=None, outFile=None, sideLabel=False, labelColor=None,
                          yFormat=None, transparent=False, openFile=False, closeFig=True):
    '''
    Plot a stacked bar plot using data in df, given the index column, the
    column holding the values to pivot to columns, and the column holding
    the values. The argument 'ncol' specifies the number of columns with
    which to render the legend.
    '''
    #_logger.debug('plotStackedBarsScalar %s', sideLabel)
    setupPlot()

    colList = [item for item in [indexCol, columns, valuesCol] if item]  # if indexCol is None, this drops it

    # TBD: handle year values as columns to plot
    df2 = df[colList].pivot(index=indexCol, columns=columns, values=valuesCol)

    setupPalette(len(df2.columns), pal=palette)

    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    df2.plot(kind='bar', stacked=True, ax=ax, grid=False, width=barWidth, rot=rotation)

    if box == False:
        sns.despine(left=True)

    if yticks:
        plt.tick_params(axis='y', direction='out', length=5, width=.75,
                        colors='k', left='on', right='off')

    if zeroLine:
        ax.axhline(0, color='k', linewidth=0.75, linestyle='-')

    if ygrid:
        ax.yaxis.grid(color='lightgrey', linestyle='solid')

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    legendY = -0.6 if legendY is None else legendY
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, legendY), ncol=ncol)

    if title:
        ax.set_title(title, y=1.05)

    if ymin is not None or ymax is not None:
        ax.set_autoscale_on(False)
        ax.set_ylim(ymin, ymax)

    _finalizeFigure(fig, ax, outFile=outFile, sideLabel=sideLabel, labelColor=labelColor,
                    yFormat=yFormat, transparent=transparent, openFile=openFile, closeFig=closeFig)

    return (fig, ax)


def plotStackedTimeSeries(df, index='region', xlabel='', ylabel='', ncol=5, box=False,
                          zeroLine=False, title="", ygrid=False, yticks=False,
                          ymin=None, ymax=None, barWidth=0.5, legendY=None, yearStep=5,
                          palette=None, outFile=None, sideLabel=False, labelColor=None,
                          yFormat=None, transparent=False, openFile=False, closeFig=True):
    #_logger.debug('plotStackedTimeSeries %s', sideLabel)
    setupPlot()
    df = dropExtraCols(df, inplace=False)
    grouped = df.groupby(index)
    df2 = grouped.aggregate(np.sum)
    df3 = df2.transpose()

    setupPalette(len(df3.columns), pal=palette)
    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    df3.plot(kind='bar', stacked=True, ax=ax, grid=False, width=barWidth)

    # space out year labels to every 5 years
    locs, labels = plt.xticks()
    yearCols = digitColumns(df)

    if int(yearCols[1]) - int(yearCols[0]) == 1 and yearStep > 1:
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

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    legendY = -0.2 if legendY is None else legendY
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, legendY), ncol=ncol)

    if title:
        ax.set_title(title, y=1.05)

    _finalizeFigure(fig, ax, outFile=outFile, sideLabel=sideLabel, labelColor=labelColor,
                    yFormat=yFormat, transparent=transparent, openFile=openFile, closeFig=closeFig)

    return (fig, ax)


def plotTimeSeries(df, xlabel='', ylabel='', box=False, zeroLine=False, title="", ygrid=False,
                   yticks=False, ymin=None, ymax=None, legend=False, legendY=None, yearStep=5,
                   outFile=None, sideLabel=False, labelColor=None, yFormat=None, transparent=False,
                   openFile=False, closeFig=True):

    setupPlot()
    fig, ax = plt.subplots(1, 1, figsize=(8, 4))

    yearCols = digitColumns(df)

    x = [int(y) for y in yearCols]
    y = list(df[yearCols].iloc[0])
    plt.plot(x, y)

    # TBD: see if this is worth doing
    # space out year labels to every 5 years
    #locs, labels = plt.xticks()
    #plt.xticks(locs[::yearStep], yearCols[::yearStep])

    if box == False:
        sns.despine(left=True)

    if yticks:
        plt.tick_params(axis='y', direction='out', length=5, width=.75,
                        colors='k', left='on', right='off')

    if zeroLine:
        ax.axhline(0, color='k', linewidth=0.75, linestyle='-')

    if ygrid:
        ax.yaxis.grid(color='lightgrey', linestyle='solid')

    if ymin is not None or ymax is not None:
        ax.set_autoscale_on(False)
        ax.set_ylim(ymin, ymax)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if legend:
        legendY = -0.2 if legendY is None else legendY
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, legendY))
    else:
        ax.legend([], frameon=False)

    if title:
        ax.set_title(title, y=1.05)

    _finalizeFigure(fig, ax, outFile=outFile, sideLabel=sideLabel, labelColor=labelColor,
                    yFormat=yFormat, transparent=transparent, openFile=openFile, closeFig=closeFig)

    return (fig, ax)


def chartGCAM(args, num=None, negate=False):
    """
    Generate a chart from GCAM data. This function is called to process
    the ``chart`` sub-command for a single scenario. See the command-line
    arguments to the ``chart`` sub-command for details about `args`.

    :param args: (argparse Namespace) command-line arguments to `chart`
        sub-command
    :param num: (int or None) if not None, a number to prepend to the
        filename to allow files to have numerical sequence.
    :param negate: (bool) if True, all values in year columns are multiplied
        by -1 before plotting.
    :return: none
    """
    barWidth   = args.barWidth
    box        = args.box
    byRegion   = args.byRegion
    columns    = args.columns
    constraint = args.constraint
    csvFile    = args.csvFile
    indexCol   = args.indexCol or None
    label      = args.label
    labelColor = args.labelColor
    legendY    = args.legendY
    ncol       = args.ncol
    openFile   = args.open
    outFile    = args.outFile
    outputDir  = args.outputDir
    palette    = args.palette
    region     = args.region
    rotation   = args.rotation
    sumYears   = args.sumYears
    timeseries = args.timeseries
    title      = args.title
    transparent= args.transparent
    unstackCol  = args.unstackedCol
    unstackReg = args.unstackedRegion
    valueCol   = args.valueCol
    xlabel     = args.xlabel
    yFormat    = args.format
    yearStep   = args.yearStep
    ygrid      = args.ygrid
    ylabel     = args.ylabel
    ymax       = args.ymax
    ymin       = args.ymin
    yticks     = args.yticks
    zeroLine   = args.zeroLine

    # DOCUMENT
    # use outputDir if provided, else use parent dir of outFile
    outputDir = outputDir or os.path.dirname(outFile)

    if not os.path.lexists(outputDir):
        os.mkdir(outputDir, 0o755)

    if outFile:
        imgFile = os.path.basename(outFile)
    else:
        # otherwise compute output filename using outputDir and suffix
        suffix = args.suffix or '.png'
        suffix = '-' + suffix if suffix[0] not in ['.', '-', '_'] else suffix
        filename = os.path.basename(csvFile)
        root, ext = os.path.splitext(filename)
        prefix = "%d-" % num if num else ""
        imgFile = prefix + root + suffix

    outFile = pathjoin(outputDir, imgFile)

    _logger.debug("Generating %s", unixPath(outFile, abspath=True))

    if args.years:
        yearStrs = args.years.split('-')
        assert len(yearStrs) == 2, "Year range must be given as YYYY-YYYY"
    else:
        yearStrs = None

    # e.g., "/Users/rjp/ws-ext/new-reference/batch-new-reference/LUC_Emission_by_Aggregated_LUT_EM-new-reference." % scenario
    df = readCsv(csvFile, skiprows=args.skiprows, years=yearStrs, interpolate=args.interpolate)

    if region:
        try:
            df = df.query('region == "%s"' % region)
        except Exception as e:
            raise CommandlineError("Failed to slice by region %s\n  -- %s" % (region, e))

        if df.shape[0] == 0:
            raise CommandlineError('Region "%s" was not found in %s' % (region, csvFile))

    if constraint:
        try:
            df = df.query(constraint)
        except Exception as e:
            raise CommandlineError("Failed to apply constraint: %s\n  -- %s" % (constraint, e))

    yearCols = digitColumns(df)

    if args.multiplier or args.divisor or negate:
        df = df.copy(deep=True)

    multiplier = args.multiplier or _getFloatFromFile(args.multiplierFile)
    if multiplier:
        df[yearCols] *= multiplier

    divisor = args.divisor or _getFloatFromFile(args.divisorFile)
    if divisor:
        df[yearCols] /= divisor

    if negate:
        outFile = _amendFilename(outFile, 'negated')
        imgFile = _amendFilename(imgFile, 'negated')
        df[yearCols] *= -1

    regions = df.region.unique() if byRegion else [None]    # allows loop to work when not byRegion

    outFileOrig = outFile
    imgFileOrig = imgFile
    titleOrig   = title
    dfOrig = df

    for reg in regions:
        if reg:
            df = dfOrig.query('region == "%s"' % reg)
            title = titleOrig + " (%s)" % reg
            outFile = _amendFilename(outFileOrig, reg)
            imgFile = _amendFilename(imgFileOrig, reg)
            _logger.debug("Processing %s", reg)

        sideLabel = imgFile if label else ''

        if unstackCol:
            otherRegion = 'Rest of world'
            mainRegion  = reg or unstackReg

            plotUnstackedRegionComparison(df, unstackCol, valueCol=valueCol, region=mainRegion,
                                          otherRegion=otherRegion, box=box, title=title, ncol=ncol,
                                          xlabel=xlabel, ylabel=ylabel, ygrid=ygrid, yticks=yticks,
                                          ymin=ymin, ymax=ymax, legendY=legendY, palette=palette,
                                          outFile=outFile, sideLabel=sideLabel, labelColor=labelColor,
                                          yFormat=yFormat, transparent=transparent, openFile=openFile)
        elif sumYears or valueCol:
            if sumYears:
                # create a new value column by summing year columns
                valueCol = '_total_'
                df = df.copy()
                df[valueCol] = df[yearCols].sum(axis=1)

            plotStackedBarsScalar(df, indexCol, columns, valueCol, box=box, zeroLine=zeroLine,
                                  title=title, xlabel=xlabel, ylabel=ylabel, ygrid=ygrid, yticks=yticks,
                                  ymin=ymin, ymax=ymax, rotation=rotation, ncol=ncol, barWidth=barWidth,
                                  legendY=legendY, palette=palette, outFile=outFile, sideLabel=sideLabel,
                                  labelColor=labelColor, yFormat=yFormat, transparent=transparent,
                                  openFile=openFile)

        elif timeseries:
            plotTimeSeries(df, xlabel=xlabel, ylabel=ylabel, box=box, zeroLine=zeroLine, title=title, ygrid=ygrid,
                           yticks=yticks, ymin=ymin, ymax=ymax, legend=False, legendY=legendY, yearStep=yearStep,
                           outFile=outFile, sideLabel=sideLabel, labelColor=labelColor, yFormat=yFormat,
                           transparent=transparent, openFile=openFile)

        else:
            plotStackedTimeSeries(df, index=indexCol, yearStep=yearStep, ygrid=ygrid, yticks=yticks,
                                  ymin=ymin, ymax=ymax, zeroLine=zeroLine, title=title, legendY=legendY,
                                  box=box, xlabel=xlabel, ylabel=ylabel, ncol=ncol, barWidth=barWidth,
                                  palette=palette, outFile=outFile, sideLabel=sideLabel, labelColor=labelColor,
                                  yFormat=yFormat, transparent=transparent, openFile=openFile)

def chartMain(mainArgs, tool, parser):
    # DOCUMENT '*null*', if still useful
    if not mainArgs.fromFile and mainArgs.csvFile == '*null*':
        raise CommandlineError("Must specify a CSV file or use -f flag to read arguments from a file")

    os.chdir(mainArgs.workingDir)

    # Process these separately
    negate = mainArgs.negate
    del mainArgs.negate

    if mainArgs.fromFile:
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

                argsNS  = argparse.Namespace(**argDict)
                allArgs = parser.parse_args(args=fileArgs, namespace=argsNS)

                nextNum = num if enumerate else None
                num += 1

                chartGCAM(allArgs, num=nextNum, negate=negate)

    else:
        chartGCAM(mainArgs, negate=negate)

