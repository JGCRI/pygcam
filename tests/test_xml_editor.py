import pytest
from pygcam.xmlEditor import extractStubTechnology
from pygcam.xml_edit import xmlSel, xmlEdit

cfg_path = './data/xml/configuration_ref.xml'

@pytest.mark.parametrize("xpath, expected",
                         [('//ScenarioComponents/Value[@name="socioeconomics"]', True),
                          ('//ScenarioComponents/Value[@name="industry"]', True),
                          ('//ScenarioComponents/Value[@name="foobar"]', False),
                         ])
def test_sel(xpath, expected):
    assert xmlSel(cfg_path, xpath) == expected


@pytest.mark.parametrize("xpath, value",
                         [("//Bools/Value[@name='PrintPrices']", 1),
                          ("//Files/Value[@name='dbFileName']/@write-output", 0),
                          ("//Ints/Value[@name='stop-period']", -1)
                          ])
def test_edit(xpath, value):
    xmlEdit(cfg_path, [(xpath, value)])

def test_extract_stub_tech():
    energy_trans = '/Volumes/Plevin1TB/Software/GCAM/6.0/gcam-core/input/gcamdata/xml/en_transformation.xml'
    outfile = '/Users/rjp/tmp/extracted.xml'

    extractStubTechnology('USA', energy_trans, outfile,  'refining', 'biomass liquids', 'corn ethanol')
