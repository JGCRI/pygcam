'''
.. Created on: 5/11/16
.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from .utils import XMLFile, getBooleanXML, resourceStream

#
# Classes to parse queryFiles and the <queries> element of project.xml
# (see pygcam/etc/queryFile-schema.xsd). These are in a separate file
# for sharing between query.py and project.py
#
class Query(object):
    def __init__(self, node, defaultMap):
        self.name = node.get('name')
        self.delete = getBooleanXML(node.get('delete', '1'))
        self.useDefault = useDefault = getBooleanXML(node.get('useDefault', '1'))

        # see if the user provided the attribute, or we defaulted to 1
        explicitUseDefault = node.get('useDefault', None) and useDefault

        # Create a list of tuples with (mapName, level) where level may be None
        rewriters = node.findall('rewriter')
        self.rewriters = map(lambda obj: (obj.get('name'), obj.get('level')), rewriters)

        # We add the default map in two cases: (i) user specified some rewriters and explicitly
        # set useDefault="1", or (ii) there are no rewriters and useDefault has not been set to "0".
        if defaultMap and ((rewriters and explicitUseDefault) or (not rewriters and useDefault)):
            self.rewriters.append((defaultMap, None))

    def getName(self):
        return self.name

class QueryFile(object):
    def __init__(self, node):
        defaultMap = self.defaultMap = node.get('defaultMap', None)

        nodes = node.findall('query')
        self.queries = [Query(node, defaultMap) for node in nodes]

    def queryNames(self):
        names = map(Query.getName, self.queries)
        return names

    @classmethod
    def parse(cls, filename):
        """
        Parse an XML file holding a list of query descriptions.
        :param filename: (str) the name of the XML file to read
        :return: a QueryFile instance.
        """
        schemaStream = resourceStream('etc/queryFile-schema.xsd')
        xmlFile = XMLFile(filename, schemaFile=schemaStream)
        return cls(xmlFile.tree.getroot())
