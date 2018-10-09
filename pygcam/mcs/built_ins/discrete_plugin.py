# Copyright (c) 2016 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from pygcam.log import getLogger
from .McsSubcommandABC import McsSubcommandABC

from ..error import DistributionSpecError

DISCRETE_SUFFIX = 'ddist'
DEFAULT_DISCRETE_PRECISION = 100
DEFAULT_DISCRETE_TOLERANCE = 0.01

SPEC_SEPARATOR  = r'\s+'

_logger = getLogger(__name__)

def getDiscreteDistFromData(data, bins=30):
    """
    Returns a set of (value, frequency) pairs for some title from the given dictionary of {value: count}.
    The values are stored in returnValue[data], and each frequency can be found from minData, minData+binsize,
    minData+2*binsize, etc...
    Assumes there are relatively few discrete values the data can take, and returns
    pairs ready for processing by DiscreteDist.py

    data: dictionary mapping values to counts of those values.

    bins: number of bins to put data into. Default is 30.
    """
    import numpy as np
    from math import ceil, floor
    from six import iteritems
    from ..error import DistributionSpecError

    if bins <= 0 or int(bins) != bins:
        raise DistributionSpecError('Number of bins must be a positive integer.')

    dataArray = np.zeros(bins)
    minData = min(data)
    dataRange = max(data) - minData
    binSize = int(ceil(dataRange / bins))

    # if dataRange is zero, only one value was given. Turns out this edge case isn't well handled by the rest of the code
    if not dataRange:
        return {'data': np.array([1.0]), 'min': minData, 'binSize': 0}

    # In the rare edge case where the range of the data is divisible by the bin number
    # increment binsize to avoid fencemaking error
    if binSize * bins == dataRange:
        binSize += 1
    size = 0
    for key, cnt in iteritems(data):
        dataArray[int(floor((key - minData) / binSize))] += cnt  # divide by size so results sum to 1
        size += cnt

    if size:
        dataArray /= float(size)

    # half bin offset of min because we're sampling from the middle of each bucket, not from its bottom
    return {'data': dataArray, 'min': minData + float(binSize) / 2, 'binSize': binSize}

def getDataDict(fileName, dataTitle, varTitles=None, countTitle=None):
    """
    Takes in a fileName (csv format), rowTitle, and columnTitle and generates
    dataDict with a list of values of data for every value of [varTitle[0], varTitle[1], etc..].
    In other words, each member of varTitle represents a column to key the output dataDict by.
    Returns a dict of dicts. The outer dict is keyed by a tuple constructed from the indices of
    the columns specified by varTitles. The inner dict is keyed by the value for the data in the
    column identified by dataTitle.

    fileName: csv file.

    dataTitle: title of column in file that represents data

    varTitles: List of titles of columns in csv file. Each combination of different values of
    varTitles will be separated into their own dict, and put into the returned dict keyed by a
    tuple made up of values of varTitles.

    countTitle: optional argument. Must be the title of a column of the file. Each entry in
    dataTitle is counted as if it is repeated countTitle times.

    Example: csv file that looks like:

    A,B,C,data,count
    1,2,3,8,10
    2,3,4,7,1
    2,3,4,6,2
    1,2,8,1,3
    2,3,9,7,8

    let varTitles = ['A','B'], dataTitle='data',countTitle='count'
    The returned dataDict will have keys (1,2) and (2,3)
    dataDict[(1,2)] = {8:10, 1:3}
    dataDict[(2,3)] = {7:9, 6:2}
    """
    import csv
    from collections import defaultdict
    from warnings import warn

    if not varTitles:
        warn("dataDict was not given a list of variable names.")
        varTitles = []

    with open(fileName, 'rb') as f:
        reader = csv.reader(f)
        firstLine = reader.next()

        # set appropriate indices
        datIndex = firstLine.index(dataTitle)
        varIndices = [firstLine.index(title) for title in varTitles]

        cntIndex = None
        if countTitle:
            cntIndex = firstLine.index(countTitle)

        # create dataDict
        dataDict = defaultdict(lambda: defaultdict(int))

        for entry in reader:
            dictInd = tuple([entry[i] for i in varIndices])
            cnt = int(entry[cntIndex]) if cntIndex else 1
            # Skip counts of zero, which can occur with the non-forest records in World.csv
            if cnt:
                dataDict[dictInd][float(entry[datIndex])] += cnt

    return dataDict

