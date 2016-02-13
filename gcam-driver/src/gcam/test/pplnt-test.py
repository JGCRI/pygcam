#!/usr/bin/env python
"""Test functions for processing power plant water data.
"""

import sys
## enable this code to run from the gcam/test/ directory
sys.path.append('../..')

import gcam.water
from gcam.water import pplnt
import json
import unittest 

class TestPplnt(unittest.TestCase):
    def setUp(self):
        """ Runs functions to be tested and sets up test variables. 
        """
        infile = open('data/toy.json', 'r')          
        dict1 = {'Coal': 1, 'Gas':2, 'Nuclear':3}
        
        self.json = pplnt.getWaterUsage(infile, dict1)
        self.features = self.json["features"]
        self.tupleList = pplnt.pplnt_convertjson(self.json)
        self.grid = pplnt.pplnt_grid(self.tupleList)
        
        self.waterValues = [650.0, 500.0, 600.0, 2640.0] #List of expected values for water usage
        self.len = 4 #Expected number of plants (# in data file)
        
        
        infile.close()
        
    def testWaterValue(self):
        """Verify that water-usage value is a float and equals the expected
        value.
        """
        self.assertEqual(len(self.features), self.len)
        
        i = 0
        for plant in self.features:
            self.assertIs(type(plant["properties"]["water-usage"]), float)
            self.assertEqual(plant["properties"]["water-usage"], self.waterValues[i])
            i +=1

    def testConvertJSON(self):
        """Verify that pplnt_convertjson works correctly."""
        #Make sure all plants were copied over
        self.assertEqual(len(self.tupleList), len(self.features))

        i = 0
        for plant in self.tupleList:
            #Check that tuples are all equal to 3
            self.assertEqual(len(plant), 3)
            #Check that longitude is a float equal to json input
            self.assertEqual(plant[0], self.features[i]["geometry"]["coordinates"][0])
            self.assertIs(type(plant[0]), float)
            #Check that latitude is a float equal to json input
            self.assertEqual(plant[1], self.features[i]["geometry"]["coordinates"][1])
            self.assertIs(type(plant[1]), float)
            #check that water is equal to json input
            self.assertEqual(plant[2], self.features[i]["properties"]["water-usage"])
            i+=1

    def testPplntGrid(self):
        """Test pplnt_grid by comparing expected dictionary to actual."""
        #List of expected key and water values
        expectedDict={(239,113):1150.0, (663,113):600.0, (661,115):2640.0}

        #Check that grid conversion worked properly and that water values are
        #correct
        i = 0
        for key in self.grid:
            self.assertDictEqual(self.grid, expectedDict)
        



if __name__ == '__main__':
    unittest.main()
    
