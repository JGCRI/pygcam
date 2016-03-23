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

#%matplotlib inline

_logger = getLogger(__name__)


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
    verbose    = args.verbose

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

                argsNS = argparse.Namespace()
                for key, value in argDict.iteritems():
                    setattr(argsNS, key, value)

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