def driver(args, tool):
    """
    Converts an input csv file into an output file of discrete distribution declarations.

    inputFile: csv file. Must have columns headed with dataTitle, as well as each entry of varTitles and countTitle.

    outputFile: place to store discrete distribution data. Should have suffix matching Distro.DISCRETE_SUFFIX (initially 'out')

    dataTile: Title of column of actual data to be put into discrete distributions.

    varName: Optional name of each entry. If not supplied, varName will be the base name of the file being read from.

    varTitles: Optional array of titles of columns in inputFile. A separate distribution will be made for every value of each column in varTitle.
    For example, if varTitles is ['a','b','c'], and the 'a','b',and 'c' columns of inputFile have domains [1,2],[3,4],[5,6], respectively,
    the outputFile will have 8 rows, one for each of [1,3,5],[1,3,6],[1,4,5],[1,4,6],[2,3,5],[2,3,6],[2,4,5],[2,4,6].

    bins: Number of bins to divide distributions into. Default is 30.
    truncate: Number of decimal places for frequency entries of output file. Default is 3.
    countTitle: Optional column of inputFile. Each entry in dataTitle is treated as if it has been duplicated countTitle number of times.
    keyFunc: Optional function for how to key the entries of the output file. Must be a function of varTitles. Takes in a list
    of the same length as varTitles and outputs a list of the same length.
    Output is a .ddist file that specifies all of the discrete distributions found in the .csv file.
    """
    from os.path import basename

    from ..error import DistributionSpecError
    from ..util import checkSuffix

    inputFile  = args.inputFile
    outputFile = args.outputFile
    dataTitle  = args.dataTitle
    varName    = args.varName
    varTitles  = args.varTitles
    countTitle = args.countTitle
    bins       = args.bins
    truncate   = args.truncate

    if not checkSuffix(outputFile, DISCRETE_SUFFIX):
        raise DistributionSpecError('Output file is not a .%s file' % DISCRETE_SUFFIX)

    if varName is None:
        varName = basename(inputFile).split('.')[0]

    # Get the data from the input file
    dataDict = getDataDict(inputFile, dataTitle, varTitles=varTitles, countTitle=countTitle)

    # Aggregate the data and counts
    distDicts = {key: getDiscreteDistFromData(value, bins) for key, value in dataDict.items()}

    with open(outputFile, 'w') as outFile:
        for key, distDict in distDicts.items():
            outFile.write(varName)
            # Get rid of quotes and whitespace so as not to mess up the reading of .ddist files
            outKey = '[' + ','.join(key) + ']'
            if SPEC_SEPARATOR in outKey:
                raise DistributionSpecError('Key %s contains illegal character "%s".' % (outKey, SPEC_SEPARATOR))
            outFile.write(outKey)
            minValue = distDict['min']
            binSize = distDict['binSize']
            for binNum, frequency in enumerate(distDict['data']):
                f = round(frequency, truncate)
                # If f is too small (rounds to 0), may as well not even print it
                if f:
                    outFile.write('\t' + str(minValue + binNum * binSize) + ':' + str(f))
            outFile.write('\n')

class DiscreteCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Convert csv files to the .ddist format.'''}
        super(DiscreteCommand, self).__init__('discrete', subparsers, kwargs)
        self.group = None   # don't display this for now

    def addArgs(self, parser):
        from ..constants import DEFAULT_BINS, DEFAULT_TRUNCATE, COUNT_TITLE

        parser.add_argument('-i', '--inputFile', required=True,
                            help='Path to input .csv file being converted.')

        parser.add_argument('-o', '--outputFile', required=True,
                            help='Path to output .ddist file.')

        parser.add_argument('-d', '--dataTitle', required=True,
                            help='Actual data title in the .csv file.')

        parser.add_argument('-b', '--bins', type=int, default=DEFAULT_BINS,
                            help='Number of bins to separate discrete distro into')

        parser.add_argument('-t', '--truncate', type=int, default=DEFAULT_TRUNCATE,
                            help='Number of digits to truncate output to. Default is 3')

        parser.add_argument('-c', '--countTitle', type=str, default=COUNT_TITLE,
                            help='Title of column representing counts of data.')

        parser.add_argument('-n', '--varName', type=str, default=None,
                            help='Title of rows of output distribution')

        parser.add_argument('-v', '--varTitles', type=str, nargs='*',
                            help='Titles of columns keying different distributions in the input file')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)


# TODO: maybe simplify using scipy.stats.rv_discrete, but loses the tolerance option.
# http://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rv_discrete.html
# from scipy import stats
# xk = np.arange(7)
# pk = (0.1, 0.2, 0.3, 0.1, 0.1, 0.0, 0.2)
# custm = stats.rv_discrete(name='custm', values=(xk, pk))

# Deprecated?
class DiscreteDist(object):
    """
    An object to represent a discrete distribution of values.
    """
    def __init__(self, probList, precision=DEFAULT_DISCRETE_PRECISION, tolerance=DEFAULT_DISCRETE_TOLERANCE):
        """
        Takes in a list of (value, probability) tuples to initiate.
        Tolerance allows for distributions with a sum of probabilities close but
        not equal to 1 due to rounding errors. precision determines how many entries
        are in the fast ppf list; ppf values will be accurate within 1/precision
        """
        import numpy as np

        totalProb = sum([x[1] for x in probList])
        if not (1 - tolerance <= totalProb <= 1 + tolerance):
            raise DistributionSpecError('Sum of probabilities != 1 (sum=%f). Try setting the tolerance higher.' % totalProb)

        self.probList = sorted(probList)
        self.values = [x[0] for x in self.probList]
        self.probs = [x[1] / totalProb for x in self.probList]

        # Initialize the lookup table for fast ppf
        self.precision = precision
        self.fastPPF = np.zeros(precision)

        index = 0
        cumProb = 0
        for i in range(precision):
            if i / float(precision) > self.probs[index] + cumProb:
                cumProb += self.probs[index]
                index += 1
            self.fastPPF[i] = self.values[index]

    def __eq__(self, comp):
        return self.values == comp.values and self.probs == comp.probs and self.precision == comp.precision

    def ppf(self, percentiles):
        """
        This ppf function behaves differently than those for continuous
        distributions. In this discrete case, we just want to split the
        range from 0 to 1 so that each discrete value has the assigned
        probability. This way when the LHS function passes in a vector of
        N percentiles, the values returned will occur in the correct proportions.
        The percentiles parameter must be 'array-like' to match (some) of the
        behavior of scipy.stats.rv_continuous.ppf
        """
        from functools import reduce

        if not reduce(lambda x, y: x and 0 < y < 1, percentiles):
            raise DistributionSpecError('Percentiles must all be > 0 and < 1')

        return [self.fastPPF[int(x * self.precision)] for x in percentiles]
        #return map(lambda x: self.fastPPF[int(x * self.precision)], percentiles)

    def rvs(self, n=1):
        """Returns one or more random values, according to the RV's distribution."""
        from scipy.stats import uniform

        return self.ppf(uniform.rvs(size=n))
