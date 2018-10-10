'''
  .. Copyright (c) 2016 Richard Plevin

  See the https://opensource.org/licenses/MIT for license details.
'''
import os
from .config import pathjoin
from .log import getLogger
from .error import CommandlineError, FileFormatError
from .utils import mkdirs, ensureCSV, QueryResultsDir
from .query import readCsv, dropExtraCols, csv2xlsx, sumYears, sumYearsByGroup, QueryFile

_logger = getLogger(__name__)


def computeDifference(df1, df2, resetIndex=True, dropna=True, asPercentChange=False):
    """
    Compute the difference between two DataFrames.

    :param df1: a pandas DataFrame instance
    :param obj2: a pandas DataFrame instance
    :param resetIndex: (bool) if True (the default), the index in the DataFrame
      holding the computed difference is reset so that data in non-year columns
      appear in individual columns. Otherwise, the index in the returned
      DataFrame is based on all non-year columns.
    :param dropna: (bool) if True, drop rows with NaN values after computing difference
    :param asPercentChange: (bool) if True, compute percent change rather than difference.
    :return: a pandas DataFrame with the difference in all the year columns, computed
      as (df2 - df1) if asPercentChange is False, otherwise as (df2 - df1)/df1.
    """
    df1 = dropExtraCols(df1, inplace=False)
    df2 = dropExtraCols(df2, inplace=False)

    if set(df1.columns) != set(df2.columns):
        raise FileFormatError("Can't compute difference because result sets have different columns. df1:%s, df2:%s" \
                              % (df1.columns, df2.columns))

    # Handle corner case in which query results for non-existent data have zero in Units column
    if 'Units' in df1.columns:
        units = list(df1.Units.unique())
        if len(units) == 2 and '0.0' in units:
            units.remove('0.0')
            realUnits = units[0]
            df1.Units = realUnits
            df2.Units = realUnits

    yearCols = [col for col in df1.columns if col.isdigit()]
    nonYearCols = list(set(df1.columns) - set(yearCols))

    df1.set_index(nonYearCols, inplace=True)
    df2.set_index(nonYearCols, inplace=True)

    # Compute difference for timeseries values
    diff = df2 - df1

    if asPercentChange:
        diff /= df1

    if dropna:
        diff.dropna(inplace=True)

    if resetIndex:
        diff.reset_index(inplace=True)      # convert multi-index back to regular column values

    return diff

def _label(referenceFile, otherFile, asPercentChange=False):
    label = "([{other}] minus [{ref}]) / [{ref}]" if asPercentChange else "[{other}] minus [{ref}]"

    return label.format(other=otherFile, ref=referenceFile)

def writeDiffsToCSV(outFile, referenceFile, otherFiles, skiprows=1, interpolate=False,
                    years=None, startYear=0, asPercentChange=False):
    """
    Compute the differences between the data in a reference .CSV file and one or more other
    .CSV files as (other - reference), optionally interpolating annual values between
    timesteps, storing the results in a single .CSV file.
    See also :py:func:`writeDiffsToXLSX` and :py:func:`writeDiffsToFile`

    :param outFile: (str) the name of the .CSV file to create
    :param referenceFile: (str) the name of a .CSV file containing reference results
    :param otherFiles: (list of str) the names of other .CSV file for which to
       compute differences.
    :param skiprows: (int) should be 1 for GCAM files, to skip header info before column names
    :param interpolate: (bool) if True, linearly interpolate annual values between timesteps
       in all data files and compute the differences for all resulting years.
    :param years: (iterable of 2 values coercible to int) the range of years to include in
       results.
    :param startYear: (int) the year at which to begin interpolation, if interpolate is True.
       Defaults to the first year in `years`.
    :param asPercentChange: (bool) if True, compute percent change rather than difference.
    :return: none
    """
    refDF = readCsv(referenceFile, skiprows=skiprows, interpolate=interpolate,
                    years=years, startYear=startYear)

    with open(outFile, 'w') as f:
        for otherFile in otherFiles:
            otherFile = ensureCSV(otherFile)   # add csv extension if needed
            otherDF   = readCsv(otherFile, skiprows=skiprows, interpolate=interpolate,
                                years=years, startYear=startYear)

            diff = computeDifference(refDF, otherDF, asPercentChange=asPercentChange)
            csvText = diff.to_csv(index=None)
            label = _label(referenceFile, otherFile, asPercentChange=asPercentChange)
            f.write("%s\n%s" % (label, csvText))    # csvText has "\n" already


