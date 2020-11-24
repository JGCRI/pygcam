# Copyright (c) 2012-2015. The Regents of the University of California (Regents)
# and Richard Plevin. See the file COPYRIGHT.txt for details.
import os
import numpy as np
from pygcam.matplotlibFix import plt

import pandas as pd
import seaborn as sns
from six import iteritems
from six.moves import xrange

from pygcam.config import getParam, getParamAsBoolean
from pygcam.log import getLogger
from pygcam.utils import mkdirs

from .error import PygcamMcsSystemError, PygcamMcsUserError
from .Database import getDatabase, Input

_logger = getLogger(__name__)

DEFAULT_BIN_COUNT = 3
DEFAULT_MAX_TORNADO_VARS = 15

def makePlotPath(value, simId):
    plotDir = getParam('MCS.PlotDir')
    subDir  = os.path.join(plotDir, "s%d" % simId)
    mkdirs(subDir)
    plotType = getParam('MCS.PlotType')
    path = os.path.join(subDir, "%s.%s" % (value, plotType))
    #print "Plot path: ", path
    return path

def printExtraText(fig, text, loc='top', color='lightgrey', weight='ultralight', fontsize='xx-small'):
    """
    Print 'extra' text at the top, bottom, right, or left edge of the figure.
    """
    if not text:
        return

    rot = 0
    ha  = 'center'
    va  = 'center'
    x   = 0.5
    y   = 0.5

    if loc == 'top':
        y = 0.98
        va = 'top'
    elif loc == 'bottom':
        y = 0.02
        va = 'bottom'
    elif loc == 'right':
        x = 0.98
        ha = 'right'
        rot = 270
    else: # left
        x = 0.02
        ha = 'left'
        rot = 90

    fig.text(x, y, text, color=color, weight=weight, fontsize=fontsize, va=va, ha=ha, rotation=rot)


def plotHistogram(values, xlabel=None, ylabel=None, title=None, xmin=None, xmax=None,
                  extra=None, extraColor='grey', extraLoc='right',
                  hist=True, showCI=False, showMean=False, showMedian=False,
                  color=None, shade=False, kde=True, show=True, filename=None):

    fig = plt.figure()

    style    = "white"
    colorSet = "Set1"
    sns.set_style(style)
    sns.set_palette(colorSet, desat=0.6)
    red, blue, green, purple = sns.color_palette(colorSet, n_colors=4)

    color = blue if color is None else color
    count = values.count()
    bins  = count // 10 if count > 150 else (count // 5 if count > 50 else (count // 2 if count > 20 else None))
    sns.distplot(values, hist=hist, bins=bins, kde=kde, color=color, kde_kws={'shade': shade})

    #sns.axlabel(xlabel=xlabel, ylabel=ylabel)
    if xlabel:
        plt.xlabel(xlabel) # , size='large')
    if ylabel:
        plt.ylabel(ylabel) # , size='large')

    sns.despine()

    if title:
        t = plt.title(title)
        t.set_y(1.02)

    printExtraText(fig, extra, color=extraColor, loc=extraLoc)

    if xmin is not None or xmax is not None:
        ax = plt.gca()
        ax.set_autoscale_on(False)
        ax.set_xlim(xmin, xmax)

    if showCI or showMean:
        ymin, ymax = plt.ylim()
        xmin, xmax = plt.xlim()
        textSize = 9
        labely   = ymax * 0.95
        deltax   = (xmax-xmin) * 0.01

        if showCI:
            color = red
            ciLow  = np.percentile(values, 2.5)
            ciHigh = np.percentile(values, 97.5)
            plt.axvline(ciLow,  color=color, linestyle='solid', linewidth=2)
            plt.axvline(ciHigh, color=color, linestyle='solid', linewidth=2)
            plt.text(ciLow  + deltax, labely, '2.5%%=%.2f'  % ciLow,  size=textSize, rotation=90, color=color)
            plt.text(ciHigh + deltax, labely, '97.5%%=%.2f' % ciHigh, size=textSize, rotation=90, color=color)

        if showMean:
            color = green
            mean = np.mean(values)
            plt.axvline(mean, color=color, linestyle='solid', linewidth=2)
            plt.text(mean + deltax, labely, 'mean=%.2f' % mean, color=color, size=textSize, rotation=90)

        if showMedian:
            color = purple
            median = np.percentile(values, 50)
            labely = ymax * 0.50
            plt.axvline(median, color=color, linestyle='solid', linewidth=2)
            plt.text(median + deltax, labely, 'median=%.2f' % median, color=color, size=textSize, rotation=90)

    if show:
        plt.show()

    if filename:
        _logger.info("plotHistogram writing to: %s", filename)
        fig.savefig(filename)

    plt.close(fig)


