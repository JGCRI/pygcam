'''
Created on 12/12/15
@author: Richard Plevin

Copyright (c) 2015 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.
'''
import sys
import os
from lxml import etree as ET
import copy
from .common import GCAM_32_REGIONS

ThisModule = sys.modules[__name__]

AllUnmanagedLand = ['UnmanagedPasture', 'UnmanagedForest', 'Shrubland', 'Grassland']


def _makeRegionXpath(regions):
    if not regions:
        return ""

    if isinstance(regions, (str, unicode)):
        regions = [regions]

    patterns = map(lambda s: "@name='%s'" % s, regions)
    regionPattern = ' or '.join(patterns)
    xpath = "//region[%s]" % regionPattern
    # print xpath
    return xpath

def _makeLandClassXpath(landClasses, protected=False):
    if isinstance(landClasses, (str, unicode)):
        landClasses = [landClasses]

    prefix = 'Protected' if protected else ''
    patterns = map(lambda s: "starts-with(@name, '%s%s')" % (prefix, s), landClasses)
    landPattern = ' or '.join(patterns)
    xpath = ".//UnmanagedLandLeaf[%s]" % landPattern
    # print xpath
    return xpath

def findChildren(node, tag, cls=None):
    '''
    :param node: the node to find children from
    :param tag: the tag for the children to find
    :param cls: optional class to instantiate for each child. If
    not specified, the class is assumed to be named by the
    capitalized version of the tag, i.e., tag 'foo' implies class Foo.
    As a special case, if cls == str, a list of the text contents for
    the given tag is returned.
    :return: a list of elements of type 'cls' or the imputed class.
    '''
    if not cls:
        className = tag[0].upper() + tag[1:]    # retains camelCase
        cls = getattr(ThisModule, className)

    nodes = node.findall(tag)
    if cls == str:
        children = map(lambda node: node.text, nodes)
    else:
        children = map(cls, nodes)

    return children

class XMLFile(object):
    # TBD: move to common once debugged; use it in project.py as well.

    def __init__(self, xmlFile, schemaFile=None, raiseError=True, rootClass=None):
        parser = ET.XMLParser(remove_blank_text=True)
        self.tree = ET.parse(xmlFile, parser)

        if not schemaFile:
            return

        schemaDoc = ET.parse(schemaFile)
        schema = ET.XMLSchema(schemaDoc)

        if raiseError:
            try:
                schema.assertValid(self.tree)
            except ET.DocumentInvalid as e:
                raise Exception("Validation of '%s'\n  using schema '%s' failed:\n  %s" % (xmlFile, schemaFile, e))
        else:
            return schema.validate(self.tree)

        self.root = rootClass(self.tree)

    def getRoot(self):
        return self.root

class LandProtection(object):
    def __init__(self, node):
        self.groups    = findChildren(node, 'group')
        self.scenarios = findChildren(node, 'scenario')

    def getScenario(self, name):
        return Scenario.getScenario(name)

    def protectLand(self, infile, outfile, scenarioName, backup=True):
        parser = ET.XMLParser(remove_blank_text=True)
        tree = ET.parse(infile, parser)

        scenario = Scenario.getScenario(scenarioName)
        if not scenario:
            raise Exception("Scenario '%s' was not found" % scenarioName)

        # Iterate over all definitions for this scenario, applying the protections
        # incrementally to the tree representing the XML file that was read in.
        for protReg in scenario.protRegDict.values():
            regions = [protReg.name]
            for prot in protReg.protections:
                createProtected(tree, prot.fraction, landClasses=prot.landClasses, regions=regions)

        if backup:
            try:
                # This is mainly for testing to ensure we're not clobbering reference files. Ignore errors.
                os.rename(outfile, outfile + '~')
            except:
                pass

        print "Writing '%s'..." % outfile,
        tree.write(outfile, xml_declaration=True, pretty_print=True)
        print 'done.'


    @staticmethod
    def validateXML(doc, raiseError=True):
        '''
        Validate a parsed project.xml file
        '''
        schemaFile = os.path.join(os.path.dirname(__file__), 'etc', 'protection-schema.xsd')
        schemaDoc = ET.parse(schemaFile)
        schema = ET.XMLSchema(schemaDoc)

        if raiseError:
            schema.assertValid(doc)
        else:
            return schema.validate(doc)

