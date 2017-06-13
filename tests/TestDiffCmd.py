import os
import shutil
from unittest import TestCase

from pygcam.query import readCsv, readQueryResult
from pygcam.diff import computeDifference
from pygcam.utils import QueryResultsDir, mkdirs

class TestDiffCmd(TestCase):
    def setUp(self):
        self.ws = './data/ws'
        self.baseline = 'base-0'
        self.policy   = 'corn-0'
        self.queryDir = 'queryResults'
        self.years = [2015, 2050]

        self.tmpDir = '/tmp/testDiff'
        self.removeTmpDir()         # start clean
        mkdirs(self.tmpDir)

    def tearDown(self):
        self.removeTmpDir()

    def removeTmpDir(self):
        try:
            shutil.rmtree(self.tmpDir)
        except:
            pass

    def getFilename(self, scenario):
        return os.path.join(self.ws, scenario, QueryResultsDir)

    def readPurposeGrown(self, scenario):
        batchDir = self.getFilename(scenario)
        df = readQueryResult(batchDir, scenario, 'Purpose-grown_biomass_production',
                             years=self.years, interpolate=False)
        return df

    def test_computeDifference(self):
        baseDF = self.readPurposeGrown(self.baseline)
        cornDF = self.readPurposeGrown(self.policy)

        computedDiff = computeDifference(baseDF, cornDF)

        infile = os.path.join(self.ws, self.policy, 'diffs', 'expected-Purpose-grown_biomass_production-corn-0-base-0.csv')
        expectedDiff = readCsv(infile, years=self.years, interpolate=False)

        # check that all values are suitably close to zero
        testDiff = computeDifference(expectedDiff, computedDiff)
        yearCols = filter(str.isdigit, testDiff.columns)
        bools = abs(testDiff[yearCols]) > 1e-8
        self.assertFalse(bools.all().all())



