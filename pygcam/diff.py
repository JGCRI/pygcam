import os
from .log import getLogger
from .error import PygcamException
from .common import mkdirs
from .subcommand import SubcommandABC
from .query import readCsv, ensureCSV, dropExtraCols, csv2xlsx, sumYears, sumYearsByGroup

_logger = getLogger(__name__)

VERSION = "0.2"


def computeDifference(df1, df2):
    """
    Compute the difference between two DataFrames.

    :param df1: a pandas DataFrame instance
    :param obj2: a pandas DataFrame instance
    :return: a pandas DataFrame with the difference in all the year columns, computed
      as (df2 - df1).
    """
    df1 = dropExtraCols(df1, inplace=False)
    df2 = dropExtraCols(df2, inplace=False)

    if set(df1.columns) != set(df2.columns):
        raise PygcamException("Can't compute difference because result sets have different columns. df1:%s, df2:%s" \
                              % (df1.columns, df2.columns))

    yearCols = filter(str.isdigit, df1.columns)
    nonYearCols = list(set(df1.columns) - set(yearCols))

    df1.set_index(nonYearCols, inplace=True)
    df2.set_index(nonYearCols, inplace=True)

    # Compute difference for timeseries values
    diff = df2 - df1
    return diff


def writeDiffsToCSV(outFile, referenceFile, otherFiles, skiprows=1, interpolate=False, percentage=False):
    refDF = readCsv(referenceFile, skiprows=skiprows, interpolate=interpolate)

    with open(outFile, 'w') as f:
        for otherFile in otherFiles:
            otherFile = ensureCSV(otherFile)   # add csv extension if needed
            otherDF   = readCsv(otherFile, skiprows=skiprows, interpolate=interpolate)

            diff = computeDifference(refDF, otherDF)

            csvText = diff.to_csv(None)
            label = "[%s] minus [%s]" % (otherFile, referenceFile)
            if percentage:
                label = "(%s)/%s" % (label, referenceFile)
            f.write("%s\n%s" % (label, csvText))    # csvText has "\n" already


def writeDiffsToXLSX(outFile, referenceFile, otherFiles, skiprows=1,
                     interpolate=False, percentage=False):
    import pandas as pd

    with pd.ExcelWriter(outFile, engine='xlsxwriter') as writer:
        sheetNum = 1
        _logger.debug("Reading reference file:", referenceFile)
        refDF = readCsv(referenceFile, skiprows=skiprows, interpolate=interpolate)

        for otherFile in otherFiles:
            otherFile = ensureCSV(otherFile)   # add csv extension if needed
            _logger.debug("Reading other file:", otherFile)
            otherDF   = readCsv(otherFile, skiprows=skiprows, interpolate=interpolate)

            sheetName = 'Diff%d' % sheetNum
            sheetNum += 1

            diff = computeDifference(refDF, otherDF, percentage=percentage)

            diff.reset_index(inplace=True)      # convert multi-index into regular column values
            diff.to_excel(writer, index=None, sheet_name=sheetName, startrow=2, startcol=0)

            #workbook  = writer.book
            #worksheet = workbook.add_worksheet(sheetName)
            worksheet = writer.sheets[sheetName]
            label     = "[%s] minus [%s]" % (otherFile, referenceFile)
            if percentage:
                label = "(%s)/%s" % (label, referenceFile)
            worksheet.write_string(0, 0, label)

            startRow = diff.shape[0] + 4
            worksheet.write_string(startRow, 0, otherFile)
            startRow += 2
            otherDF.reset_index(inplace=True)
            otherDF.to_excel(writer, index=None, sheet_name=sheetName, startrow=startRow, startcol=0)

        dropExtraCols(refDF, inplace=True)
        _logger.debug("writing DF to excel file", outFile)
        refDF.to_excel(writer, index=None, sheet_name='Reference', startrow=0, startcol=0)


