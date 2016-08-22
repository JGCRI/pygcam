'''
.. Created on: 8/21/16
.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from pygcam.utils import XMLFile, getBooleanXML, resourceStream

#
# Classes to parse "simple" scenario setup files.
# (See pygcam/etc/scenarioSetup-schema.xsd).
#
class ScenarioSetup(object):
    def __init__(self, node):
        self.name = node.get('name')

        self.iterators  = map(Iterator, node.findall('vars/iterator'))
        self.scenGroups = map(ScenarioGroup, node.findall('scenarioGroup'))

        # self.delete = getBooleanXML(node.get('delete', '1'))
        # self.useDefault = useDefault = getBooleanXML(node.get('useDefault', '1'))

    @classmethod
    def parse(cls, filename):
        """
        Parse an XML file holding a list of query descriptions.
        :param filename: (str) the name of the XML file to read
        :return: a QueryFile instance.
        """
        schemaStream = resourceStream('etc/scenarioSetup-schema.xsd')
        xmlFile = XMLFile(filename, schemaFile=schemaStream)
        return cls(xmlFile.tree.getroot())

    def run(self, name, scenario, group=None):
        """
        Run the setup with the given `name`.

        :param name: (str) the name of the ScenarioSetup
        :param scenario: (str) the name of the scenario to run
        :param group: (str) name of scenario group. If not provided,
           the default group will be used, or the only group if there
           is only one.
        :return: none
        """
        pass

class Iterator(object):
    def __init__(self, node):
        self.name = node.get('name')
        self.type = numericType = int if node.get('type') == 'int' else float
        self.min  = numericType(node.get('min'))
        self.max  = numericType(node.get('max'))
        self.incr = numericType(node.get('incr', 1))

        iterators  = map(Iterator, node.findall('vars/iterators'))
        scenGroups = map(ScenarioGroup, node.findall('scenarioGroup'))

    def __str__(self):
        return "<iterator name='%s' type='%s' min='%s' max='%s' incr='%s'/>" % \
               (self.name, self.type, self.min, self.max, self.incr)

class ScenarioGroup(object):
    def __init__(self, node):
        self.name = node.get('name')
        self.useGroupDir = getBooleanXML(node.get('useGroupDir', 0))
        self.iteratorName = node.get('iterator')

        self.scenarios = map(Scenario, node.findall('scenario'))

class Scenario(object):
    def __init__(self, node):
        self.name = node.get('name')
        self.active   = getBooleanXML(node.get('baseline', 0))
        self.baseline = getBooleanXML(node.get('active', 1))
        self.iteratorName = node.get('iterator')

        self.actions = map(ConfigAction, node.findall('config'))
        self.generators = map(Generator, node.findall('generator'))

    def __str__(self):
        return "<scenario name='%s'>" % self.name

class ConfigAction(object):
    def __init__(self, node):
        self.name = node.get('name')
        self.action = node.get('action')
        self.dir = node.get('dir', '')
        self.xmlFile = node.text

    def __str__(self):
        return "<config name='%s' action='%s' dir='%s'>%s</config>" % \
               (self.name, self.action, self.dir, self.xmlFile)

class Generator(object):
    def __init__(self, node):
        self.name = node.get('name')
        self.content = node.text

    def __str__(self):
        return "<generator name='%s'>%s</generator>" % (self.name, self.content)


if __name__ == '__main__':
    obj = ScenarioSetup.parse('etc/scenarioSetup-example.xml')
    print obj
