'''
.. Created on: 5/11/16
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from collections import defaultdict

from .config import getParam
from .error import PygcamException
from .utils import getBooleanXML, resourceStream
from .XMLFile import XMLFile

#
# Classes to parse queryFiles and the <queries> element of project.xml
# (see pygcam/etc/queries-schema.xsd). These are in a separate file
# for sharing between query.py and project.py
#
class Query(object):
    def __init__(self, node, defaultMap):
        self.name = node.get('name')
        self.saveAs = node.get('saveAs', self.name)
        self.delete = getBooleanXML(node.get('delete', '1'))
        self.useDefault = useDefault = getBooleanXML(node.get('useDefault', '1'))
        self.states = node.get('states', 'none')

        # see if the user provided the attribute, or we defaulted to 1
        explicitUseDefault = node.get('useDefault', None) and useDefault

        # Create a list of tuples with (mapName, level) where level may be None
        rewriters = node.findall('rewriter')
        self.rewriters = [(obj.get('name'), obj.get('level')) for obj in rewriters]

        # We add the default map in two cases: (i) user specified some rewriters and explicitly
        # set useDefault="1", or (ii) there are no rewriters and useDefault has not been set to "0".
        if defaultMap and ((rewriters and explicitUseDefault) or (not rewriters and useDefault)):
            self.rewriters.append((defaultMap, None))


class QueryFile(object):
    def __init__(self, node):
        defaultMap = self.defaultMap = node.get('defaultMap', None)

        nodes = node.findall('query')
        self.queries = [Query(node, defaultMap) for node in nodes]

    def queryFilenames(self):
        """
        Return the name used to compose the filename for this query, which
        may differ from the original query name, e.g., if the same query
        needs to be rewritten differently for different purposes.
        """
        names = [q.saveAs for q in self.queries]
        return names

    @classmethod
    def parse(cls, filename):
        """
        Parse an XML file holding a list of query descriptions.
        :param filename: (str) the name of the XML file to read
        :return: a QueryFile instance.
        """
        xmlFile = XMLFile(filename, schemaPath='etc/queries-schema.xsd', conditionalXML=True)
        return cls(xmlFile.tree.getroot())

#
# Classes to parse rewriteSets.xml (see pygcam/etc/rewriteSets-schema.xsd)
#
class Rewrite(object):
    def __init__(self, node):
        self.From = node.get('from')    # 'from' is a keyword...
        self.to   = node.get('to')
        self.byAEZ = getBooleanXML(node.get('byAEZ', '0'))
        self.byBasin = getBooleanXML(node.get('byBasin', '0'))    # TBD: GCAM5

    def __str__(self):
        # TBD: Add byBasin for GCAM5
        return "<Rewrite from='%s' to='%s' byAEZ='%s'>" % (self.From, self.to, self.byAEZ)


class RewriteSet(object):
    def __init__(self, node):
        self.name  = node.get('name')
        self.level = node.get('level')
        self.byAEZ = getBooleanXML(node.get('byAEZ', '0'))
        self.byBasin = getBooleanXML(node.get('byBasin', '0'))   # TBD: GCAM5
        self.appendValues = getBooleanXML(node.get('append-values', '0'))
        self.rewrites = [Rewrite(x) for x in node.findall('rewrite')]

    def __str__(self):
        # TBD: Add byBasin for GCAM5
        return "<RewriteSet name='%s' level='%s' byAEZ='%s' append-values='%s'>" % \
               (self.name, self.level, self.byAEZ, self.appendValues)

    def asRegionMap(self):
        regionMap = defaultdict(list)
        for rewrite in self.rewrites:
            regionMap[rewrite.to].append(rewrite.From)

        return regionMap

class RewriteSetParser(object):
    # store instances by filename to avoid repeated parsing
    cache = {}

    def __init__(self, node, filename):
        rewriteSets = [RewriteSet(x) for x in node.findall('rewriteSet')]
        self.rewriteSets = {obj.name : obj for obj in rewriteSets}
        self.filename = filename # for error messages only

    def getRewriteSet(self, name):
        try:
            return self.rewriteSets[name]
        except KeyError:
            raise PygcamException('RewriteSet "%s" not found in file "%s"' % (name, self.filename))

    @classmethod
    def parse(cls, filename=None):
        """
        Parse an XML file holding a list of query result rewrites.
        :param filename: (str) the name of the XML file to read, or, if
           None, the value of config variable GCAM.XmlSetsFile is used.
        :return: a RewriteSetParser instance
        """
        filename = filename or getParam('GCAM.RewriteSetsFile')

        obj = cls.cache.get(filename)
        if obj:
            return obj

        xmlFile = XMLFile(filename, schemaPath='etc/rewriteSets-schema.xsd')
        obj = cls(xmlFile.tree.getroot(), filename)
        cls.cache[filename] = obj
        return obj

    @classmethod
    def getRegionMap(cls, rewriteSetName, filename=None):
        """
        Lookup a RewriteSet in the given file (or in GCAM.RewriteSetsFile)
        and return it as dictionary.

        :param rewriteSetName: (str) the name of the set to look up.
        :param filename: (str or None) path to rewriteSets.xml file, or if
           None, the value of config variable GCAM.RewriteSetsFile is used.
        :return: (dict) a dictionary keyed by aggregate region names,
           with values being a list of standard GCAM region names comprising
           the aggregate.
        """
        rewriteParser = cls.parse()
        rewriteSet = rewriteParser.getRewriteSet(rewriteSetName)
        return rewriteSet.asRegionMap()
