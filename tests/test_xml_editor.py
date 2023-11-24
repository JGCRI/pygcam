import pytest
from pygcam.mcs.error import PygcamMcsUserError
from pygcam.sectorEditors import extractStubTechnology
from pygcam.xml_edit import xmlSel, xmlEdit
from pygcam.XMLConfigFile import XMLConfigFile, INTS_GROUP

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


def test_xml_config_file():
    cfg_file  = XMLConfigFile.get_instance(cfg_path)
    cfg_file2 = XMLConfigFile.get_instance(cfg_path)

    # ensure that second call returns cached instance
    assert cfg_file == cfg_file2

    tag = 'test-tag'
    path = '../../foo/bar.xml'
    cfg_file.add_component_pathname(tag, path)
    assert cfg_file.get_component_pathname(tag) == path

    path2 = '../../local-xml/foo/bar.xml'
    cfg_file.update_component_pathname(tag, path2)
    assert cfg_file.get_component_pathname(tag) == path2

    cfg_file.delete_component(tag)
    with pytest.raises(PygcamMcsUserError, match=r".* not found"):
        cfg_file.get_component_pathname(tag)

    with pytest.raises(PygcamMcsUserError, match=r".* not found in group .*"):
        cfg_file.delete_component(tag)

    path3  = '../trial-xml/foo/bar.xml'
    cfg_file.insert_component_pathname(tag, path3, 'demand')
    assert cfg_file.get_component_pathname(tag) == path3

    with pytest.raises(PygcamMcsUserError, match=r".* doesn't exist"):
        cfg_file.insert_component_pathname(tag, path3, 'nonexistent-tag')

    with pytest.raises(PygcamMcsUserError, match=r".* not found"):
        cfg_file.get_config_group('nonexistent-group')

    int_arg = 'climateOutputInterval'
    with pytest.raises(PygcamMcsUserError, match=r".* must provide newTag or text, or both"):
        cfg_file.update_config_element(int_arg, INTS_GROUP, newName=None, newValue=None)

    value = '1'
    cfg_file.update_config_element(int_arg, INTS_GROUP, newValue=value)
    elt = cfg_file.get_config_element(int_arg, INTS_GROUP)
    assert elt.text == value

    new_name = 'climate-output-interval'
    cfg_file.update_config_element(int_arg, INTS_GROUP, newName=new_name)
    # old elt should have been edited in place
    assert elt.attrib['name'] == new_name
