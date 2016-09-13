'''
.. Created on: 5/11/16
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from .error import PygcamException
from .utils import XMLFile, getBooleanXML, resourceStream

#
# Classes to parse queryFiles and the <queries> element of project.xml
# (see pygcam/etc/queries-schema.xsd). These are in a separate file
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
        schemaStream = resourceStream('etc/queries-schema.xsd')
        xmlFile = XMLFile(filename, schemaFile=schemaStream)
        return cls(xmlFile.tree.getroot())

#
# Classes to parse rewriteSets.xml (see pygcam/etc/rewriteSets-schema.xsd)
#
class Rewrite(object):
    def __init__(self, node):
        self.From = node.get('from')    # 'from' is a keyword...
        self.to   = node.get('to')
        self.byAEZ = getBooleanXML(node.get('byAEZ', '0'))

    def __str__(self):
        return "<Rewrite from='%s' to='%s' byAEZ='%s'>" % (self.From, self.to, self.byAEZ)


class RewriteSet(object):
    def __init__(self, node):
        self.name  = node.get('name')
        self.level = node.get('level')
        self.byAEZ = getBooleanXML(node.get('byAEZ', '0'))
        self.appendValues = getBooleanXML(node.get('append-values', '0'))
        self.rewrites = map(Rewrite, node.findall('rewrite'))

    def __str__(self):
        return "<RewriteSet name='%s' level='%s' byAEZ='%s' append-values='%s'>" % \
               (self.name, self.level, self.byAEZ, self.appendValues)

class RewriteSetParser(object):
    def __init__(self, node, filename):
        rewriteSets = map(RewriteSet, node.findall('rewriteSet'))
        self.rewriteSets = {obj.name : obj for obj in rewriteSets}
        self.filename = filename # for error messages only

    def getRewriteSet(self, name):
        try:
            return self.rewriteSets[name]
        except KeyError:
            raise PygcamException('RewriteSet "%s" not found in file "%s"' % (name, self.filename))

    @classmethod
    def parse(cls, filename):
        """
        Parse an XML file holding a list of query result rewrites.
        :param filename: (str) the name of the XML file to read
        :return: a list of RewriteSet instances
        """
        schemaStream = resourceStream('etc/rewriteSets-schema.xsd')
        xmlFile = XMLFile(filename, schemaFile=schemaStream)
        return cls(xmlFile.tree.getroot(), filename)
