"""
.. Support for generating land-protection scenarios described in an XML file.

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from __future__ import print_function
import copy
import os
import sys

from lxml import etree as ET

from .config import getParam
from .constants import UnmanagedLandClasses, GCAM_32_REGIONS
from .error import FileFormatError, CommandlineError, PygcamException
from .log import getLogger
from .utils import mkdirs, pathjoin, flatten, parse_version_info
from .XMLFile import XMLFile

_logger = getLogger(__name__)

Verbose = False

def pp(elt):
    print(ET.tostring(elt, pretty_print=True))

def _findChildren(node, tag, cls=None):
    """
    Find all the children beneath `node` with the given `tag`, and
    return an instance of the class `cls` representing that node.

    :param node: the node to find children from
    :param tag: the tag for the children to find
    :param cls: optional class to instantiate for each child. If
      not specified, the class is assumed to be named by the
      capitalized version of the tag, i.e., tag 'foo' implies class Foo.
      As a special case, if cls == str, a list of the text contents for
      the given tag is returned.
    :return: a list of elements of type 'cls' or the imputed class.
    """

    if not cls:
        className = tag[0].upper() + tag[1:]    # retains camelCase
        thisModule = sys.modules[__name__]
        cls = getattr(thisModule, className)

    nodes = node.findall(tag)
    if cls == str:
        children = map(lambda node: node.text, nodes)
    else:
        children = map(cls, nodes)

    return children


class LandProtection(object):
    """
    Stores the application's representation of the parsed XML file describing land
    protection scenarios.

    :param node: an ``lxml.etree.Element`` representing the top-level ``<landProtection>`` node
    """
    def __init__(self, node):
        self.groups    = _findChildren(node, 'group')
        self.scenarios = _findChildren(node, 'scenario')

    def getScenario(self, name):
        return Scenario.getScenario(name)

    def protectLandTree(self, tree, scenarioName):
        """
        Apply the protection scenario `scenarioName` to the parsed XML file `tree`.
        This interface is provided so WriteFuncs (which are passed an open XMLInputFile)
        can apply protection scenarios.

        :param tree: (lxml ElementTree) a tree for a parsed XML input file.
        :param scenarioName: (str) the name of the scenario to apply
        :return: none
        """
        _logger.info("Applying protection scenario %s", scenarioName)

        scenario = Scenario.getScenario(scenarioName)
        if not scenario:
            raise FileFormatError("Scenario '%s' was not found" % scenarioName)

        # Iterate over all definitions for this scenario, applying the protections
        # incrementally to the tree representing the XML file that was read in.
        for protReg in scenario.protRegDict.values():
            regions = [protReg.name]
            for prot in protReg.protections:
                createProtected(tree, prot.fraction, landClasses=prot.landClasses, regions=regions)

    # TBD: test this
    def protectLand(self, infile, outfile, scenarioName, backup=True, unprotectFirst=False):
        """
        Generate a copy of `infile` with land protected according to `scenarioName`,
        writing the output to `outfile`.

        :param infile: input file (should be one of the GCAM aglu-xml land files)
        :param outfile: the file to create which represents the desired land protection
        :param scenarioName: a scenario in the landProtection.xml file
        :param backup: if True, create a backup `outfile`, with a '~' appended to the name,
          before writing a new file.
        :param unprotectFirst: (bool) if True, make all land "unprotected" before protecting.
        :return: none
        """
        parser = ET.XMLParser(remove_blank_text=True)
        tree = ET.parse(infile, parser)

        # TBD: eliminate this for v5.0
        # Remove any existing land protection, if so requested
        if unprotectFirst:
            unProtectLand(tree, otherArable=True)

        self.protectLandTree(tree, scenarioName)

        if backup:
            try:
                # Ensure we're not clobbering reference files.
                backupFile = outfile + '~'
                os.rename(outfile, backupFile)
            except Exception as e:
                PygcamException('Failed to create backup file "%s": %s', backupFile, e)

        _logger.info("Writing '%s'...", outfile)
        tree.write(outfile, xml_declaration=True, pretty_print=True)


class Group(object):
    Instances = {}

    def __init__(self, node):
        self.regions = _findChildren(node, 'region', cls=str)
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

        # print(ET.tostring(group, pretty_print=True))
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
        self.protections = _findChildren(node, 'protection')

    def expandNames(self):
        names = []
        Group.expandNames(self.name, names)
        return names

class Protection(object):
    def __init__(self, node):
        self.fraction = float(node.find('fraction').text)
        self.landClasses = _findChildren(node, 'landClass', cls=str)

class Scenario(object):
    Instances = {}

    def __init__(self, node):
        self.name = node.get('name')
        self.protRegs = _findChildren(node, 'protectedRegion')
        self.Instances[self.name] = self
        self.protRegDict = protRegDict = {}       # allows regions to override groups

        for protReg in self.protRegs:
            _logger.debug("Defining protectedRegion '%s'", protReg.name)
            regions = protReg.expandNames()

            # print(protReg.name, ' => ', regions)
            for region in regions:
                regCopy = copy.copy(protReg)
                regCopy.name = region
                protRegDict[region] = regCopy

    @classmethod
    def getScenario(cls, name):
        return cls.Instances.get(name)

def _makeRegionXpath(regions):
    if not regions:
        return ""

    if isinstance(regions, (str, unicode)):
        regions = [regions]

    patterns = map(lambda s: "@name='%s'" % s, regions)
    regionPattern = ' or '.join(patterns)
    xpath = "//region[%s]" % regionPattern
    _logger.debug('regionXpath: ' + xpath)
    return xpath

def _makeLandClassXpath(landClasses, protected=False):
    if isinstance(landClasses, (str, unicode)):
        landClasses = [landClasses]

    prefix = 'Protected' if protected else ''
    patterns = map(lambda s: 'starts-with(@name, "%s%s")' % (prefix, s), landClasses)
    landPattern = ' or '.join(patterns)
    xpath = ".//UnmanagedLandLeaf[%s]" % landPattern
    _logger.debug('landClassXpath: ' + xpath)
    return xpath

def unProtectLand(tree, landClasses=None, otherArable=False, regions=None):
    """
    Restore the file to 0% land protection by adding the protected land back
    into its unprotected counterpart and deleting the protected elements.

    :param tree: a tree representing a parsed GCAM land_input XML file
    :param landClasses: a string or a list of strings, or None. If None, all
           standard unmanaged land classes are modified.
    :param otherArable: (bool) if True, land class 'OtherArableLand' is
        included in default land classes.
    :param regions: a string or a list of strings, or None. If None, all
           regions are modified.
    :return: None
    """
    regionXpath = _makeRegionXpath(regions) if regions else ''
    landRoots = tree.xpath(regionXpath + '//LandAllocatorRoot')

    if not landClasses:
        landClasses = UnmanagedLandClasses + (['OtherArableLand'] if otherArable else [])

    protectedXpath = _makeLandClassXpath(landClasses, protected=True)

    for landRoot in landRoots:
        protectedNodes = landRoot.xpath(protectedXpath)

        if len(protectedNodes) == 0:
            continue

        # Find matching not-protected node and add protected land back in
        for node in protectedNodes:
            name = node.get('name')
            unProtectedName = name[len("Protected"):]
            prefix = './/UnmanagedLandLeaf[@name="%s"]' % unProtectedName

            protectedAllocs = node.xpath(".//allocation|.//landAllocation")

            for alloc in protectedAllocs:
                year = alloc.get('year')
                xpath = prefix + '//%s[@year="%s"]' % (alloc.tag, year)
                unprotectedAlloc = landRoot.find(xpath)
                originalArea = float(unprotectedAlloc.text) + float(alloc.text)
                unprotectedAlloc.text = str(originalArea)

        # Remove all the protected nodes, restoring the file to its original state
        landNodes = landRoot.xpath('./LandNode[starts-with(@name, "Protected")]')
        for landNode in landNodes:
            parent = landNode.getparent()
            parent.remove(landNode)

def createProtected(tree, fraction, landClasses=None, otherArable=False,
                    regions=None, unprotectFirst=False):
    """
    Modify an lxml tree representing a GCAM input file to protect a `fraction`
    of `landClasses` in `regions`.

    :param tree: a tree representing a parsed GCAM land_input XML file
    :param fraction: the fraction of land in the given land classes to protect
    :param landClasses: a string or a list of strings, or None. If None, all
           standard unmanaged land classes are modified.
    :param otherArable: (bool) if True, land class 'OtherArableLand' is
        included in default land classes.
    :param regions: a string or a list of strings, or None. If None, all
           regions are modified.
    :param unprotectFirst: (bool) if True, make all land "unprotected" before
           protecting.
    :return: None
    """
    version = parse_version_info()
    if version >= (5, 0):
        raise PygcamException("Called landProtection.createProtected on GCAM version >= 5.0. Use landProtectionUpdate.protectLand instead.")

    _logger.debug('createProtected: fraction=%.2f, landClasses=%s, regions=%s, unprotect=%s',
                  fraction, landClasses, regions, unprotectFirst)

    def multiplyValues(nodes, factor):
        for n in nodes:
            newValue = float(n.text) * factor
            n.text = str(newValue)

    # Remove any existing land protection, if so requested
    if unprotectFirst:
        unProtectLand(tree, landClasses=landClasses, otherArable=otherArable, regions=regions)

    regionXpath = (_makeRegionXpath(regions) if regions else '') + '//LandAllocatorRoot'
    landRoots = tree.xpath(regionXpath)

    if not landClasses:
        landClasses = UnmanagedLandClasses + (['OtherArableLand'] if otherArable else [])

    unmgdXpath     = _makeLandClassXpath(landClasses)
    protectedXpath = _makeLandClassXpath(landClasses, protected=True)

    allocXpath = ".//allocation|.//landAllocation"

    for landRoot in landRoots:
        # ensure that we're not protecting an already-protected land class in these regions
        nodes = landRoot.xpath(protectedXpath)
        if len(nodes) > 0:
            node = nodes[0]
            regNodes = list(node.iterancestors(tag='region'))
            region = regNodes[0].get('name')
            raise FileFormatError('Error: Land class %s is already protected in region %s' % (node.tag, region))

        nodes = landRoot.xpath(unmgdXpath)

        for node in nodes:
            landnode = ET.SubElement(landRoot, 'LandNode')

            new = copy.deepcopy(node)
            newName = 'Protected' + node.get('name')
            new.set('name', newName)
            landnode.set('name', newName)
            landnode.set('fraction', "%.4f" %fraction)
            landnode.append(new)

            originalAreas = node.xpath(allocXpath)
            protectedAreas = new.xpath(allocXpath)

            multiplyValues(originalAreas, 1 - fraction)
            multiplyValues(protectedAreas, fraction)

def protectLand(infile, outfile, fraction, landClasses=None, otherArable=False,
                regions=None, unprotectFirst=False):
    """
    Create a copy of `infile` that protects a `fraction` of `landClasses` in `regions`.

    :param infile: the path of a GCAM land_input XML file
    :param outfile: the path of the XML file to create by modifying data from `infile`
    :param fraction: the fraction of land in the given land classes to protect
    :param landClasses: a string or a list of strings, or None. If None, all
        "standard" unmanaged land classes are modified.
    :param otherArable: (bool) if True, land class 'OtherArableLand' is
        included in default land classes.
    :param regions: a string or a list of strings, or None. If None, all
        regions are modified.
    :param unprotectFirst: (bool) if True, make all land "unprotected" before
        protecting.
    :return: None
    """
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(infile, parser)

    createProtected(tree, fraction, landClasses=landClasses, otherArable=otherArable,
                    regions=regions, unprotectFirst=unprotectFirst)
    tree.write(outfile, xml_declaration=True, pretty_print=True)

_LandXmlFiles = ['land2.xml', 'land3.xml']

def _landXmlPaths(workspace, landXmlFiles=_LandXmlFiles):
    xmlDir = pathjoin(workspace, 'input', 'gcam-data-system', 'xml', 'aglu-xml')
    paths = map(lambda filename: pathjoin(xmlDir, filename), landXmlFiles)
    return paths

def parseLandProtectionFile(scenarioFile=None):
    scenarioFile = scenarioFile or getParam('GCAM.LandProtectionXmlFile')
    xmlFile = XMLFile(scenarioFile, schemaPath='etc/protection-schema.xsd')
    obj = LandProtection(xmlFile.getRoot())
    return obj

def runProtectionScenario(scenarioName, outputDir=None, workspace=None,
                          scenarioFile=None, xmlFiles=None, inPlace=False,
                          unprotectFirst=False):
    """
    Run the protection named by `scenarioName`, found in `scenarioFile` if given,
    or the value of config variable `GCAM.LandProtectionXmlFile` otherwise. The source
    files are take from `workspace`, if given, otherwise from the value of `GCAM.RefWorkspace`.
    Results are written to the given `outputDir`. In the even that the input and output
    files are the same, `inPlace` must be set to True to indicate that overwriting is intended.
    By default the two files `xmlFiles`, land2.xml and land3.xml in the aglu-xml directory,
    are processed, though other files can be specified in the unlikely case that you have
    alternatives.

    :param scenarioName: (str) the name of a protection scenario defined in the `scenarioFile`
    :param outputDir: (str) the directory under which to write the modified land files. Ignored
       if inPlace=True.
    :param workspace: (str) the location of the workspace holding the input files (ignored
       if xmlFiles are specified explicitly)
    :param scenarioFile: (str) the path to a protection.xml file defining `scenarioName`
    :param xmlFiles: (list of str) the paths of the XML input files to modify
    :param inPlace: (bool) if True, input and output files may be the same (output overwrites input).
    :param unprotectFirst: (bool) if True, make all land "unprotected" before
           protecting.
    :return: none
    """
    _logger.debug("Land-protection scenario '%s'", scenarioName)

    landProtection = parseLandProtectionFile(scenarioFile=scenarioFile)

    workspace = workspace or getParam('GCAM.SandboxRefWorkspace')
    xmlFiles = xmlFiles or _landXmlPaths(workspace)

    for inFile in xmlFiles:
        basename = os.path.basename(inFile)
        outFile = inFile if inPlace else pathjoin(outputDir, basename)

        # check that we're not clobbering the input file
        if not inPlace and os.path.lexists(outFile) and os.path.samefile(inFile, outFile):
            raise CommandlineError("Attempted to overwrite '%s' but --inPlace was not specified." % inFile)

        landProtection.protectLand(inFile, outFile, scenarioName, unprotectFirst=unprotectFirst)

def protectLandMain(args):

    global Verbose
    Verbose = args.verbose
    regions      = args.regions and flatten(map(lambda s: s.split(','), args.regions))
    scenarioFile = args.scenarioFile or getParam('GCAM.LandProtectionXmlFile')
    scenarioName = args.scenario
    outDir    = args.outDir
    workspace = args.workspace or getParam('GCAM.RefWorkspace')
    template  = args.template

    if not workspace:
        raise CommandlineError('Workspace must be identified in command-line or config variable GCAM.RefWorkspace')

    if args.mkdir:
        mkdirs(outDir)

    xmlFiles = _landXmlPaths(workspace)

    # Process instructions from protection XML file
    if scenarioName:
        if not scenarioFile:
            raise CommandlineError('Scenario "%s" was specified, but a scenario file was not identified',
                                   scenarioName)
        runProtectionScenario(scenarioName, outDir, workspace=workspace,
                              scenarioFile=scenarioFile, xmlFiles=xmlFiles, inPlace=args.inPlace)
        return

    # If no scenario name given, process command-line args
    fraction = args.fraction
    if fraction is None:
        raise CommandlineError('If not using protection scenarios, fraction must be provided')

    landClasses = flatten(map(lambda s: s.split(','), args.landClasses)) if args.landClasses \
                    else UnmanagedLandClasses + (['OtherArableLand'] if args.otherArable else [])

    fraction = float(fraction)
    templateDict = {'fraction' : str(int(fraction * 100)),
                    'regions'  : '-'.join(regions) if regions else 'global',
                    'classes'  : '-'.join(landClasses) if args.landClasses else 'unmanaged'}

    for path in xmlFiles:
        filename = os.path.basename(path)
        templateDict['filename'] = filename
        templateDict['basename'] = os.path.splitext(filename)[0]

        outFile = template.format(**templateDict)
        outPath = pathjoin(outDir, outFile)
        _logger.debug("protectLand(%s, %s, %0.2f, %s, %s)", path, outFile, fraction, landClasses, regions)
        protectLand(path, outPath, fraction, landClasses=landClasses, regions=regions)
