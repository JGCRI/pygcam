'''
Created on 12/12/15
@author: Richard Plevin

Copyright (c) 2015 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.
'''
from lxml import etree as ET
import copy

AllUnmanagedLand = ['UnmanagedPasture', 'UnmanagedForest', 'Shrubland', 'Grassland']

def _makeRegionXpath(regions):
    if not regions:
        return ""

    if isinstance(regions, (str, unicode)):
        regions = [regions]

    patterns = map(lambda s: "@name='%s'" % s, regions)
    regionPattern = ' or '.join(patterns)
    xpath = "//region[%s]" % regionPattern
    return xpath

def _makeLandClassXpath(landClasses, protected=False):
    if isinstance(landClasses, (str, unicode)):
        landClasses = [landClasses]

    prefix = 'Protected' if protected else ''
    patterns = map(lambda s: "starts-with(@name, '%s%s')" % (prefix, s), landClasses)
    landPattern = ' or '.join(patterns)
    xpath = ".//UnmanagedLandLeaf[%s]" % landPattern
    return xpath

def createProtected(tree, fraction, landClasses=AllUnmanagedLand, regions=None):
    """
    Modify an lxml tree to protect a `fraction` of `landCovers` in `regions`.

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