def writeDiffsToFile(outFile, referenceFile, otherFiles, ext='csv',
                     skiprows=1, interpolate=False, percentage=False):
    if ext == '.csv':
        writeDiffsToCSV(outFile, referenceFile, otherFiles, skiprows=skiprows,
                        interpolate=interpolate, percentage=percentage)
    else:
        writeDiffsToXLSX(outFile, referenceFile, otherFiles, skiprows=skiprows,
                         interpolate=interpolate, percentage=percentage)

def main(args):
    mkdirs(args.workingDir)
    os.chdir(args.workingDir)

    _logger.debug('Working dir: %s', args.workingDir)

    percentage  = args.percentage
    convertOnly = args.convertOnly
    skiprows    = args.skiprows
    interpolate = args.interpolate
    groupSum    = args.groupSum
    sum         = args.sum

    yearStrs = args.years.split('-')
    if len(yearStrs) == 2:
        global Years, StartYear
        Years = yearStrs
        StartYear = args.startYear

    # If a queryFile is given, we loop over the query names, computing required arguments to performDiff().
    if args.queryFile:
        if len(args.csvFiles) != 2:
            raise Exception, "When --queryFile is specified, 2 positional arguments--the baseline and policy names--are required."

        baseline, policy = args.csvFiles

        def makePath(query, scenario):
            return os.path.join(scenario, "batch-" + scenario, '%s-%s.csv' % (query, scenario))

        with open(args.queryFile, 'rU') as f:    # 'U' converts line separators to '\n' on Windows
            lines = f.read()
            queries = filter(None, lines.split('\n'))   # eliminates blank lines

        for query in queries:
            baselineFile = makePath(query, baseline)
            policyFile   = makePath(query, policy)
            diffsDir = os.path.join(policy, 'diffs')
            mkdirs(diffsDir)

            outFile = os.path.join(diffsDir, '%s-%s-%s.csv' % (query, policy, baseline))

            _logger.debug("Writing %s", outFile)

            writeDiffsToFile(outFile, baselineFile, [policyFile], ext='.csv', skiprows=skiprows,
                             interpolate=interpolate, percentage=percentage)
    else:
        csvFiles = map(ensureCSV, args.csvFiles)
        referenceFile = csvFiles[0]
        otherFiles    = csvFiles[1:] if len(csvFiles) > 1 else []

        outFile = args.outFile
        root, ext = os.path.splitext(outFile)
        if not ext:
            outFile = ensureCSV(outFile)
            ext = '.csv'

        extensions = ('.csv', '.xlsx')
        if ext not in extensions:
            raise PygcamException("Output file extension must be one of %s", extensions)

        if convertOnly or groupSum or sum:
            if convertOnly:
                csv2xlsx(csvFiles, outFile, skiprows=skiprows, interpolate=interpolate)
            elif groupSum:
                sumYearsByGroup(groupSum, csvFiles, skiprows=skiprows, interpolate=interpolate)
            elif sum:
                sumYears(csvFiles, skiprows=skiprows, interpolate=interpolate)
            return

        writeDiffsToFile(outFile, referenceFile, otherFiles, ext=ext, skiprows=skiprows,
                         interpolate=interpolate, percentage=percentage)



class DiffCommand(SubcommandABC):
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
        super(DiffCommand, self).__init__('diff', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('csvFiles', nargs='+',
                    help='''The files to process. For difference operations, the first file is treated
                    as the reference file whose time-series data is subtracted from that of each other
                    file. If missing, ".csv" suffixes are added to all arguments (the ".csv" is optional).''')

        parser.add_argument('-D', '--workingDir', default='.',
                            help='''The directory to change to before performing any operations''')

        parser.add_argument('-g', '--groupSum', default="",
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

        parser.add_argument('-y', '--years', default="",
                            help='''Takes a parameter of the form XXXX-YYYY, indicating start and end years of interest.
                            Other years are dropped (except for annual outputs.)''')

        parser.add_argument('-Y', '--startYear', type=int, default=0,
                            help='''The year at which to begin interpolation''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        main(args)
