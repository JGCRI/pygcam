"""
.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.

   Support for running a sequence of operations for a GCAM project
   that is described in an XML file.
"""
import sys
import os
from lxml import etree as ET
import copy
import platform
import argparse

from .common import GCAM_32_REGIONS, mkdirs, ToolException, flatten
from .config import readConfigFiles, getParam

ThisModule = sys.modules[__name__]

UnmanagedLandClasses = ['UnmanagedPasture', 'UnmanagedForest', 'Shrubland', 'Grassland']

PROGRAM = 'protectLand.py'
VERSION = '0.1'
Verbose = False

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
        cls = getattr(ThisModule, className)

    nodes = node.findall(tag)
    if cls == str:
        children = map(lambda node: node.text, nodes)
    else:
        children = map(cls, nodes)

    return children

# TBD: move to common once debugged; use it in project.py as well.
class XMLFile(object):
    """
    Represents an XML file, which is parsed by lxml.etree and stored internally.

    :param xmlFile: pathname of the XML file
    :param schemaFile: optional XMLSchema file to use for validation
    :param raiseError: if True, raise an error if validation fails
    :param rootClass: optional root class, which is instantiated for the parsed
      tree and stored internally
    """
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
                raise ToolException("Validation of '%s'\n  using schema '%s' failed:\n  %s" % (xmlFile, schemaFile, e))
        else:
            return schema.validate(self.tree)

        self.root = rootClass(self.tree)

    def getRoot(self):
        return self.root

class LandProtection(object):
    """
    Stores the application's representation of the parsed XML file describing land
    protection scenarios.

    :param node: an lxml.etree.Element representing the top-level ``<landProtection>`` node
    """
    def __init__(self, node):
        self.groups    = findChildren(node, 'group')
        self.scenarios = findChildren(node, 'scenario')

    def getScenario(self, name):
        return Scenario.getScenario(name)

    def protectLand(self, infile, outfile, scenarioName, backup=True):
        """
        Generate a copy of `infile` with land protected according to `scenarioName`,
        writing the output to `outfile`.

        :param infile: input file (should be one of the GCAM aglu-xml land files)
        :param outfile: the file to create which represents the desired land protection
        :param scenarioName: a scenario in the landProtection.xml file
        :param backup: if True, create a backup `outfile`, with a '~' appended to the name,
          before writing a new file.
        :return: none
        """
        parser = ET.XMLParser(remove_blank_text=True)
        tree = ET.parse(infile, parser)

        scenario = Scenario.getScenario(scenarioName)
        if not scenario:
            raise ToolException("Scenario '%s' was not found" % scenarioName)

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

    # @staticmethod
    # def validateXML(doc, raiseError=True):
    #     '''
    #     Validate a parsed project.xml file
    #     '''
    #     schemaFile = os.path.join(os.path.dirname(__file__), 'pygcam', 'etc', 'protection-schema.xsd')
    #     schemaDoc = ET.parse(schemaFile)
    #     schema = ET.XMLSchema(schemaDoc)
    #
    #     if raiseError:
    #         schema.assertValid(doc)
    #     else:
    #         return schema.validate(doc)

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

def createProtected(tree, fraction, landClasses=UnmanagedLandClasses, regions=None):
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
            raise ToolException('Error: Land class %s is already protected in region %s' % (node.tag, region))

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

def protectLand(infile, outfile, fraction, landClasses=UnmanagedLandClasses, regions=None):
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

DefaultTemplate = 'prot_{fraction}_{filename}'

