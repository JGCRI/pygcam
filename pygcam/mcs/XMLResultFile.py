# Created on 5/11/15
#
# Copyright (c) 2015-2017. The Regents of the University of California (Regents).
# See the file COPYRIGHT.txt for details.
import os
from collections import OrderedDict
from datetime import datetime

import pandas as pd

from ..config import getParam
from ..log import getLogger
from ..XMLFile import XMLFile
from .error import PygcamMcsUserError, PygcamMcsSystemError, FileMissingError
from .Database import getDatabase
from .XML import XMLWrapper, findAndSave

_logger = getLogger(__name__)

RESULT_TYPE_DIFF = 'diff'
RESULT_TYPE_SCENARIO = 'scenario'
DEFAULT_RESULT_TYPE = RESULT_TYPE_SCENARIO

QUERY_OUTPUT_DIR = 'queryResults'

RESULT_ELT_NAME = 'Result'
FILE_ELT_NAME = 'File'
CONSTRAINT_ELT_NAME = 'Constraint'
COLUMN_ELT_NAME = 'Column'

class XMLConstraint(XMLWrapper):
    equal = ['==', '=', 'equal', 'eq']
    notEqual = ['!=', '<>', 'notEqual', 'not equal', 'neq']

    def __init__(self, element):
        super(XMLConstraint, self).__init__(element)
        self.column = element.get('column')
        self.op = element.get('op')
        self.value = element.get('value')
        self.groupBy = element.get('groupby')

        if self.op:
            known = self.equal + self.notEqual
            if not self.op in known:
                raise PygcamMcsUserError('Unknown operator in constraint: %s' % self.op)

            if not self.value:
                raise PygcamMcsUserError('Constraint with operator "%s" is missing a value' % self.op)

    def asString(self):
        op = '==' if self.op in self.equal else ('!=' if self.op in self.notEqual else None)

        if op:
            return "%s %s %r" % (self.column, op, self.value)

        return None


class XMLColumn(XMLWrapper):
    def __init__(self, element):
        super(XMLColumn, self).__init__(element)


class XMLResult(XMLWrapper):
    '''
    Represents a single Result (model output) from the results.xml file.
    '''
    def __init__(self, element):
        super(XMLResult, self).__init__(element)
        self.name = element.get('name')
        self.type = element.get('type', DEFAULT_RESULT_TYPE)
        self.desc = element.get('desc')
        self.queryFile = self._getPath(FILE_ELT_NAME)

        col = self.element.find(COLUMN_ELT_NAME)
        self.column = XMLColumn(col) if col is not None else None

        # Create the "where" clause to use with a DataFrame.query() on the results we'll read in
        self.constraints = map(XMLConstraint, self.element.iterfind(CONSTRAINT_ELT_NAME))
        constraintStrings = filter(None, map(XMLConstraint.asString, self.constraints))
        self.whereClause = ' and '.join(constraintStrings)

    def isScalar(self):
        return self.column is not None

    def _getPath(self, eltName):
        'Get a single filename from the named element'
        objs = self.element.findall(eltName)
        filename = objs[0].get('name')
        if os.path.isabs(filename):
            raise PygcamMcsUserError("For %s named %s: path (%s) must be relative" % (eltName, self.name, filename))

        return filename

    def csvPathname(self, scenario, baseline=None, outputDir='.', type=RESULT_TYPE_SCENARIO):
        """
        Compute the pathname of a .csv file from an outputDir,
        scenario name, and optional baseline name.
        """
        # Output files are stored in the output dir with same name as query file but with 'csv' extension.
        basename = os.path.basename(self.queryFile)
        mainPart, extension = os.path.splitext(basename)
        middle =  scenario if type == RESULT_TYPE_SCENARIO else ("%s-%s" % (scenario, baseline))
        csvFile = "%s-%s.csv" % (mainPart, middle)
        csvPath = os.path.abspath(os.path.join(outputDir, csvFile))
        return csvPath

    def columnName(self):
        return self.column.getName() if self.column is not None else None


