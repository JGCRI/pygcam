from pygcam.xmlEditor import xmlSel, xmlEdit

cfg = '/Users/rjp/tmp/configuration_ref.xml'

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