def argParser():
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description='''Generate versions of GCAM's land_input XML files that protect a
given fraction of land of the given land types in the given regions. The script can be
run multiple times on the same file to apply different percentage protection to
distinct regions or land classes. The script detects if you attempt to protect
already-protected land class and region combinations, as this fails in GCAM.''')

    parser.add_argument('-b', '--backup', action='store_true',
                        help='''Make a copy of the output file, if it exists (with an added ~ after
                        filename) before writing new output.''')

    parser.add_argument('-f', '--fraction', type=float, default=None,
                        help='''The fraction of land in the given land classes to protect. (Required)''')

    parser.add_argument('-i', '--inFile', action='append',
                        help='''One or more input files to process. Use separate -i flags for each file.''')

    parser.add_argument('--inPlace', action='store_true',
                        help='''Edit the file in place. This must be given explicitly, to avoid overwriting
                        files by mistake.''')

    parser.add_argument('-l', '--landClasses', action='append',
                        help='''The land class or classes to protect in the given regions. Multiple,
                        comma-delimited land types can be given in a single argument, or the -l flag can
                        be repeated to indicate additional land classes. By default, all unmanaged land
                        classes are protected. Allowed land classes are %s''' % UnmanagedLandClasses)

    parser.add_argument('-m', '--mkdir', action='store_true',
                        help='''Make the output dir if necessary.''')

    parser.add_argument('-o', '--outDir', type=str, default='.',
                        help='''The directory into which to write the modified files. Default is current directory.''')

    parser.add_argument('-t', '--template', type=str, default=DefaultTemplate,
                        help='''Specify a template to use for output filenames. The keywords {fraction}, {filename},
                        {regions}, and {classes} (with surrounding curly braces) are replaced by the following values
                        and used to form the name of the output files, written to the given output directory.
                        fraction: 100 times the given fraction (i.e., int(fraction * 100));
                        filename: the name of the input file being processed (e.g., land_input_2.xml or land_input_3.xml);
                        basename: the portion of the input filename prior to the extension (i.e., before '.xml');
                        regions: the given regions, separated by '-', or the word 'global' if no regions are specified;
                        classes: the given land classes, separated by '-', or the word 'unmanaged' if no land classes
                        are specified. The default pattern is "%s".''' % DefaultTemplate)

    parser.add_argument('-r', '--regions', action='append',
                        help='''The region or regions for which to protect land. Multiple, comma-delimited
                        regions can be given in a single argument, or the -r flag can be repeated to indicate
                        additional regions. By default, all regions are protected.''')

    parser.add_argument('-s', '--scenario', default=None,
                        help='''The name of a land-protection scenario defined in the file given by the --scenarioFile
                        argument or it's default value.''')

    parser.add_argument('-S', '--scenarioFile', default=None,
                        help='''An XML file defining land-protection scenarios. Default is the value
                        of configuration file parameter GCAM.LandProtectionXmlFile.''')

    parser.add_argument('-v', '--verbose', action='store_true', help='''Show diagnostic output''')

    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + VERSION)

    parser.add_argument('-w', '--workspace', type=str, default=None,
                        help='''Specify the path to the GCAM workspace to use. If input files are not identified
                        explicitly, the files in {workspace}/input/gcam-data-system/xml/aglu-xml/land_input_{2,3}.xml
                        are used as inputs. Default is value of configuration parameter GCAM.ReferenceWorkspace.''')

    return parser

def parseArgs(args=None):
    """
    Allows calling the arg parser programatically.
    :param args: The parameter list to parse.
    :return: populated Namespace instance
    """
    parser = argParser()
    args = parser.parse_args(args=args)
    return args


def main(args):
    readConfigFiles()

    global Verbose
    Verbose = args.verbose
    landClasses  = flatten(map(lambda s: s.split(','), args.landClasses)) if args.landClasses else UnmanagedLandClasses
    regions      = args.regions and flatten(map(lambda s: s.split(','), args.regions))
    scenarioFile = args.scenarioFile or getParam('GCAM.LandProtectionXmlFile')
    scenarioName = args.scenario
    outDir    = args.outDir
    inFiles   = args.inFile
    workspace = args.workspace or getParam('GCAM.ReferenceWorkspace')
    template  = args.template
    inPlace   = args.inPlace
    backup    = args.backup

    if not inFiles and not workspace:
        raise ToolException('Must specify either inFiles or workspace')

    if workspace:
        if inFiles:
            print "Workspace is defined; ignoring inFiles"

        # compute equivalent 'inFiles' arguments for loop below
        filenames = ['land_input_2.xml', 'land_input_3.xml']
        xmlDir = os.path.join(workspace, 'input', 'gcam-data-system', 'xml', 'aglu-xml')
        inFiles = map(lambda filename: os.path.join(xmlDir, filename), filenames)

    if args.mkdir:
        mkdirs(outDir)

    if scenarioName:
        if not scenarioFile:
            raise ToolException('A scenario file was not identified')

        print "Land-protection scenario '%s'" % scenarioName

        schemaFile = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'pygcam', 'etc', 'protection-schema.xsd')
        xmlFile = XMLFile(scenarioFile, schemaFile=schemaFile, rootClass=LandProtection)
        landProtection = xmlFile.getRoot()
        for inFile in inFiles:
            basename = os.path.basename(inFile)
            outFile  = os.path.join(outDir, basename)

            # check that we're not clobbering the input file
            if not inPlace and os.path.lexists(outFile) and os.path.samefile(inFile, outFile):
                raise ToolException("Attempted to overwrite '%s' but --inPlace was not specified." % inFile)

            landProtection.protectLand(inFile, outFile, scenarioName, backup=backup)

        return

    fraction = args.fraction
    if fraction is None:
        raise ToolException('If not using protection scenarios, fraction must be provided')

    fraction = float(fraction)
    templateDict = {'fraction' : str(int(fraction * 100)),
                    'regions'  : '-'.join(regions) if regions else 'global',
                    'classes'  : '-'.join(landClasses) if args.landClasses else 'unmanaged'}

    for path in inFiles:
        filename = os.path.basename(path)
        templateDict['filename'] = filename
        templateDict['basename'] = os.path.splitext(filename)[0]

        outFile = template.format(**templateDict)
        outPath = os.path.join(outDir, outFile)
        if Verbose:
            print "protectLand(%s, %s, %0.2f, %s, %s)" % (path, outFile, fraction, landClasses, regions)
        protectLand(path, outPath, fraction, landClasses=landClasses, regions=regions) #, template=template)