class Group(object):
    Instances = {}

    def __init__(self, node):
        self.regions = findChildren(node, 'region', cls=str)
        self.Instances[node.get('name')] = self

    @classmethod
    def globalGroup(cls):
        '''
        Generate built-in 'global' region
        '''
        group = ET.Element('group', name='Global')
        for name in GCAM_32_REGIONS:
            reg = ET.SubElement(group, 'region')
            reg.text = name

        # print ET.tostring(group, pretty_print=True)
        return cls(group)

    @classmethod
    def getGroup(cls, name):
        group = cls.Instances.get(name)

        if not group and name.lower() == 'global':
            group = cls.globalGroup()

        return group

    @classmethod
    def regionNames(cls, groupName):
        group = cls.getGroup(groupName)
        return map(lambda region: region.name, group.regions)

    @staticmethod
    def expandNames(name, names):
        '''
        Recursively expand a list of region/group names into a list of actual region names.
        This is generally not called directly; it is called from ProtectedRegion, which is
        where the expansion is required.

        :param name: the name of the initial region/group to expand
        :param names: a list which holds the accumulated region names
        :return: nothing -- the result is in the list `names` passed by the user.
        '''
        group = Group.getGroup(name)
        if not group:
            names.append(name)
        else:
            for region in group.regions:
                Group.expandNames(region, names)

class ProtectedRegion(object):
    def __init__(self, node):
        self.name = node.get('name')
        self.protections = findChildren(node, 'protection')

    def expandNames(self):
        names = []
        Group.expandNames(self.name, names)
        return names

class Scenario(object):
    Instances = {}

    def __init__(self, node):
        self.name = node.get('name')
        self.protRegs = findChildren(node, 'protectedRegion')
        self.Instances[self.name] = self
        self.protRegDict = protRegDict = {}       # allows regions to override groups

        for protReg in self.protRegs:
            # print "Processing protectedRegion '%s'" % protReg.name
            regions = protReg.expandNames()

            # print protReg.name, ' => ', regions
            for region in regions:
                regCopy = copy.copy(protReg)
                regCopy.name = region
                protRegDict[region] = regCopy

    @classmethod
    def getScenario(cls, name):
        return cls.Instances.get(name)

class Protection(object):
    def __init__(self, node):
        self.landClasses = findChildren(node, 'landClass', cls=str)
        self.fraction = float(node.get('fraction'))

def createProtected(tree, fraction, landClasses=AllUnmanagedLand, regions=None):
    """
    Modify an lxml tree representing a GCAM input file to protect a `fraction`
    of `landClasses` in `regions`.

    :param tree: a tree representing a parsed GCAM land_input XML file
    :param fraction: the fraction of land in the given land classes to protect
    :param landClasses: a string or a list of strings, or None. If None, all
           unmanaged land classes are modified.
    :param regions: a string or a list of strings, or None. If None, all
           regions are modified.
    :return: None
    """
    def multiplyValues(nodes, factor):
        for n in nodes:
            newValue = float(n.text) * factor
            n.text = str(newValue)

    # print 'CreateProtected regions:', regions
    regionXpath = _makeRegionXpath(regions) if regions else ''
    landRoots = tree.xpath(regionXpath + '//LandAllocatorRoot')

    unmgdXpath     = _makeLandClassXpath(landClasses)
    protectedXpath = _makeLandClassXpath(landClasses, protected=True)

    for landRoot in landRoots:
        # ensure that we're not protecting an already-protected land class in these regions
        nodes = landRoot.xpath(protectedXpath)
        if len(nodes) > 0:
            node = nodes[0]
            regNodes = list(node.iterancestors(tag='region'))
            region = regNodes[0].get('name')
            raise Exception('Error: Land class %s is already protected in region %s' % (node.tag, region))

        nodes = landRoot.xpath(unmgdXpath)

        for node in nodes:
            landnode = ET.SubElement(landRoot, 'LandNode')
            new = copy.deepcopy(node)
            newName = 'Protected' + node.get('name')
            new.set('name', newName)
            landnode.set('name', newName)
            landnode.set('fraction', str(fraction))
            landnode.append(new)

            allocXpath = ".//allocation|.//landAllocation"
            originalAreas = node.xpath(allocXpath)
            protectedAreas = new.xpath(allocXpath)

            multiplyValues(originalAreas, 1 - fraction)
            multiplyValues(protectedAreas, fraction)

def protectLand(infile, outfile, fraction, landClasses=AllUnmanagedLand, regions=None):
    """
    Create a copy of `infile` that protects a `fraction` of `landClasses` in `regions`.

    :param infile: the path of a GCAM land_input XML file
    :param outfile: the path of the XML file to create by modifying data from `infile`
    :param fraction: the fraction of land in the given land classes to protect
    :param landClasses: a string or a list of strings, or None. If None, all
           unmanaged land classes are modified.
    :param regions: a string or a list of strings, or None. If None, all
           regions are modified.
    :return: None
    """
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(infile, parser)

    createProtected(tree, fraction, landClasses=landClasses, regions=regions)
    tree.write(outfile, xml_declaration=True, pretty_print=True)
