'''
  .. Copyright (c) 2016 Richard Plevin

  See the https://opensource.org/licenses/MIT for license details.
'''
import os
from .config import pathjoin, mkdirs, getParamAsPath
from .constants import (QRESULTS_DIRNAME, DIFFS_DIRNAME,
                        LAND_LEAF, LAND_ALLOC, LAND_USE, BASIN,
                        IRR_LEVEL, IRR_TYPE, SOIL_TYPE)
from .error import CommandlineError, FileFormatError
from .file_utils import ensureCSV
from .log import getLogger
from .query import readCsv, dropExtraCols, csv2xlsx, sumYears, sumYearsByGroup, QueryFile

_logger = getLogger(__name__)


def computeDifference(df1, df2, resetIndex=True, dropna=True,
                      asPercentChange=False, splitLand=False):
    """
    Compute the difference between two DataFrames.

    :param df1: a pandas DataFrame instance
    :param df2: a pandas DataFrame instance
    :param resetIndex: (bool) if True (the default), the index in the DataFrame
      holding the computed difference is reset so that data in non-year columns
      appear in individual columns. Otherwise, the index in the returned
      DataFrame is based on all non-year columns.
    :param dropna: (bool) if True, drop rows with NaN values after computing difference
    :param asPercentChange: (bool) if True, compute percent change rather than difference.
    :param splitLand: (bool) whether to split 'Landleaf' column (if present) to create two
      new columns, 'land_use' and 'basin'. Ignored if `resetIndex` is False.

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

        # Only split 'Landleaf' / 'land_allocation' if we're resetting the index
        if splitLand and LAND_LEAF in nonYearCols or LAND_ALLOC in nonYearCols:
            # avoid overwriting existing columns of the target names
            dupes = {LAND_USE, BASIN}.intersection(set(diff.columns))
            if dupes:
                _logger.warning(f"Ignoring request to split {LAND_LEAF} column. Target column(s) {dupes} already exist.")
                return diff

            land_col = LAND_LEAF if LAND_LEAF in nonYearCols else LAND_ALLOC
            splits = diff[land_col].str.split('_', expand=True)
            cols = splits.shape[1]
            if cols < 2:
                _logger.warning(f"Ignoring request to split {land_col} column. Expected split to produce at least 2 columns; got {cols}")
                return diff

            loc = len(nonYearCols)
            if cols > 4:
                diff.insert(loc, SOIL_TYPE, splits[4])
                diff.loc[diff[SOIL_TYPE].isnull(), SOIL_TYPE] = 'Mineral'
            if cols > 3:
                diff.insert(loc, IRR_LEVEL, splits[3])
            if cols > 2:
                diff.insert(loc, IRR_TYPE, splits[2])

            diff.insert(loc, BASIN, splits[1])
            diff.insert(loc, LAND_USE, splits[0])

    return diff

def _label(referenceFile, otherFile, asPercentChange=False):
    label = "([{other}] minus [{ref}]) / [{ref}]" if asPercentChange else "[{other}] minus [{ref}]"

    return label.format(other=otherFile, ref=referenceFile)

def writeDiffsToCSV(outFile, referenceFile, otherFiles, skiprows=1, interpolate=False,
                    years=None, startYear=0, asPercentChange=False, splitLand=False):
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

            diff = computeDifference(refDF, otherDF, asPercentChange=asPercentChange,
                                     splitLand=splitLand)
            csvText = diff.to_csv(index=None)
            label = _label(referenceFile, otherFile, asPercentChange=asPercentChange)
            f.write("%s\n%s" % (label, csvText))    # csvText has "\n" already


def writeDiffsToXLSX(outFile, referenceFile, otherFiles, skiprows=1, interpolate=False,
                     years=None, startYear=0, asPercentChange=False, splitLand=False):
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

            diff = computeDifference(refDF, otherDF, asPercentChange=asPercentChange,
                                     splitLand=splitLand)
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
                     years=None, startYear=0, asPercentChange=False, splitLand=False):
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
    :param asPercentChange: (bool) whether to write diffs as percent change from baseline
    :param splitLand: (bool) whether to split 'Landleaf' column (if present) to create two
        new columns, 'land_use' and 'basin'.
    :return: none
    """
    writer = writeDiffsToCSV if ext == '.csv' else writeDiffsToXLSX
    writer(outFile, referenceFile, otherFiles, skiprows=skiprows, interpolate=interpolate,
           years=years, startYear=startYear, asPercentChange=asPercentChange, splitLand=splitLand)


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
    diffsDir = diffsDir or pathjoin(workingDir, policy, DIFFS_DIRNAME)
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
    pathname = pathjoin(workingDir, scenario, QRESULTS_DIRNAME, f'{query}-{scenario}.csv')
    return pathname

def diffMain(args, tool):
    from .mcs.sim_file_mapper import get_mapper

    convertOnly = args.convertOnly
    skiprows    = args.skiprows
    interpolate = args.interpolate
    splitLand   = args.splitLand
    groupSum    = args.groupSum
    sum         = args.sum
    queryFile   = args.queryFile
    yearStrs    = args.years.split('-')
    asPercentChange = args.asPercentChange
    workingDir  = args.workingDir

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

        if not workingDir:
            mapper = tool.mapper or get_mapper(policy, scenario_group=args.group)
            workingDir = os.path.dirname(mapper.sandbox_scenario_dir)

        os.chdir(workingDir)

        _logger.debug('Working dir: %s', workingDir)


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
                             splitLand=splitLand, asPercentChange=asPercentChange)
    else:
        if not args.workingDir:
            raise CommandlineError("--workingDir/-D is required when --queryFile/-q is not specified")

        os.chdir(args.workingDir)

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
                         splitLand=splitLand, asPercentChange=asPercentChange)