class XMLResultFile(XMLFile):
    """
    XMLResultFile manipulation class.
    """

    cache = {}

    @classmethod
    def getInstance(cls, filename):
        try:
            return cls.cache[filename]

        except KeyError:
            obj = cls.cache[filename] = cls(filename)
            return obj

    def __init__(self, filename):
        super(XMLResultFile, self).__init__(filename, load=True, schemaPath='mcs/etc/results-schema.xsd')
        root = self.tree.getroot()

        self.results = OrderedDict()    # the parsed fileNodes, keyed by filename
        findAndSave(root, RESULT_ELT_NAME, XMLResult, self.results)

    def getResultDefs(self, type=None):
        """
        Get results of type 'diff' or 'scenario'
        """
        results = self.results.values()

        if type:
            results = filter(lambda result: result.type == type, results)

        return results

    def saveOutputDefs(self):
        '''
        Save the defined outputs in the SQL database
        '''
        db = getDatabase()
        session = db.Session()
        for result in self.getResultDefs():
            db.createOutput(result.name, description=result.desc, session=session)

        session.commit()
        db.endSession(session)

    @classmethod
    def addOutputs(cls):
        resultsFile = getParam('MCS.ResultsFile')
        obj = cls(resultsFile)
        obj.saveOutputDefs()

class QueryResult(object):
    '''
    Holds the results of an XPath batch query
    '''
    def __init__(self, filename):
        self.filename = filename
        self.title = None
        self.df    = None
        self.units = None
        self.readCSV()

    @staticmethod
    def parseScenarioString(scenStr):
        """
        Parse a GCAM scenario string into a name and a time stamp

        :param scenStr: (str) a scenario name string of the form
           "Reference,date=2014-29-11T08:10:45-08:00"

        :return: (str, datetime) the scenario name and a datetime instance
        """
        name, datePart = scenStr.split(',')
        # _logger.debug("datePart: %s", datePart)
        dateWithTZ = datePart.split('=')[1]     # drop the 'date=' part
        # _logger.debug("dateWithTZ: %s", dateWithTZ)

        # drops the timezone info with strptime doesn't handle.
        # TBD: this is ok as long as all the scenarios were run in the same timezone...
        lenTZ = len("-00:00")
        dateWithoutTZ = dateWithTZ[:-lenTZ]
        # _logger.debug("dateWithoutTZ: %s", dateWithoutTZ)

        runDate = datetime.strptime(dateWithoutTZ, "%Y-%d-%mT%H:%M:%S")   # N.B. order is DD-MM, not MM-DD
        return name, runDate

    def readCSV(self):
        '''
        Read a CSV file produced by a batch query. The first line is the name of the query;
        the second line provides the column headings; all subsequent lines are data. Data
        are comma-delimited, and strings with spaces are double-quoted. Assume units are
        the same as in the first row of data.
        '''
        _logger.debug("readCSV: reading %s", self.filename)
        with open(self.filename) as f:
            self.title  = f.readline().strip()
            self.df = pd.read_table(f, sep=',', header=0, index_col=False, quoting=0)

        df = self.df

        if 'Units' in df.columns:
            self.units = df.Units[0]

        # split the scenario field into two parts; here we create the columns
        df['ScenarioName'] = None
        df['ScenarioDate'] = None

        if 'scenario' in df.columns:        # not the case for "diff" files
            name, date = self.parseScenarioString(df.loc[0].scenario)
            df['ScenarioName'] = name
            df['ScenarioDate'] = date

    def getFilename(self):
        return self.filename

    def getTitle(self):
        return self.title

    def getData(self):
        return self.df


