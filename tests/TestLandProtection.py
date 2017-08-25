import unittest
import os
import subprocess
from pygcam.landProtection import _makeLandClassXpath, _makeRegionXpath, protectLand, runProtectionScenario
from pygcam.windows import IsWindows

class TestLandProtection(unittest.TestCase):
    def setUp(self):
        pass

    def assertFilesEqual(self, outfile, testfile, deleteOnSuccess=True):
        '''
        Run diff on two files and test that there is no difference.
        '''
        # print "diff %s %s" % (outfile, testfile)
        diffCmd = r"c:\cygwin64\bin\diff" if IsWindows else "diff"
        status = subprocess.call([diffCmd, '-w', outfile, testfile], shell=False)  # -w => ignore whitespace
        self.assertEqual(status, 0, 'Files %s and %s differ' % (outfile, testfile))
        if deleteOnSuccess:
            os.unlink(outfile) # doesn't happen if assertion fails, so file can be examined


    def test_makeRegionXpath(self):
        pairs = (('USA', "//region[@name='USA']"),
                 (['EU15', 'Brazil'], "//region[@name='EU15' or @name='Brazil']"),
                 (None, ""))

        for value, expected in pairs:
            xpath = _makeRegionXpath(value)
            self.assertEqual(xpath, expected, 'Expected\n\t%s\ngot\n\t%s' % (expected, xpath))

    def test_makeLandXpath(self):
        pairs = (('Shrubland',
                  './/UnmanagedLandLeaf[starts-with(@name, "Shrubland")]'),
                 (['Shrubland', 'UnmanagedForest'],
                  './/UnmanagedLandLeaf[starts-with(@name, "Shrubland") or starts-with(@name, "UnmanagedForest")]'))

        for value, expected in pairs:
            xpath = _makeLandClassXpath(value)
            self.assertEqual(xpath, expected, 'Expected\n\t%s\ngot\n\t%s' % (expected, xpath))

    def test_createProtected_land_2(self):
        protectedFraction = 0.9
        classes = ['UnmanagedPasture', 'UnmanagedForest', 'Shrubland']
        regions = ['Brazil', 'USA']

        xmlDir = os.path.join('data', 'xml')

        for num in (2, 3):
            infile   = os.path.join(xmlDir, 'partial_land_input_%d.xml' % num)
            outfile  = os.path.join(xmlDir, 'changed_land_input_%d.xml' % num)
            testfile = os.path.join(xmlDir, 'expected_land_input_%d.xml' % num)

            protectLand(infile, outfile, protectedFraction, landClasses=classes, regions=regions)
            self.assertFilesEqual(outfile, testfile)

    def test_protection_scenario(self):
        scenarioName = 'test'
        xmlDir = os.path.join('data', 'xml')
        tmpDir = os.path.join('data', 'tmp')

        scenarioFile = os.path.join(xmlDir, 'protection.xml')

        xmlFiles = map(lambda num: os.path.join(xmlDir, 'partial_land_input_%d.xml' % num), (2, 3))

        runProtectionScenario(scenarioName, outputDir=tmpDir, scenarioFile=scenarioFile,
                              xmlFiles=xmlFiles, inPlace=False)

        for num in (2, 3):
            outfile  = os.path.join(tmpDir, 'partial_land_input_%d.xml' % num)
            testfile = os.path.join(xmlDir, 'test_scenario_land_input_%d.xml' % num)

            self.assertFilesEqual(outfile, testfile)


if __name__ == "__main__":
    unittest.main()
