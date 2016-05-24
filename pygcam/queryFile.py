'''
.. Created on: 5/11/16
.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from .utils import XMLFile, getBooleanXML, resource_stream

#
# Classes to parse queryFiles and the <queries> element of project.xml
# (see pygcam/etc/queryFile-schema.xsd). These are in a separate file
# for sharing between query.py and project.py
#
class Query(object):
    def __init__(self, node, defaultMap):
        self.name = node.get('name')
        self.useDefault = getBooleanXML(node.get('useDefault', '1'))

        # Create a list of tuples with (mapName, level) where level may be None
        rewriters = node.findall('rewriter')
        self.rewriters = map(lambda obj: (obj.get('name'), obj.get('level')), rewriters)

        if defaultMap and self.useDefault:
            rewriters.append((defaultMap, None))

class QueryFile(object):
    def __init__(self, node):
        defaultMap = self.defaultMap = node.get('defaultMap', None)

        nodes = node.findall('query')
        self.queries = [Query(node, defaultMap) for node in nodes]

    @classmethod
    def parse(cls, filename):
        """
        Parse an XML file holding a list of query descriptions.
        :param filename: (str) the name of the XML file to read
        :return: a QueryFile instance.
        """
        schemaStream = resource_stream('pygcam', 'etc/queryFile-schema.xsd')
        xmlFile = XMLFile(filename, schemaFile=schemaStream)
        return cls(xmlFile.tree.getroot())