def writeDiffsToXLSX(outFile, referenceFile, otherFiles, skiprows=1, interpolate=False,
                     years=None, startYear=0, asPercentChange=False):
    """
    Compute the differences between the data in a reference .CSV file and one or more other
    .CSV files as (other - reference), optionally interpolating annual values between
    timesteps, storing the results in a single .XLSX file with each difference matrix
    on a separate worksheet, and with an index worksheet with links to the other worksheets.
    See also :py:func:`writeDiffsToCSV` and :py:func:`writeDiffsToFile`.

    :param outFile: (str) the name of the .XLSX file to create
    :param referenceFile: (str) the name of a .CSV file containing reference results
    :param otherFiles: (list of str) the names of other .CSV file for which to
       compute differences.
    :param skiprows: (int) should be 1 for GCAM files, to skip header info before column names
    :param interpolate: (bool) if True, linearly interpolate annual values between timesteps
       in all data files and compute the differences for all resulting years.
    :param years: (iterable of 2 values coercible to int) the range of years to include in
       results.
    :param startYear: (int) the year at which to begin interpolation, if interpolate is True.
       Defaults to the first year in `years`.
    :param asPercentChange: (bool) if True, compute percent change rather than difference.
    :return: none
    """
    import pandas as pd

    with pd.ExcelWriter(outFile, engine='xlsxwriter') as writer:
        sheetNum = 1
        _logger.debug("Reading reference file:", referenceFile)
        refDF = readCsv(referenceFile, skiprows=skiprows, interpolate=interpolate,
                        years=years, startYear=startYear)

        for otherFile in otherFiles:
            otherFile = ensureCSV(otherFile)   # add csv extension if needed
            _logger.debug("Reading other file:", otherFile)
            otherDF = readCsv(otherFile, skiprows=skiprows, interpolate=interpolate,
                              years=years, startYear=startYear)

            sheetName = 'Diff%d' % sheetNum
            sheetNum += 1

            diff = computeDifference(refDF, otherDF, asPercentChange=asPercentChange)
            diff.to_excel(writer, index=None, sheet_name=sheetName, startrow=2, startcol=0)

            worksheet = writer.sheets[sheetName]
            label = _label(referenceFile, otherFile, asPercentChange=asPercentChange)
            worksheet.write_string(0, 0, label)

            startRow = diff.shape[0] + 4
            worksheet.write_string(startRow, 0, otherFile)
            startRow += 2
            otherDF.reset_index(inplace=True)
            otherDF.to_excel(writer, index=None, sheet_name=sheetName, startrow=startRow, startcol=0)

        dropExtraCols(refDF, inplace=True)
        _logger.debug("writing DF to excel file", outFile)
        refDF.to_excel(writer, index=None, sheet_name='Reference', startrow=0, startcol=0)


def writeDiffsToFile(outFile, referenceFile, otherFiles, ext='csv', skiprows=1, interpolate=False,
                     years=None, startYear=0, asPercentChange=False):
    """
    Compute the differences between the data in a reference .CSV file and one or more other
    .CSV files as (other - reference), optionally interpolating annual values between
    timesteps, storing the results in a single .CSV or .XLSX file. See :py:func:`writeDiffsToCSV`
    and :py:func:`writeDiffsToXLSX` for more details.

    :param outFile: (str) the name of the file to create
    :param referenceFile: (str) the name of a .CSV file containing reference results
    :param otherFiles: (list of str) the names of other .CSV file for which to
       compute differences.
    :param ext: (str) if '.csv', results are written to a single .CSV file, otherwise, they
       are written to an .XLSX file.
    :param skiprows: (int) should be 1 for GCAM files, to skip header info before column names
    :param interpolate: (bool) if True, linearly interpolate annual values between timesteps
       in all data files and compute the differences for all resulting years.
    :param years: (iterable of 2 values coercible to int) the range of years to include in
       results.
    :param startYear: (int) the year at which to begin interpolation, if interpolate is True.
       Defaults to the first year in `years`.
    :return: none
    """
    writer = writeDiffsToCSV if ext == '.csv' else writeDiffsToXLSX
    writer(outFile, referenceFile, otherFiles, skiprows=skiprows, interpolate=interpolate,
           years=years, startYear=startYear, asPercentChange=asPercentChange)


