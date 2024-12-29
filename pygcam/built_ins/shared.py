#
# Defines a superclass used by both CO2e and CI2 plugins
#
import os
from pygcam.config import getParam, pathjoin
from pygcam.error import PygcamException
from pygcam.log import getLogger
from pygcam.query import readCsv

_logger = getLogger(__name__)

def log_fmt_df(df):
    return '\n' + df.to_string(formatters={'value': '{:,.2f}'.format}) + '\n'

class PluginCommon(object):
    def __init__(self, mapper, firstYear, lastYear, queryList, is_diff=True):
        self.mapper = mapper
        self.baseline = mapper.baseline
        self.policy = mapper.scenario
        self.diffsDir = mapper.sandbox_diffs_dir
        self.queryList = queryList

        self.is_diff = is_diff      # CO2e operates on queryResults, not diffs like CI plugin

        self.firstYear = firstYear
        self.lastYear = lastYear
        self.yearsOfInterest = range(firstYear, lastYear + 1)
        self.yearCols = [str(y) for y in self.yearsOfInterest]

        self.GHG = None
        self.diffDFs = None
        self.queryDFs = None
        self.lucCO2 = None
        self.normedDFs = None

    def run(self, *args, **kwargs):
        self.verifyResultFiles(self.policy)  # raises error if anything is missing

    def csv_dir(self):
        mapper = self.mapper
        pathname = mapper.sandbox_diffs_dir if self.is_diff else mapper.sandbox_query_results_dir
        return pathname

    def queryPathname(self, queryName):
        csv_dir = self.csv_dir()

        if self.is_diff:
            pathname = pathjoin(csv_dir, f'{queryName}-{self.policy}-{self.baseline}.csv')
        else:
            pathname = pathjoin(csv_dir, f'{queryName}-{self.policy}.csv')

        return pathname

    def ensureCSV(self, filename):
        'Add a .csv extension to a filename, if there is none. Return the filename.'
        mainPart, extension = os.path.splitext(filename)
        if not extension:
            filename = mainPart + '.csv'

        return filename

    def verifyResultFiles(self, scenario):
        csv_dir = self.csv_dir()

        def resultFileDoesntExist(queryName):
            basename = self.queryPathname(queryName)
            fullname = self.ensureCSV(basename)
            path = pathjoin(csv_dir, fullname)
            _logger.debug("Checking for '%s'", path)
            return None if os.path.lexists(path) else path

        # find missing files, if any
        names = list(filter(resultFileDoesntExist, self.queryList))
        if names:
            names_str = "\n  ".join(names)
            raise PygcamException(f"Query result files are missing in {csv_dir} for '{scenario}':\n  {names_str}")

    # Deprecated - use readQueryResult for both use cases?
    def readDiff(self, query):
        '''
        Read a single query and return a DF holding the results.
        '''
        path = self.queryPathname(query)
        df = readCsv(path)
        return df

    def readDiffs(self):
        '''
        Read the given list of query diff results for the given scenario into DFs.
        Return a dict keyed by query name, with the corresponding DF as the value.
        '''
        _logger.debug("Loading diff results")

        results = {q: self.readDiff(q) for q in self.queryList}
        return results

    def readQueryResult(self, queryName, **kwargs):
        '''
        Read a single query result and return a DF holding the results.
        '''
        path = self.queryPathname(queryName)
        df = readCsv(path, **kwargs)
        return df

    def readQueryResults(self, **kwargs):
        '''
        Read the given list of queries results for the given scenario into DFs.
        Return a dict keyed by query name, with the corresponding DF as the value.
        '''
        _logger.debug("Loading query results")

        results = {q: self.readQueryResult(q, **kwargs) for q in self.queryList}
        return results

    def filterValues(self, df, column, values, complement=False):
        '''
        Restore the columns as such, perform the query, isolate the
        rows of interest, and set the index back to the original value.
        Return a new df with only rows matching the filter criteria.
        '''
        if not hasattr(values, '__iter__'):
            values = [values]

        query = "%s %s in %s" % (column, 'not' if complement else '', values)
        df = df.query(query)
        return df

    def sumDiffs(self, df, col=None, values=None, complement=False):
        '''
        Sum the year-by-year differences and then sum across years. If col and
        values are provided, only rows with (or without, if complement is True)
        one of the given values in the given column will be included in the sum. The
        parameter startYear allows fuel changes to be counted starting at the shock
        year rather than counting the values interpolated from the baseline to the
        value in the first shock year.
        '''
        if col and values:
            df = self.filterValues(df, col, values, complement=complement)

        yearTotals = df[self.yearCols].sum() # sum columns
        total = yearTotals.sum()        # sum across years
        return total
