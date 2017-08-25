from __future__ import print_function
from pygcam.xmlEditor import xmlSel, xmlEdit, extractStubTechnology

cfg = './data/xml/configuration_ref.xml'

def testSel(xpath):
    print('%s: %s' % (xpath, xmlSel(cfg, xpath)))

testSel('//ScenarioComponents/Value[@name="socioeconomics"]')
testSel('//ScenarioComponents/Value[@name="industry"]')
testSel('//ScenarioComponents/Value[@name="foobar"]')

def testEdit(pairs):
    xmlEdit(cfg, pairs)

testEdit([("//Bools/Value[@name='PrintPrices']", 1)])
testEdit([("//Files/Value[@name='dbFileName']/@write-output", 0),
          ("//Ints/Value[@name='stop-period']", -1)])


energy_trans = '/Users/rjp/GCAM/current/input/gcam-data-system/xml/energy-xml/en_transformation.xml'
outfile = '/Users/rjp/tmp/extracted.xml'

extractStubTechnology('USA', energy_trans, outfile,  'refining', 'biomass liquids', 'corn ethanol')
