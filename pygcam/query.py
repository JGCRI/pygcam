"""
.. Support for querying GCAM's XML database and processing results.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from .common import getTempFile
from .config import readConfigFiles, getParam
from .error import PygcamException


# TBD: have a library version more like the original, and build the class on that,
# TBD: so users can have it either way? Or, try to rewrite utils using this (and similar)
# TBD: classes to vet the design.

def dropExtraCols(df, inplace=True):
    """
    Drop some columns that GCAM queries sometimes return, but which we generally don't need.
    The columns dropped are ['scenario', 'Notes', 'Date'].

    :param df: a DataFrame hold the results of a GCAM query.
    :param inplace: if True, modify `df` in-place; otherwise return a modified copy.
    :return: the original `df` (if inplace=True) or the modified copy.
    """
    columns = df.columns
    unnamed = 'Unnamed:'    # extra (empty) columns can sneak in; eliminate them
    dropCols = filter(lambda s: s[0:len(unnamed)] == unnamed, columns)

    # TBD: get these column names from config file
    unneeded  = set(['scenario', 'Notes', 'Date'])
    columnSet = set(columns)
    dropCols += columnSet & unneeded    # drop any columns in both sets

    resultDF = df.drop(dropCols, axis=1, inplace=inplace)
    return resultDF

def computeDifference(df1, df2):
    """
    Compute the difference between two DataFrames.

    :param df1: a DataFrame instance
    :param obj2: a DataFrame instance
    :return: a DataFrame with the difference in all the year columns, computed
      as (df2 - df1).
    """
    df1 = df1.dropExtraCols(inplace=False)
    df2 = df2.dropExtraCols(inplace=False)

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

def batchQuery(database, query, scenario, outfile=None, asGcamResult=False):
    """
    Run a query against GCAM's XML database, optionally save
    the results into `outfile`, and return the data either as a
    `GcamResult` instance (if asGcamResult is True) otherwise as
    a `DataFrame`.

    :param database: the pathname to the XML database to query
    :param query: the name of a query to execute
    :param scenario: the name of the scenario to perform the query on
    :param outfile: if None, query results are written to a temp file and read
      into a DataFrame; if not None, the results are saved in `outfile`.
    :param asGcamResult: (bool) True if results should be returned as a
      `GcamResult` instance; otherwise results are returned in a DataFrame.
    :return: an DataFrame of `GcamResult` instance holding the query results
    """
    tmpfile = False
    if not outfile:
        tmpfile = True
        outfile = getTempFile('.csv')
    try:
        # run the query on database for scenario; results written to outfile

        obj = GcamResult(outfile)

    finally:
        if tmpfile:
            # remove the file
            pass

    return obj if asGcamResult else obj.df

class GcamResult(object):
    """
    Holds the result of a batch query against GCAM's XML database. Many of the methods
    in `GcamResult` are available as function on DataFrames. This class provides an
    object wrapper around a core set of these functions.

    :param filename: the path to a .csv file in the usual GCAM format.
    :interpolate: if True annual values are interpolated.
    :param years: a sequence of two years (str or int); only in this range (inclusive)
      are kept. Data for other years is dropped.
    :param interpolate: if True, annual values are linearly interpolated between
      timesteps.
    :param startYear: If non-zero, begin interpolation at this year, which
      must be the name of a column in the DataFrame.
    :param exitOnError: if False, we trap the error and exit, otherwise we pass
          it on.
    """
    def __init__(self, filename, years=None, interpolate=False, startYear=0):
        self.filename = filename
        self.df = self.readCsv(filename, years=years, interpolate=interpolate,
                               startYear=startYear)
        if years:
            self.limitYears(self, years)

        if interpolate:
            # Modify it in place; if caller prefers a copy, they can pass
            # interpolate=False and call interpolateYears afterwards.
            self.df = self.interpolateYears(startYear=startYear, inplace=True)

    def limitYears(self, years):
        """
        Modify self.df to drop all years outside the range given by `years`.

        :param years: a sequence of two years (str or int); only in this range (inclusive)
          are kept. Data for other years is dropped.
        :return: none; self.df is modified in place.
        """
        df = self.df
        first, last = map(int, years)
        yearCols  = map(int, filter(str.isdigit, df.columns))
        dropYears = map(str, filter(lambda y: y < first or y > last, yearCols))
        df.drop(dropYears, axis=1, inplace=True)

    # TBD: Move the guts of this out to a function
    def interpolateYears(self, startYear=0, inplace=False):
        """
        Interpolate linearly between each pair of years in the GCAM output. The
        timestep is calculated from the numerical (string) column headings given
        in the DataFrame `df`, which are assumed to represent years in the time-series.
        The years to interpolate between are read from `df`, so there's no dependency
        on any particular time-step, or even on the time-step being constant.

        :param df: a DataFrame holding data of the format returned by batch queries
          on the GCAM XML database
        :param startYear: If non-zero, begin interpolation at this year.
        :param inplace: If True, modify `self.df` in place; otherwise modify a copy.
        :return: if `inplace` is True, `self.df` is returned; otherwise a copy
          of `self.df` with interpolated values is returned.
        """
        df = self.df
        yearCols = filter(str.isdigit, df.columns)
        years = map(int, yearCols)

        for i in range(0, len(years)-1):
            start = years[i]
            end   = years[i+1]
            timestep = end - start

            if timestep == 1:       # don't interpolate annual results if already annual
                continue

            startCol = df[str(start)]
            endCol   = df[str(end)]

            # compute vector of annual deltas for each row
            delta = (endCol - startCol)/timestep

            # interpolate the whole column -- but don't interpolate before the start year
            for j in range(1, timestep):
                nextYear = start + j
                df[str(nextYear)] = df[str(nextYear-1)] + (0 if nextYear < startYear else delta)

        yearCols = filter(str.isdigit, df.columns)  # get annualized year columns
        years = map(int, yearCols)       # sort as integers
        years.sort()
        yearCols = map(str, years)       # convert back to strings, now sorted

        nonYearCols = list(set(df.columns) - set(yearCols))
        result = df.reindex_axis(nonYearCols + yearCols, axis=1, copy=(not inplace))

        self.df = result    # a no-op if we modified df in place
        return result

    def readCsv(self, filename, skiprows=1):
        """
        Read a .csv file of the form generated by batch queries on the GCAM
        XML database. Basically this is a generic .csv file with an extra
        header row.

        :param filename: the .csv file to read
        :param skiprows: the number of rows to skip before looking for column
          headings and data. The default is 1, which appropriate for GCAM .csv files.
        :return: a DataFrame containing the data from the .csv file, which is also
          stored in `self.df`.
        """
        self.df = readCsv(filename, skiprows=skiprows)
        return self.df

    @classmethod
    def computeDifference(cls, obj1, obj2):
        """
        Compute the difference between the DataFrames in two GcamResult instances.

        :param obj1: a `GcamResult` instance
        :param obj2: a `GcamResult` instance
        :return: a DataFrame with the difference in all the year columns, computed
          as (obj2.df - obj1.df).
        """
        diff = computeDifference(obj1.df, obj2.df)
        return diff

    def dropExtraCols(self, inplace=True):
        """
        Drop some columns that GCAM queries sometimes return, but which we
        generally don't need. The columns dropped are ['scenario', 'Notes', 'Date'].

        :param inplace: if True, modify `df` in-place; otherwise return a modified copy.
        :return: the original `df` (if inplace=True) or the modified copy.
        """
        df = dropExtraCols(self.df, inplace=inplace)
        return df


if __name__ == '__main__':
    pass
