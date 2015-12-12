import unittest
import os
import subprocess
from pygcam.landProtection import *

class TestLandProtection(unittest.TestCase):
    def setUp(self):
        pass

    def test_makeRegionXpath(self):
        pairs = (('USA', "//region[@name='USA']"),
                 (['EU15', 'Brazil'], "//region[@name='EU15' or @name='Brazil']"),
                 (None, ""))

        for value, expected in pairs:
            xpath = makeRegionXpath(value)
            self.assertEqual(xpath, expected, 'Expected\n\t%s\ngot\n\t%s' % (expected, xpath))

    def test_makeLandCoverXpath(self):
        pairs = (('Shrubland',
                  ".//UnmanagedLandLeaf[starts-with(@name, 'Shrubland')]"),
                 (['Shrubland', 'UnmanagedForest'],
                  ".//UnmanagedLandLeaf[starts-with(@name, 'Shrubland') or starts-with(@name, 'UnmanagedForest')]"))

        for value, expected in pairs:
            xpath = makeLandCoverXpath(value)
            self.assertEqual(xpath, expected, 'Expected\n\t%s\ngot\n\t%s' % (expected, xpath))

    def test_createProtected_land_2(self):
        parser = ET.XMLParser(remove_blank_text=True)

        protFrac = 0.9
        covers = ['UnmanagedPasture', 'UnmanagedForest', 'Shrubland']
        regions = ['Brazil', 'USA']

        for num in (2, 3):
            infile   = os.path.join('xml', 'partial_land_input_%d.xml' % num)
            outfile  = os.path.join('xml', 'changed_land_input_%d.xml' % num)
            testfile = os.path.join('xml', 'expected_land_input_%d.xml' % num)

            tree = ET.parse(infile, parser)
            print "Testing protection of %.2f of %s in %s, file: %s" % (protFrac, covers, regions, infile)
            createProtected(tree, protFrac, landCovers=covers, regions=regions)
            tree.write(outfile, xml_declaration=True, pretty_print=True)

            status = subprocess.call(['diff', outfile, testfile], shell=False)
            self.assertEqual(status, 0, 'Files %s and %s differ' % (outfile, testfile))
            print "Deleting %s" % outfile
            os.unlink(outfile) # doesn't happen if assertion fails, so file can be examined


if __name__ == "__main__":
    unittest.main()
