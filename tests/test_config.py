import pytest
from .utils_for_testing import load_config_from_string
from pygcam.config import setParam, setSection, getParam, getParamAsBoolean, getParamAsInt, getParamAsFloat

config_text_1 = """[test_section]
TestInteger = 123
TestFloat = 456.789
TestBoolean = yes
TestString = something that
    includes a newline
"""

def test_get_param():
    load_config_from_string(config_text_1)

    section = 'test_section'
    setSection(section)

    assert getParam("TestString") == "something that\nincludes a newline"

    assert getParamAsFloat('TestFloat') == 456.789
    assert getParamAsInt('TestInteger') == 123
    assert getParamAsBoolean('TestBoolean') == True

    with pytest.raises(TypeError):
        assert setParam('TestInteger', 123) # values must be strings


@pytest.mark.parametrize("value, expected",
                         [('yes', True),
                          ('1', True),
                          ('TRUE', True),
                          ('No', False),
                          ('0', False),
                          ('FaLsE', False)])
def test_get_boolean(value, expected):
    setParam('TestBoolean', value)
    assert getParamAsBoolean('TestBoolean') == expected