def plotTornado(data, colname='value', labelsize=9, title=None, color=None, height=0.8,
                maxVars=DEFAULT_MAX_TORNADO_VARS, rlabels=None, xlabel='Contribution to variance', figsize=None,
                show=True, filename=None, extra=None, extraColor='grey', extraLoc='right', importanceCSV=None):
    '''
    :param data: A sorted DataFrame or Series indexed by variable name, with
                 column named 'value' and if rlabels is set, a column of that
                 name holding descriptive labels to display.
    :param labelsize: font size for labels
    :param title: If not None, the title to show
    :param color: The color of the horizontal bars
    :param height: Bar height
    :param maxVars: The maximum number of variables to display
    :param rlabels: If not None, the name of a column holding values to show on the right
    :param xlabel: Label for X-axis
    :param figsize: tuple for desired figure size. Defaults to (12,6) if rlabels else (8,6).
    :param show: If True, the figure is displayed on screen
    :param filename: If not None, the figure is saved to this file
    :param extra: Extra text to display in a lower corner of the plot (see extraLoc)
    :param extraColor: (str) color for extra text
    :param extraLoc: (str) location of extra text, i.e., 'right', or 'left'.
    :param importanceCSV: (str) None, or the name of a file into which to save CSV data used to plot the tornado.
    :return: nothing
    '''
    count, cols = data.shape

    if 0 < maxVars < count:
        data = data[:maxVars]            # Truncate the DF to the top "maxVars" rows
        count = maxVars

    # Reverse the order so the larger (abs) values are at the top
    revIndex = list(reversed(data.index))
    data = data.loc[revIndex]

    itemNums = list(range(count))
    # ypos = np.array(itemNums) - 0.08   # goose the values to better center labels

    if not figsize:
        figsize = (12, 6) if rlabels else (8, 6)

    #fig = plt.figure(figsize=figsize)
    #fig = plt.figure(facecolor='white', figsize=figsize)
    #plt.plot()

    # if it's a dataframe, we expect to find the data in the value column
    values = data if isinstance(data, pd.Series) else data[colname]

    if importanceCSV:
        values.to_csv(importanceCSV)

    if color is None:
        color = sns.color_palette("deep", 1)

    # TBD: This looks like it has been resolved; try this again using seaborn
    # tried pandas; most of the following manipulations can be handled in one call, but
    # it introduced an ugly dashed line at x=0 which I didn't see how to remove. Maybe
    # address this again if seaborn adds a horizontal bar chart.
    values.plot(kind="barh", color=sns.color_palette("deep", 1), figsize=figsize,
                xlim=(-1, 1), ylim=(-1, count), xticks=np.arange(-0.8, 1, 0.2))

    plt.xlabel(xlabel)

    right = 0.6 if rlabels else 0.9
    plt.subplots_adjust(left=0.3, bottom=0.1, right=right, top=0.9)  # more room for rlabels

    fig = plt.gcf()
    ax  = plt.gca()

    ax.xaxis.tick_top()
    ax.tick_params(axis='x', labelsize=labelsize)
    ax.tick_params(axis='y', labelsize=labelsize)
    ax.set_yticklabels(data.index)
    ax.set_yticks(itemNums)

    if rlabels:
        ax2 = plt.twinx()
        plt.ylim(-1, count)
        ax2.tick_params(axis='y', labelsize=labelsize)
        ax2.set_yticklabels(data[rlabels])
        ax2.set_yticks(itemNums)

        for t in ax2.xaxis.get_major_ticks() + ax2.yaxis.get_major_ticks():
            t.tick1On = False
            t.tick2On = False

    # show vertical grid lines only
    ax.yaxis.grid(False)
    ax.xaxis.grid(True)

    # Remove tickmarks from both axes
    for t in ax.xaxis.get_major_ticks() + ax.yaxis.get_major_ticks():
        t.tick1On = False
        t.tick2On = False

    if title:
        plt.title(title, y=1.05)  # move title up to avoid tick labels

    printExtraText(fig, extra, loc=extraLoc, color=extraColor)

    if show:
        plt.show()

    if filename:
        _logger.debug("Saving tornado plot to %s" % filename)
        fig.savefig(filename)

    plt.close(fig)