def diffCsvPathname(query, baseline, policy, diffsDir=None, workingDir='.', createDir=False,
                    asPercentChange=False):
    """
    Compute the path to the CSV file containing differences between `policy` and
    `baseline` scenarios for `query`.

    :param query: (str) the base file name of the query result
    :param baseline: (str) the baseline scenario
    :param policy: (str) the policy scenario
    :param workingDir: (str) the directory immediately above the baseline
        and policy sandboxes.
    :param createDir: (bool) whether to create the diffs directory, if needed.
    :return: (str) the pathname of the CSV file
    """
    diffsDir = diffsDir or pathjoin(workingDir, policy, 'diffs')
    if createDir:
        mkdirs(diffsDir)

    chg = '-pctChg' if asPercentChange else ''
    pathname = pathjoin(diffsDir, '%s-%s-%s%s.csv' % (query, policy, baseline, chg))
    return pathname

def queryCsvPathname(query, scenario, workingDir='.'):
    """
    Compute the path to the CSV file containing results for the given
    `query` and `scenario`.

    :param query: (str) the base file name of the query result
    :param scenario: (str) the scenario name
    :param workingDir: (str) the directory immediately above the baseline
        and policy sandboxes.
    :return: (str) the pathname of the CSV file
    """
    pathname = pathjoin(workingDir, scenario, QueryResultsDir, '%s-%s.csv' % (query, scenario))
    return pathname

def diffMain(args):
    workingDir = args.workingDir
    mkdirs(workingDir)
    os.chdir(workingDir)

    _logger.debug('Working dir: %s', workingDir)

    convertOnly = args.convertOnly
    skiprows    = args.skiprows
    interpolate = args.interpolate
    groupSum    = args.groupSum
    sum         = args.sum
    queryFile   = args.queryFile
    yearStrs    = args.years.split('-')
    asPercentChange = args.asPercentChange

    if len(yearStrs) == 2:
        years = yearStrs
        startYear = args.startYear
    else:
        years = startYear = None

    # If a query file is given, we loop over the query names, computing required arguments to performDiff().
    if queryFile:
        if len(args.csvFiles) != 2:
            raise CommandlineError("When --queryFile is specified, 2 positional arguments--the baseline and policy names--are required.")

        baseline, policy = args.csvFiles

        # def makePath(query, scenario):
        #     return pathjoin(scenario, QueryResultsDir, '%s-%s.csv' % (query, scenario))

        mainPart, extension = os.path.splitext(queryFile)

        if extension.lower() == '.xml':
            queryFileObj = QueryFile.parse(queryFile)
            queries = queryFileObj.queryFilenames()
        else:
            with open(queryFile, 'rU') as f:    # 'U' converts line separators to '\n' on Windows
                lines = f.read()
                queries = [line for line in lines.split('\n') if line]   # eliminates blank lines

        for query in queries:
            baselineFile = queryCsvPathname(query, baseline, workingDir=workingDir)
            policyFile   = queryCsvPathname(query, policy,   workingDir=workingDir)

            outFile = diffCsvPathname(query, baseline, policy, workingDir=workingDir,
                                      createDir=True, asPercentChange=asPercentChange)
            _logger.info("Writing %s", outFile)

            writeDiffsToFile(outFile, baselineFile, [policyFile], ext='.csv', skiprows=skiprows,
                             interpolate=interpolate, years=years, startYear=startYear,
                             asPercentChange=asPercentChange)
    else:
        csvFiles = [ensureCSV(f) for f in args.csvFiles]
        referenceFile = csvFiles[0]
        otherFiles    = csvFiles[1:] if len(csvFiles) > 1 else []

        outFile = args.outFile
        root, ext = os.path.splitext(outFile)
        if not ext:
            outFile = ensureCSV(outFile)
            ext = '.csv'

        extensions = ('.csv', '.xlsx')
        if ext not in extensions:
            raise CommandlineError("Output file extension must be one of %s", extensions)

        if convertOnly or groupSum or sum:
            if convertOnly:
                csv2xlsx(csvFiles, outFile, skiprows=skiprows, interpolate=interpolate)
            elif groupSum:
                sumYearsByGroup(groupSum, csvFiles, skiprows=skiprows, interpolate=interpolate)
            elif sum:
                sumYears(csvFiles, skiprows=skiprows, interpolate=interpolate)
            return

        writeDiffsToFile(outFile, referenceFile, otherFiles, ext=ext, skiprows=skiprows,
                         interpolate=interpolate, years=years, startYear=startYear,
                         asPercentChange=asPercentChange)

