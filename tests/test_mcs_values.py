import unittest

from pygcam.XMLFile import McsValues


class TestSymlinks(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_read(self):
        filename = 'data/xml/mcsValues-example.xml'
        mcsValues = McsValues(filename)

        regions = mcsValues.regions()

        self.assertTrue(regions, 'regions() returned an empty list')
        self.assertEqual(len(regions), 2, 'Wrong number of regions; should be 2')

        regionSet = set(regions)
        expectedSet = set(['USA', 'China'])
        self.assertEqual(regionSet, expectedSet, 'Expected %s, got %s' % (expectedSet, regionSet))

        chinaValues = mcsValues.values('China')
        self.assertTrue(chinaValues, "Failed to find values for China")

        expectedSet = set([0.25, 1.25, 1.5])
        chinaSet = set(chinaValues.values())
        self.assertTrue(chinaSet == expectedSet, "Expected values %s, got %s" % (expectedSet, chinaSet))


        expectedSet = set(['biodiesel', 'cellulosic ethanol', 'corn ethanol'])
        chinaSet = set(chinaValues.keys())
        self.assertTrue(chinaSet == expectedSet, "Expected names %s, got %s" % (expectedSet, chinaSet))