def plotConvergence(simId, expName, paramName, values, show=True, save=False):
    '''
    Examine the first 3 moments (mean, std, skewness) in the data set
    for increasing number (N) of values, growing by the given increment.
    Optionally plot the relationship between each of the moments and N,
    so we can when (if) convergence occurs.
    '''
    _logger.debug("Generating convergence plots...")
    count = values.count()
    results = {'Mean': [], 'Stdev': [], 'Skewness': [], '95% CI': []}

    increment = min(100, count // 20)
    nValues = list(range(increment, count + increment - 1, increment))

    for N in nValues:
        sublist = values[:N]
        results['Mean'].append(sublist.mean())
        results['Stdev'].append(sublist.std())
        results['Skewness'].append(sublist.skew())

        ciLow  = np.percentile(sublist, 2.5)
        ciHigh = np.percentile(sublist, 97.5)
        results['95% CI'].append(ciHigh - ciLow)

    # Insert zero value at position 0 for all lists to ensure proper scaling
    nValues.insert(0,0)
    for dataList in results.values():
        dataList.insert(0,0)

    labelsize=12
    for key, values in iteritems(results):
        plt.clf()   # clear previous figure
        ax = plt.gca()
        ax.tick_params(axis='x', labelsize=labelsize)
        ax.tick_params(axis='y', labelsize=labelsize)
        plt.plot(nValues, results[key])
        plt.title("%s" % paramName, size='large')
        ax.yaxis.grid(False)
        ax.xaxis.grid(True)
        plt.xlabel('Trials', size='large')
        plt.ylabel(key, size='large')
        plt.figtext(0.12, 0.02, "SimId=%d, Exp=%s" % (simId, expName),
                    color='black', weight='roman', size='x-small')

        if save:
            filename = makePlotPath("%s-s%02d-%s-%s" % (expName, simId, paramName, key), simId)
            _logger.debug("Saving convergence plot to %s" % filename)
            plt.savefig(filename)

        if show:
            plt.show()

    fig = plt.gcf()
    plt.close(fig)


# Could use series.describe() but I like this format better
def printStats(series):
    name   = series.name
    count  = series.count()
    mean   = series.mean()
    median = series.median()
    stdev  = series.std()
    skew   = series.skew()
    minv   = series.min()
    maxv   = series.max()
    ciLow  = series.quantile(0.025)
    ciHigh = series.quantile(0.975)
    ciLower  = series.quantile(0.01)
    ciHigher = series.quantile(0.99)

    print('''
%s:
     count: %d
      mean: %.2f
    median: %.2f
     stdev: %.2f
      skew: %.2f
       min: %.2f
       max: %.2f
    95%% CI: [%.2f, %.2f]
    99%% CI: [%.2f, %.2f]''' % (name, count, mean, median, stdev, skew, minv, maxv,
                                ciLow, ciHigh, ciLower, ciHigher))

def normalizeSeries(series):
    'Normalize a series by dividing each element by the sum'
    total = series.sum()
    return series / total

def normalizeDF(df):
    '''
    Perform max-min normalization on all columns.
    :param df: (pandas.DataFrame) data to operate on
    :return: (pandas.DataFrame) normalized values.
    '''
    dfMin = df.min()
    df = (df - dfMin) / (df.max() - dfMin)
    return df

def spearmanCorrelation(inputs, results):
    '''
    Compute Spearman ranked correlation and normalized Spearman ranked
    correlation between values in a DataFrame of inputs and a Series of
    results. Returns a Series with the spearman rank correlation values.

    :param inputs: (pandas.DataFrame) input values for each parameter and trial
    :param results: (pandas.Series) values for one model result, per trial
    :return: (pandas.Series) rank correlations of each input to the output vector.
    '''
    corrList = [results.corr(inputs[col], method='spearman') for col in inputs.columns]
    spearman = pd.Series(data=corrList, index=inputs.columns, name='spearman')

    return spearman


def plotSensitivityResults(varName, data, filename=None, extra=None, maxVars=None, printIt=True):
    '''
    Prints results and generates a tornado plot with normalized squares of Spearman
    rank correlations between an output variable and all input variables.
    '''
    # Sort descending by absolute value (normalized are all positive from squaring)
    data.sort_values(by=['normalized'], ascending=False, inplace=True)

    if printIt:
        print("UNCERTAINTY IMPORTANCE (%s)" % varName)
        print("----------------------")
        print(data.to_string(columns=['spearman', 'value'], float_format="{:4.2f}".format))

    title = 'Sensitivity of %s' % varName
    plotTornado(data, title=title, show=False, filename=filename, extra=extra, maxVars=maxVars)

# Deprecated?
def plotGroupSensitivityResults(varName, data, filename=None, extra=None, maxVars=None, printIt=True):
    '''
    Sum the normalized contribution to variance for subscripted parameters,
    along with contribution from unsubscripted ones. For example, we sum
    the contributions for "ETA[1,5]" and "ETA[1,6]" into "ETA".
    '''
    totals = pd.Series(name='totals')

    for idx, row in data.iterrows():
        # Lop off bracketed indices at first '['.
        # e.g., from "ETA[1,5]", we'll extract "ETA"
        pos = idx.find('[')
        paramName = idx if pos < 0 else idx[0:pos]

        # Sum the values; initialize on demand
        try:
            totals[paramName] += row.value
        except KeyError:
            totals[paramName]  = row.value

    df = pd.DataFrame(totals)

    negatives = (totals < 0)
    df['sign'] = 1
    df.ix[negatives, 'sign'] = -1

    df['absval']    = totals * df['sign']
    df['normalize'] = normalizeSeries(df['absval'])
    df['value']     = df['normalize'] * df['sign']

    # Sort by absolute value
    df.sort_values('absval', ascending=False, inplace=True)

    db = getDatabase()
    with db.sessionScope() as session:
        result = session.query(Input.paramName, Input.description).distinct().all()

    resultDF = pd.DataFrame(result)
    resultDF.fillna('')
    df['description'] = resultDF['description']

    if printIt:
        print("\nPARAMETER GROUPS (%s)" % varName)
        print("----------------")
        print(df.to_string(columns=['value', 'description'], float_format="{:4.2f}".format))

    title = 'Sensitivity of %s' % varName
    plotTornado(df, title=title, figsize=None, show=False, filename=filename, maxVars=maxVars, extra=extra)


def plotInputDistributions(simId, inputDF):
    '''Plot the input values individually to test that the distributions are as expected'''

    showHist  = True
    showKDE   = False
    showShade = getParamAsBoolean('MCS.PlotShowShading')

    for heading, series in iteritems(inputDF):
        plotHistogram(series, showCI=False,
                      xlabel='Parameter value', ylabel='Probability density',
                      title='Distribution for values of %s' % heading,
                      color=None, hist=showHist, kde=showKDE, shade=showShade,
                      show=False, filename=makePlotPath(heading, simId))


def plotOutputDistribution(simId, expName, resultSeries, resultName, xlabel, trials):
    filename = makePlotPath('%s-s%02d-%s-%d-trials' % (expName, simId, resultName, resultSeries.count()), simId)

    showHist  = getParamAsBoolean('MCS.PlotShowHistogram')
    showKDE   = getParamAsBoolean('MCS.PlotShowKDE')
    showShade = getParamAsBoolean('MCS.PlotShowShading')

    numValues = resultSeries.count()

    db = getDatabase()
    xlabel = db.getOutputUnits(resultName)

    plotHistogram(resultSeries, xlabel=xlabel, ylabel='Probability density',
                  title='Frequency distribution for %s' % resultName,
                  extra='SimId=%d, Exp=%s, Trials=%d/%d' % (simId, expName, numValues, trials),
                  color=None, hist=showHist, kde=showKDE, shade=showShade,
                  showCI=True, showMean=True, showMedian=True, show=False, filename=filename)

# TBD: If row/col are obsolete, this info can now be read from trialData.csv or data.sa
def readParameterValues(simId, trials):
    def makeKey(paramName, row, col):
        return paramName
        #return "%s[%d][%d]" % (paramName, row, col) if row or col else paramName

    db = getDatabase()

    paramTuples = db.getParameters()        # Returns paramName, row, col
    paramNames  = [makeKey(*tup) for tup in paramTuples]   # names like "foo[1][14]"
    inputDF     = pd.DataFrame(index=xrange(trials), columns=paramNames, dtype=float)
    _logger.debug("Found %d distinct parameter names" % len(paramNames))

    paramValues = db.getParameterValues(simId, asDataFrame=False)
    numParams = len(paramValues)
    _logger.info('%d parameter values read' % numParams)

    for row, col, value, trialNum, pname in paramValues:
        key = makeKey(pname, row, col)
        inputDF[key][trialNum] = value

    return inputDF

def _fixColname(name):
    pos = name.find('[')
    return name[:pos] if pos >= 0 else name

def exportInputs(exportFile, inputs):
    df = inputs.copy()

    # remove [x][y] from colnames
    df.columns = [_fixColname(c) for c in df.columns]

    _logger.debug("Exporting data to '%s'", exportFile)
    df.to_csv(exportFile)

# export all available results and their matching inputs for a single scenario,
# in wide format, with 'trialNum' as index, each input/result in a column.
def exportAllInputsOutputs(simId, expName, inputDF, exportFile, sep=','):
    df = None
    db = getDatabase()
    resultList = db.getOutputsWithValues(simId, expName)

    inputDF.index.rename('trialNum', inplace=True)

    for resultName in resultList:
        resultDf = db.getOutValues(simId, expName, resultName)
        if resultDf is None:
            raise PygcamMcsUserError('No results were found for sim %d, experiment %s, result %s' % (simId, expName, resultName))

        # Copy inputs for which there are outputs
        if df is None:
            df = inputDF.iloc[resultDf.index].copy()

        # Add each output
        df[resultName] = resultDf[resultName]

    _logger.debug("Exporting inputs and results to '%s'", exportFile)
    df.to_csv(exportFile, sep=sep)
    return df

def exportResults(simId, resultList, expList, exportFile, sep=','):
    db = getDatabase()
    df = None

    for expName in expList:
        for resultName in resultList:
            # resultDf has 'trialNum' as index, 'value' holds float value
            resultDf = db.getOutValues(simId, expName, resultName)
            if resultDf is None:
                raise PygcamMcsUserError('No results were found for sim %d, experiment %s, result %s' % (simId, expName, resultName))

            # Add columns needed for boxplots
            resultDf['expName'] = expName
            resultDf['resultName'] = resultName

            resultDf.rename(columns = {resultName:'value'}, inplace=True)

            if df is None:
                df = resultDf
            else:
                df = pd.concat([df, resultDf])

    _logger.debug("Exporting results to '%s'", exportFile)
    df.to_csv(exportFile, sep=sep)

#
# Based on ema_workbench/core/utils.py:save_results()
#
def saveForEMA(simId, expNames, resultNames, inputDF, filename):
    """
    Save simulation results to the specified tar.gz file. The results are
    stored as csv files. There is an x.csv, and a csv for each outcome. In
    addition, there is a metadata csv which contains the datatype information
    for each of the columns in the x array. Unlike the version of this function
    in the EMA Workbench, this version collects data from the SQL database to
    generate a file in the required format.

    :param simId: (int) the id of the simulation
    :param expNames: (list of str) the names of the experiments to save results for
    :param resultNames: (list of str) all model input values, each row holding values for 1 trial
    :param inputDF: (pandas.DataFrame) the input data
    :param filename: (str) the path of the file
    :raises: IOError if file not found
    :return: none
    """
    from io import BytesIO
    import tarfile
    import time

    def add_file(tgzfile, string_to_add, filename):
        tarinfo = tarfile.TarInfo(filename)
        tarinfo.size = len(string_to_add)
        tarinfo.mode = 0o644
        tarinfo.mtime = time.time()
        tgzfile.addfile(tarinfo, BytesIO(string_to_add.encode('UTF-8')))

    db = getDatabase()

    # InValue.row, InValue.col, InValue.value, Trial.trialNum, Input.paramName
    rows = inputDF.shape[0]

    with tarfile.open(filename, 'w:gz') as z:
        # Write the input values to the zipfile
        expData = inputDF.to_csv(None, sep=',', index=False) # index_label='trialNum'
        add_file(z, expData, 'experiments.csv')

        # Write experiment metadata
        dtypes = inputDF.dtypes
        # list(dtypes.items()) produces results like:
        # [('A', dtype('int64')), ('B', dtype('int64')), ('C', dtype('float64'))] and
        # map(lambda dt: (dt[0], dt[1].descr), dtypes.items()) produces:
        # [('A', [('', '<i8')]), ('B', [('', '<i8')]), ('C', [('', '<f8')])]
        # So, map(lambda dt: (dt[0], dt[1].descr[0][1]), dtypes.items()) produces:
        # [('A', '<i8'), ('B', '<i8'), ('C', '<f8')]
        tuples = [(dt[0], dt[1].descr[0][1]) for dt in iteritems(dtypes)]
        tuples = map(lambda dt: (dt[0], dt[1].descr[0][1]), iteritems(dtypes))
        strings = ["{},{}".format(name, dtype) for name, dtype in tuples]
        fileText = "\n".join(strings) + '\n'
        add_file(z, fileText, 'experiments metadata.csv')

        # Write outcome metadata    # TBD: deal with timeseries

        # outcome_meta = ["{},{}".format(outcome, ','.join(outcomes[outcome].shape))
        #                 for outcome in resultNames]
        strings = ["{},{}".format(resultName, rows) for resultName in resultNames]
        fileText = "\n".join(strings) + '\n'
        add_file(z, fileText, "outcomes metadata.csv")

        # Write outcomes
        for expName in expNames:
            for resultName in resultNames:
                outValueDF = db.getOutValues(simId, expName, resultName) # cols are trialNum and value; might need to do outValueDF[resultName].to_csv
                allTrialsDF = pd.DataFrame(index=xrange(rows))           # ensure that all trials are represented (with NA if need be)
                allTrialsDF[resultName] = outValueDF[resultName]
                fileText = allTrialsDF.to_csv(None, header=False, index=False)
                fname = "{}-{}.csv".format(resultName, expName)
                add_file(z, fileText, fname)

    print("Results saved successfully to {}".format(filename))

def getCorrDF(inputs, output):
    '''
    Generate a DataFrame with rank correlations between each input vector
    and the given output vector, and sort by abs(correlation), descending.

    :param inputs: (pandas.DataFrame) input values for each parameter and trial
    :param output: (pandas.Series) output values for one result, per trial
    :return: (pandas.DataFrame) two columns, "spearman" and "abs", the prior
       holding the Spearman correlations between each input and the output
       vector, and the latter with the absolute values of these correlations.
       The DataFrame is indexed by variable name and sorted by "abs", descending.
    '''
    corrDF = pd.DataFrame(spearmanCorrelation(inputs, output))
    corrDF['abs'] = corrDF.spearman.abs()
    corrDF.sort_values('abs', ascending=False, inplace=True)
    return corrDF

def binColumns(inputDF, bins=DEFAULT_BIN_COUNT):
    columns = inputDF.columns
    binned = pd.DataFrame(columns=columns)
    for col in columns:
        s = inputDF[col]
        binned[col] = pd.cut(s, bins, labels=False)

    return binned

# TBD: Finish refactoring this
class Analysis(object):
    def __init__(self, simId, scenarioNames, resultNames, limit=0):
        self.simId = simId
        self.scenarioNames = scenarioNames
        self.resultNames = resultNames
        self.limit = limit

        self.db = getDatabase()
        self.trials = self.db.getTrialCount(simId) if limit <= 0 else limit

        if not self.trials:
            raise PygcamMcsUserError('No trials were found for simId %d' % simId)

        self.inputDF = None
        self.resultDict = {}   # DFs of results for a scenario, keyed by scenario name

    def getInputs(self):
        '''
        Read inputs for the given simId. If already read, return the
        cached DataFrame.

        :return: (pandas.DataFrame) input values for all parameters
        '''
        if self.inputDF is not None:
            return self.inputDF

        self.inputDF = df = readParameterValues(self.simId, self.trials)
        # TBD: [x][y] is probably obsolete
        # remove [x][y] subscripts from colnames
        df.columns = [_fixColname(c) for c in df.columns]
        return df

    def exportInputs(self, exportFile, columns=None, sep=','):
        '''
        Export the inputs for the current simulation / scenario. If
        provided, limit the set of inputs to the named columns.

        :param columns: (iterable of str) names of columns to export
        :return: none
        '''
        df = self.getInputs()
        if columns:
            df = df[columns]

        _logger.debug("Exporting data to '%s'", exportFile)
        df.to_csv(exportFile, sep=sep)

    def getResults(self, scenarioList=None, resultList=None):
        '''
        Get the results for the given result names, or, if none are
        specified, for the results identified when at instantiation.
        Results are cached and thus read only once from the database.

        :param scenarioList: (iterable of str) the scenarios for which
           to get results
        :param resultList: (iterable of str) the results to export
        :param sep: (str) column separator to use in output file
        :return: none
        '''
        db = self.db
        simId = self.simId
        resultDict = self.resultDict

        resultList = resultList or self.resultNames
        scenarioList = scenarioList or self.scenarioNames

        for scenario in scenarioList:
            resultDF = resultDict.get(scenario)

            for resultName in resultList:
                # returns DF with 'trialNum' as index, 'value' holds float value
                if resultDF is None or resultName not in resultDF.columns:
                    values = db.getOutValues(simId, scenario, resultName, limit=self.limit)
                    if values is None:
                        raise PygcamMcsUserError(
                            'No results were found for sim %d, experiment %s, result %s' % (simId, scenario, resultName))

                    resultDF = values if not resultDF else pd.concat([resultDF, values])

            resultDict[scenario] = resultDF

        return resultDict

    def exportResults(self, exportFile, scenarioList=None, resultList=None, sep=','):
        '''
        Export the results for the given scenario and result names, or, if not
        specified, the ones identified when at instantiation.

        :param exportFile: (str) filename to create
        :param scenList: (iterable of str) the scenarios for which to export results
        :param resultList: (iterable of str) the results to export
        :param sep: (str) column separator to use in output file
        :return: none
        '''
        resultDict = self.getResults(scenarioList=scenarioList, resultList=resultList)
        exportDF = None

        for scenario in scenarioList:
            resultDF = resultDict[scenario]

            for resultName in resultList:
                # The resultDF has 'trialNum' as index, 'value' holds float value.
                # Denormalize these to store all scenarios' results in one DF.
                df = resultDF[resultName].copy()
                df.rename(columns={resultName: 'value'}, inplace=True)

                # Add columns needed for boxplots
                df['expName'] = scenario
                df['resultName'] = resultName

                # concatenate each result set below the accumulated data
                exportDF = pd.concat([exportDF, df]) if exportDF else df

        _logger.debug("Exporting results to '%s'", exportFile)
        df.to_csv(exportFile, sep=sep)

    def plotInputDistributions(self):
        '''Plot the input values individually to test that the distributions are as expected'''

        showHist = True
        showKDE = False
        showShade = getParamAsBoolean('MCS.PlotShowShading')
        inputDF = self.getInputs()
        simId = self.simId

        for heading, series in iteritems(inputDF):
            plotHistogram(series, showCI=False,
                          xlabel='Parameter value', ylabel='Probability density',
                          title='Distribution for values of %s' % heading,
                          color=None, hist=showHist, kde=showKDE, shade=showShade,
                          show=False, filename=makePlotPath(heading, simId))

    def plotUncertaintyImportance(self, inputDF, resultSeries, filename=None,
                                  extra=None, printIt=True):
        '''
        Prints results and generates a tornado plot with normalized squares of Spearman
        rank correlations between an output variable and all input variables.
        '''
        spearman = spearmanCorrelation(inputDF, resultSeries)
        data = pd.DataFrame(spearman)
        squared = spearman ** 2
        data['normalized'] = squared / squared.sum()
        data['sign'] = 1
        data.ix[(data.spearman < 0), 'sign'] = -1
        data['value'] = data.normalized * data.sign     # normalized squares with signs restored

        # Sort descending by normalized values (all are positive from squaring)
        data.sort(columns=['normalized'], ascending=False, inplace=True)

        varName = resultSeries.name

        if printIt:
            print("UNCERTAINTY IMPORTANCE (%s)" % varName)
            print("----------------------")
            print(data.to_string(columns=['spearman', 'value'], float_format="{:4.2f}".format))

        title = 'Sensitivity of %s' % varName
        plotTornado(data, title=title, show=False, filename=filename, extra=extra)

    def plotParallelCoordinates(self, inputDF, resultSeries, numInputs=None,
                                filename=None, extra=None, inputBins=None,
                                outputLabels=['Low', 'Medium', 'High'],
                                quantiles=False, normalize=True, invert=False,
                                show=False, title=None, rotation=None):
        '''
        Plot a parallel coordinates figure.

        :param inputDF: (pandas.DataFrame) trial inputs
        :param resultSeries: (pandas.Series) results to categorize lines
        :param numInputs: (int) the number of inputs to plot, choosing these
           from the most-highly correlated (or anti-correlated) to the lowest.
           If not provided, all variables in `inputDF` are plotted.
        :param filename: (str) name of graphic file to create
        :param extra: (str) text to draw down the right side, labeling the figure
        :param inputBins: (int) the number of bins to use to quantize inputs
        :param quantiles: (bool) create bins with equal numbers of values rather than
           bins of equal boundary widths. (In pandas terms, use qcut rather than cut.)
        :param normalize: (bool) normalize values to percentages of the range for each var.
        :param invert: (bool) Plot negatively correlated values as (1 - x) rather than (x).
        :param outputLabels: (list of str) labels to assign to outputs (and thus the number
           of bins to group the outputs into.)
        :param title: (str) Figure title
        :param show: (bool) If True, show the figure.
        :return: none
        '''
        from pandas.plotting import parallel_coordinates

        corrDF = getCorrDF(inputDF, resultSeries)
        numInputs = numInputs or len(corrDF)
        cols = list(corrDF.index[:numInputs])

        # isolate the top-correlated columns
        inputDF = inputDF[cols]

        # trim down to trials with result (in case of failures)
        inputDF = inputDF.ix[resultSeries.index]

        if normalize or invert:
            inputDF = normalizeDF(inputDF)

        if invert:
            for name in cols:
                # flip neg. correlated values to reduce line crossings
                if corrDF.spearman[name] < 0:
                    inputDF[name] = 1 - inputDF[name]
                    inputDF.rename(columns={name: "(1 - %s)" % name}, inplace=True)
            cols = inputDF.columns

        # optionally quantize inputs into the given number of bins
        plotDF = binColumns(inputDF, bins=inputBins) if inputBins else inputDF.copy()

        # split results into equal-size or equal-quantile bins
        cutFunc = pd.qcut if quantiles else pd.cut
        plotDF['category'] = cutFunc(resultSeries, len(outputLabels), labels=outputLabels)

        colormap = 'rainbow'
        alpha = 0.4

        # color = [
        #     [0.8, 0.0, 0.1, alpha],
        #     [0.0, 0.8, 0.1, alpha],
        #     [0.1, 0.1, 0.8, alpha],
        # ]
        parallel_coordinates(plotDF, 'category', cols=cols, alpha=alpha,
                             #color=color,
                             colormap=colormap,
                             )
        fig = plt.gcf()
        fig.canvas.draw()       # so that ticks / labels are generated

        if rotation is not None:
            plt.xticks(rotation=rotation)

        # Labels can come out as follows for, say, 4 bins:
        # [u'', u'0.0', u'0.5', u'1.0', u'1.5', u'2.0', u'2.5', u'3.0', u'']
        # We eliminate the "x.5" labels by substituting '' and convert the remaining
        # numerical values to integers (i.e., eliminating ".0")
        def _fixTick(text):
            if inputBins:
                return '' if (not text or text.endswith('.5')) else str(int(float(text)))

            # If not binning, just show values on Y-axis
            return text

        locs, ylabels = plt.yticks()
        ylabels = [_fixTick(t._text) for t in ylabels]
        plt.yticks(locs, ylabels)

        if extra:
            printExtraText(fig, extra, loc='top', color='lightgrey', weight='ultralight', fontsize='xx-small')

        plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        if title:
            plt.title(title)

        if show:
            plt.show()

        if filename:
            _logger.debug("Saving parallel coordinates plot to %s" % filename)
            plt.savefig(filename, bbox_inches='tight')

        plt.close(fig)

# TBD:
def analyzeSimulationNew(args):
    '''
    Analyze a simulation by reading parameters and results from the database.
    '''
    simId       = args.simId
    expNames    = args.expName
    plotHist    = args.plot
    stats       = args.stats
    importance  = args.importance
    groups      = args.groups
    plotInputs  = args.plotInputs
    convergence = args.convergence
    resultName  = args.resultName
    xlabel      = args.xlabel
    inputsFile  = args.exportInputs
    resultFile  = args.resultFile
    exportEMA   = args.exportEMA
    minimum     = args.min
    maximum     = args.max
    parallel    = args.parallel

    anaObj = Analysis(args.simId, args.scenarioNames, args.resultNames, args.limit)
    trials = anaObj.trials

    if inputsFile:
        anaObj.exportInputs(inputsFile)

    if not (expNames and resultName):
        raise PygcamMcsUserError("expName and resultName must be specified")

    expList = expNames.split(',')
    resultList = resultName.split(',')

    if resultFile:
        anaObj.exportResults(resultFile, scenarioList=expList, resultList=resultList)
        return

    inputDF = anaObj.getInputs()
    inputRows, inputCols = inputDF.shape

    if exportEMA:
        saveForEMA(simId, expList, resultList, inputDF, exportEMA)
        return

    if plotInputs:
        plotInputDistributions()

    if not (importance or groups or plotHist or convergence or stats):
        return

    resultsDict = anaObj.getResults(scenarioList=expList, resultList=[resultName])

    for expName in expList:
        resultDF = resultsDict[expName]

        if resultDF is None:
            raise PygcamMcsSystemError('analyze: No results for simId=%d, expName=%s' % (simId, expName))

        if maximum is not None:
            before = resultDF.shape[0]
            resultDF = resultDF[resultDF[resultName] <= maximum]
            after = resultDF.shape[0]
            _logger.debug('Applying maximum value (%f) eliminated %d rows.', maximum, before - after)

        if minimum is not None:
            before = resultDF.shape[0]
            resultDF = resultDF[resultDF[resultName] >= minimum]
            after = resultDF.shape[0]
            _logger.debug('Applying minimum value (%f) eliminated %d rows.', minimum, before - after)

        resultSeries = resultDF[resultName]
        numResults = resultSeries.count()

        if plotHist:
            plotOutputDistribution(simId, expName, resultSeries, resultName, xlabel, trials)

        if stats:
            printStats(resultSeries)    # TBD: use resultSeries.describe() instead?

        if convergence:
            plotConvergence(simId, expName, resultName, resultSeries, show=False, save=True)

        if (importance or groups or inputsFile) and (numResults != trials or numResults != inputRows):
            _logger.info("SimID %d has %d trials, %d input rows, and %d results",
                         simId, trials, inputRows, numResults)

        if importance or groups or parallel:
            inputsWithResults = inputDF.ix[resultDF.index]

            # Drop any inputs with names ending in '-linked' since these are an artifact
            linked = [s for s in inputsWithResults.columns if s.endswith('-linked')]
            if linked:
                inputsWithResults.drop(linked, axis=1, inplace=True)

            extraText = 'SimId=%d, Exp=%s, Trials=%d/%d' % (simId, expName, numResults, trials)

            # TBD: eliminate 'groups' and call it importance instead.
            if importance or groups:
                basename = '%s-s%02d-%s-sensitivity' % (expName, simId, resultName)
                filename = makePlotPath(basename, simId)

                anaObj.plotUncertaintyImportance(inputsWithResults, resultSeries,
                                                 filename=filename, extra=extraText)

            # TBD: drop this from 'analyze' command?
            if parallel:
                basename = '%s-s%02d-%s-parallel' % (expName, simId, resultName)
                filename = makePlotPath(basename, simId)

                # TBD: plot parallel coordinates figure
                anaObj.plotParallelCoordinates(inputsWithResults, resultSeries,
                                               filename=filename, extra=extraText)


def analyzeSimulation(args):
    '''
    Analyze a simulation by reading parameters and results from the database.
    '''
    simId       = args.simId
    expNames    = args.expName
    plotHist    = args.plot
    stats       = args.stats
    importance  = args.importance
    groups      = args.groups
    plotInputs  = args.plotInputs
    convergence = args.convergence
    resultName  = args.resultName
    limit       = args.limit
    maxVars     = args.maxVars
    xlabel      = args.xlabel
    inputsFile  = args.exportInputs
    resultFile  = args.resultFile
    exportEMA   = args.exportEMA
    exportAll   = args.exportAll
    minimum     = args.min
    maximum     = args.max

    # Determine which inputs are required for each option
    requireInputs   = (exportAll or exportEMA or groups or importance or plotInputs or inputsFile)
    requireScenario = (exportAll or exportEMA or groups or importance or resultFile or plotHist or convergence or stats)
    requireResult   = (groups or importance or resultFile or plotHist or convergence or stats)

    if requireResult and not resultName:
        raise PygcamMcsUserError("result name must be specified")

    if requireScenario:
        expList = expNames and expNames.split(',')
        if (not (expList and expList[0])):
            raise PygcamMcsUserError("scenario name must be specified")
    else:
        expList = None

    db = getDatabase()
    trials = db.getTrialCount(simId) if limit <= 0 else limit
    if not trials:
        raise PygcamMcsUserError('No trials were found for simId %d' % simId)

    # inputs are shared across experiments, so gather these before looping over experiments
    if requireInputs:
        inputDF = readParameterValues(simId, trials)
        inputRows, inputCols = inputDF.shape
        _logger.info("Each trial has %d parameters", inputCols)
    else:
        inputDF = None

    if inputsFile:
        exportInputs(inputsFile, inputDF)

    if plotInputs:
        plotInputDistributions(simId, inputDF)

    if exportAll:
        exportAllInputsOutputs(simId, expList[0], inputDF, exportAll)

    if resultFile:
        resultList = resultName.split(',')
        exportResults(simId, resultList, expList, resultFile)

    if exportEMA:
        resultList = resultName.split(',')
        saveForEMA(simId, expList, resultList, inputDF, exportEMA)

    if not (requireScenario and requireResult):
        return

    for expName in expList:
        resultDF = db.getOutValues(simId, expName, resultName, limit=limit)
        if resultDF is None:
            raise PygcamMcsSystemError('analyzeSimulation: No results for simId=%d, expName=%s, resultName=%s' % (simId, expName, resultName))

        if maximum is not None:
            before = resultDF.shape[0]
            resultDF = resultDF[resultDF[resultName] <= maximum]
            after  = resultDF.shape[0]
            _logger.debug('Applying maximum value (%f) eliminated %d rows.', maximum, before - after)

        if minimum is not None:
            before = resultDF.shape[0]
            resultDF = resultDF[resultDF[resultName] >= minimum]
            after = resultDF.shape[0]
            _logger.debug('Applying minimum value (%f) eliminated %d rows.', minimum, before - after)

        resultSeries = resultDF[resultName]
        numResults = resultSeries.count()

        if plotHist:
            plotOutputDistribution(simId, expName, resultSeries, resultName, xlabel, trials)

        if stats:
            printStats(resultSeries)

        if convergence:
            plotConvergence(simId, expName, resultName, resultSeries, show=False, save=True)

        if (importance or groups or inputsFile) and (numResults != trials or numResults != inputRows):
            _logger.info("SimID %d has %d trials, %d input rows, and %d results", simId, trials, inputRows, numResults)

        if importance or groups:
            inputsWithResults = inputDF.ix[resultDF.index]

            # Drop any inputs with names ending in '-linked' since these are an artifact
            # Column names can look like 'foobar[0][34]', so we strip off indexing part.
            def _isLinked(colname):
                pos = colname.find('[')
                colname = colname if pos < 0 else colname[0:pos]
                return colname.endswith('-linked')

            linked = list(filter(_isLinked, inputsWithResults.columns))
            if linked:
                inputsWithResults.drop(linked, axis=1, inplace=True)

            spearman = spearmanCorrelation(inputsWithResults, resultSeries)

            data = pd.DataFrame(spearman)
            data['normalized'] = normalizeSeries(spearman ** 2)
            data['sign'] = 1
            negatives = (data.spearman < 0)
            data.ix[negatives, 'sign'] = -1
            data['value'] = data.normalized * data.sign     # normalized squares with signs restored

            if importance:
                plotSensitivityResults(resultName, data, maxVars=maxVars,
                                       filename=makePlotPath('%s-s%02d-%s-ind' % (expName, simId, resultName), simId),
                                       extra='SimId=%d, Exp=%s, Trials=%d/%d' % (simId, expName, numResults, trials))

            if groups:
                plotGroupSensitivityResults(resultName, data, maxVars=maxVars,
                                            filename=makePlotPath('%s-s%02d-%s-grp' % (expName, simId, resultName), simId),
                                            extra='SimId=%d, Exp=%s, Trials=%d/%d' % (simId, expName, numResults, trials))
