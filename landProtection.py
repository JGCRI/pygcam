'''
@author: Richard Plevin

Copyright (c) 2014. The Regents of the University of California (Regents).
See the file COPYRIGHT.txt for details.
'''
from lxml import etree as ET
import copy

def makeRegionXpath(regions):
    if regions and isinstance(regions, (str, unicode)):
        regions = [regions]

    patterns = map(lambda s: "@name='%s'" % s, regions)
    regionPattern = ' or '.join(patterns)
    xpath = "//region[%s]" % regionPattern
    return xpath

def makeLandCoverXpath(landCovers):
    if isinstance(landCovers, (str, unicode)):
        landCovers = [landCovers]

    patterns = map(lambda s: "starts-with(@name, '%s')" % s, landCovers)
    landPattern = ' or '.join(patterns)
    xpath = ".//UnmanagedLandLeaf[%s]" % landPattern
    return xpath


AllUnmanagedLand = ['UnmanagedPasture', 'UnmanagedForest', 'Shrubland', 'Grassland']

def createProtected(tree, fraction, landCovers=AllUnmanagedLand, regions=None):
    # landCover can be a string or a list of strings, or None. If None, all
    # unmanaged land cover types are modified. Regions can be a string or a
    # list of strings, or None. If None, all regions are modified.

    def multiplyValues(nodes, factor):
        for n in nodes:
            newValue = float(n.text) * factor
            n.text = str(newValue)

    regionXpath = makeRegionXpath(regions) if regions else ''
    landRoots = tree.xpath(regionXpath + '//LandAllocatorRoot')

    unmgdXpath = makeLandCoverXpath(landCovers)

    for landRoot in landRoots:
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

            multiplyValues(originalAreas, 1 - protFrac)
            multiplyValues(protectedAreas, protFrac)


if __name__ == '__main__':
    filename='/tmp/land_input_3.xml'
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(filename, parser)

    protFrac = 0.9
    covers = ['UnmanagedPasture', 'UnmanagedForest', 'Shrubland']
    regions = ['Africa_Eastern', 'USA']

    createProtected(tree, protFrac, landCovers=covers, regions=regions)
    tree.write('/tmp/mod3.xml', xml_declaration=True, pretty_print=True)