def collectResults(context, type):
    '''
    Called by worker to process results, return a list of dicts
    with data the master process can quickly write to the database.
    '''
    from collections import defaultdict
    from .util import getSimResultFile, activeYears, YEAR_COL_PREFIX

    _logger.debug("Collecting results for %s", context)

    baseline = context.baseline
    scenario = context.scenario

    if type == RESULT_TYPE_DIFF:
        assert baseline, "saveResults: must specify baseline for DIFF results"

    resultsFile = getSimResultFile(context.simId)
    rf = XMLResultFile.getInstance(resultsFile)
    outputDefs = rf.getResultDefs(type=type)

    if not outputDefs:
        _logger.info('saveResults: No outputs defined for type %s', type)
        return []

    # TBD: was used to delete prior results; may not be needed
    # names = map(XMLResult.getName, outputDefs)

    activeYears = activeYears()
    yearCols = map(lambda y: YEAR_COL_PREFIX + y, activeYears)

    # A single result DF can have data for multiple outputs, so we cache the files
    outputCache = defaultdict(lambda: None)

    trialDir = context.getTrialDir()

    # TBD: create context.getQueryResultsDir() ?
    scenarioOutputDir = os.path.join(trialDir, scenario, 'queryResults')

    # TBD: create context.getDiffsDir() ?
    diffsOutputDir = os.path.join(trialDir, scenario, 'diffs')

    outputDir = scenarioOutputDir if type == RESULT_TYPE_SCENARIO else diffsOutputDir

    resultList = []

    for output in outputDefs:
        csvPath = output.csvPathname(scenario, baseline=baseline, outputDir=outputDir, type=type)

        if not outputCache[csvPath]:
            try:
                outputCache[csvPath] = QueryResult(csvPath)
            except Exception as e:
                _logger.warning('saveResults: Failed to read query result: %s', e)
                raise FileMissingError(csvPath)

        queryResult = outputCache[csvPath]
        paramName   = output.name
        whereClause = output.whereClause

        selected = queryResult.df.query(whereClause) if whereClause else queryResult.df
        count = selected.shape[0]
        if count == 0:
            raise PygcamMcsUserError('Query where clause(%r) matched no results' % whereClause)

        if 'region' in selected.columns:
            firstRegion = selected.region.iloc[0]
            if count == 1:
                regionName = firstRegion
            else:
                _logger.debug(
                    "Query where clause (%r) yielded %d rows; year columns will be summed" % (whereClause, count))
                regionName = firstRegion if len(selected.region.unique()) == 1 else 'Multiple'
        else:
            regionName = 'global'

        # Create a dict to return. No need to store runId or scenario; context has these already
        resultDict = dict(regionName=regionName, paramName=paramName)

        if output.isScalar():
            colName = output.columnName()
            value = selected[colName].iloc[0]
            resultDict['isScalar'] = True
        else:
            # When no column name is specified, assume this is a time-series result, so save all years.
            # Use sum() to collapse values to a single time series; for a single row it helpfully
            # converts the 1-element series to a simple float.
            value = {colName: selected[yearStr].sum() for colName, yearStr in zip(yearCols, activeYears)}
            resultDict['isScalar'] = False
            resultDict['units'] = queryResult.units

        resultDict['value'] = value
        resultList.append(resultDict)

    # a list of dicts with results for this trial
    return resultList

def saveResults(context, resultList):
    '''
    Called on the master to save results to the database that were prepared by the worker.
    '''
    from .Database import getDatabase

    runId = context.runId

    db = getDatabase()
    session = db.Session()

    # Delete any stale results for this runId (i.e., if re-running a given runId)
    names = map(lambda resultDict: resultDict['paramName'], resultList)
    ids = db.getOutputIds(names)
    db.deleteRunResults(runId, outputIds=ids, session=session)
    db.commitWithRetry(session)

    for resultDict in resultList:
        paramName  = resultDict['paramName']
        value      = resultDict['value']
        regionName = resultDict['regionName']
        regionId = db.getRegionId(regionName)

        # Save the values to the database
        try:
            if resultDict['isScalar']:
                db.setOutValue(runId, paramName, value, session=session)  # TBD: need regionId?
            else:
                units = resultDict['units']
                db.saveTimeSeries(runId, regionId, paramName, value, units=units, session=session)

        except Exception as e:
            session.rollback()
            db.endSession(session)
            # TBD: distinguish database save errors from data access errors?
            raise PygcamMcsSystemError("saveResults failed: %s" % e)

    db.commitWithRetry(session)
    db.endSession(session)
