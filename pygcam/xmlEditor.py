'''
.. Copyright (c) 2016 Richard Plevin

   See the https://opensource.org/licenses/MIT for license details.
'''
#
#  Facilities setting up / customizing GCAM project's XML files.
#
# Common variables and functions for manipulating XML files.
# Basic approach is to create a directory for each defined scenario,
# in which modified files and a corresponding configuration XML file
# are stored.
#
# To allow functions to be called in any order or combination, each
# copies (if needed) the source file to the local scenario dir, then
# edits it in place. If was previously modified by another function,
# the copy is skipped, and the new edits are applied to the local,
# already modified file. Each function updates the local config file
# to refer to the modified file. (This may be done multiple times, to
# no ill effect.)
#
import glob
import os
import re
import shutil
import six
from lxml import etree as ET
from semver import VersionInfo

from .config import getParam, getParamAsBoolean, parse_version_info, unixPath, pathjoin
from .constants import LOCAL_XML_NAME, DYN_XML_NAME, GCAM_32_REGIONS
from .error import SetupException, PygcamException
from .log import getLogger
from .policy import (policyMarketXml, policyConstraintsXml, DEFAULT_MARKET_TYPE,
                     DEFAULT_POLICY_ELT, DEFAULT_POLICY_TYPE)
from .utils import (coercible, mkdirs, printSeries, symlinkOrCopyFile, removeTreeSafely)

# Names of key scenario components in reference GCAM 4.3 configuration.xml file
ENERGY_TRANSFORMATION_TAG = "energy_transformation"
SOLVER_TAG = "solver"

AttributePattern = re.compile('(.*)/@([-\w]*)$')
XmlDirPattern    = re.compile('/[^/]*-xml/')

_logger = getLogger(__name__)

# methods callable from <function name="x">args</function> in
# XML scenario setup scripts.
CallableMethods = {}

# decorator it identify callable methods
def callableMethod(func):
    CallableMethods[func.__name__] = func
    return func

def getCallableMethod(name):
    return CallableMethods.get(name)

def makeDirPath(elements, require=False, create=False, mode=0o775):
    """
    Join the tuple of elements to create a path to a directory,
    optionally checking that it exists or creating intermediate
    directories as needed.

    :param elements: a tuple of pathname elements to join
    :param require: if True, raise an error if the path doesn't exist
    :param create: if True, create the path if it doesn't exist
    :param mode: file mode used when making directories
    :return: the joined path
    :raises: pygcam.error.SetupException
    """
    path = pathjoin(*elements)

    if (create or require) and not os.path.lexists(path):
        if create:
            os.makedirs(path, mode)
        elif require:
            raise SetupException("Required path '%s' does not exist." % path)

    return path

#
# Copy src file to dst only if it doesn't already exist.
#
def copyIfMissing(src, dst, makedirs=False):
    """
    Copy file `src` to `dst`, but only if `dst` doesn't already exist.

    :param src: (str) pathname of the file to copy
    :param dst: (str) pathname of the copy to create
    :param makedirs: if True, make any missing directories
    :return: none
    """
    if not os.path.lexists(dst):
        parentDir = os.path.dirname(dst)
        if makedirs and not os.path.isdir(parentDir):
            _logger.debug("mkdir %s" % parentDir)
            os.makedirs(parentDir, 0o755)

        _logger.info("Copy %s\n      to %s" % (src, dst))
        shutil.copy(src, dst)
        os.chmod(dst, 0o644)

class CachedFile(object):
    parser = ET.XMLParser(remove_blank_text=True)

    # Store parsed XML trees here and use with xmlSel/xmlEdit if useCache is True
    cache = {}

    def __init__(self, filename):
        self.filename = filename
        self.edited = False

        _logger.debug("Reading '%s'", filename)
        self.tree = ET.parse(filename, self.parser)
        self.cache[filename] = self

    @classmethod
    def getFile(cls, filename):
        if filename in cls.cache:
            #_logger.debug("Found '%s' in cache", filename)
            item = cls.cache[filename]
        else:
            item = CachedFile(filename)

        return item

    def setEdited(self):
        self.edited = True

    def write(self):
        _logger.info("Writing '%s'", self.filename)
        self.tree.write(self.filename, xml_declaration=True, encoding='utf-8', pretty_print=True)
        self.edited = False

    def decache(self):
        if self.edited:
            self.write()

    @classmethod
    def decacheAll(cls):
        for item in cls.cache.values():
            item.decache()


def xmlSel(filename, xpath, asText=False):
    """
    Return True if the XML component identified by the xpath argument
    exists in `filename`. Useful for deciding whether to edit or
    insert an XML element.

    :param filename: (str) the file to edit
    :param xpath: (str) the xml element(s) to search for
    :param asText: (str) if True, return the text of the node, if found, else None
    :return: (bool) True if found, False otherwise. (see asText)
    """
    item = CachedFile.getFile(filename)
    result = item.tree.find(xpath)

    if asText:
        return result.text if result is not None else None

    return bool(result)

#
# xmlEdit can set a value, multiply a value in the XML by a constant,
# or add a constant to the value in the XML. These funcs handle each
# operation, allowing the logic to be outside the loop, which might
# iterate over thousands of elements.
#
def _set(elt, value):
    elt.text = str(value)

def _multiply(elt, value):
    elt.text = str(float(elt.text) * value)

def _add(elt, value):
    elt.text = str(float(elt.text) + value)

_editFunc = {'set'      : _set,
             'multiply' : _multiply,
             'add'      : _add}

def xmlEdit(filename, pairs, op='set', useCache=True):
    """
    Edit the XML file `filename` in place, applying the values to the given xpaths
    in the list of pairs.

    :param filename: the file to edit in-place.
    :param pairs: (iterable of (xpath, value) pairs) In each pair, the xpath selects
      elements or attributes to update with the given values.
    :param op: (str) Operation to perform. Must be in ('set', 'multiply', 'add').
      Note that 'multiply' and 'add' are *not* available for xpaths selecting
      attributes rather than node values. For 'multiply'  and 'add', the value
      should be passed as a float. For 'set', it can be a float or a string.
    :param useCache: (bool) if True, the etree is sought first in the XmlCache. This
      avoids repeated parsing, but the file is always written (eventually) if updated
      by this function.
    :return: True on success, else False
    """
    legalOps = _editFunc.keys()

    if op not in legalOps:
        raise PygcamException('xmlEdit: unknown operation "{}". Must be one of {}'.format(op, legalOps))

    modFunc = _editFunc[op]

    item = CachedFile.getFile(filename)
    tree = item.tree

    updated = False

    # if at least one xpath is found, update and write file
    for xpath, value in pairs:
        attr = None

        # If it's an attribute update, extract the attribute
        # and use the rest of the xpath to select the elements.
        match = re.match(AttributePattern, xpath)
        if match:
            attr = match.group(2)
            xpath = match.group(1)

        elts = tree.xpath(xpath)
        if len(elts):
            updated = True
            if attr:                # conditional outside loop since there may be many elements
                value = str(value)
                for elt in elts:
                    elt.set(attr, value)
            else:
                for elt in elts:
                    modFunc(elt, value)

    if updated:
        if useCache:
            item.setEdited()
        else:
            item.write()

    return updated

def extractStubTechnology(region, srcFile, dstFile, sector, subsector, technology,
                          sectorElement='supplysector', fromRegion=False):
    """
    Extract a definition from the global-technology-database based on `sector`, `subsector`,
    and `technology`, defined in `srcFile` and create a new file, `dstFile` with the extracted
    bit as a stub-technology definition for the given region. If `fromRegion` is True,
    extract the stub-technology from the regional definition, rather than from the
    global-technology-database.

    :param region: (str) the name of the GCAM region for which to copy the technology
    :param srcFile: (str) the pathname of a source XML file with a global-technology-database
    :param dstFile: (str) the pathname of the file to create
    :param sector: (str) the name of a GCAM sector
    :param subsector: (str) the name of a GCAM subsector within `sector`
    :param technology: (str) the name of a GCAM technology within `sector` and `subsector`
    :param sectorElement: (str) the name of the XML element to create (or search for, if `fromRegion`
        is True) between the ``<region>`` and ``<subsector>`` XML elements. Defaults to 'supplysector'.
    :param fromRegion: (bool) if True, the definition is extracted from a regional definition
        rather than from the global-technology-database.
    :return: True on success, else False
    """
    _logger.info("Extract stub-technology for %s (%s) to %s" % (technology, region if fromRegion else 'global', dstFile))

    if fromRegion:
        xpath = "//region[@name='%s']/%s[@name='%s']/subsector[@name='%s']/stub-technology[@name='%s']" % \
                (region, sectorElement, sector, subsector, technology)
    else:
        xpath = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                (sector, subsector, technology)

    # Read the srcFile to extract the required elements
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(srcFile, parser)

    # Rename technology => stub-technology (for global-tech-db case)
    elts = tree.xpath(xpath)
    if len(elts) != 1:
        raise PygcamException('Xpath "%s" failed' % xpath)

    technologyElt = elts[0]
    technologyElt.tag = 'stub-technology'       # no-op if fromRegion == True

    # Surround the extracted XML with the necessary hierarchy
    scenarioElt  = ET.Element('scenario')
    worldElt     = ET.SubElement(scenarioElt, 'world')
    regionElt    = ET.SubElement(worldElt, 'region', attrib={'name' : region})
    sectorElt    = ET.SubElement(regionElt, sectorElement, attrib={'name' : sector})
    subsectorElt = ET.SubElement(sectorElt, 'subsector', attrib={'name' : subsector})
    subsectorElt.append(technologyElt)

    # Workaround for parsing error: explicitly name shutdown deciders
    elts = scenarioElt.xpath("//phased-shutdown-decider|profit-shutdown-decider")
    for elt in elts:
        parent = elt.getparent()
        parent.remove(elt)

    _logger.info("Writing '%s'", dstFile)
    newTree = ET.ElementTree(scenarioElt)
    newTree.write(dstFile, xml_declaration=True, pretty_print=True)

    return True

def expandYearRanges(seq):
    """
    Expand a sequence of (year, value) tuples, or a dict keyed by
    year, where the year argument may be a string containing identifying
    range of values with an optional "step" value indicated after a ":".
    The default step is 5 years. For example, "2015-2030" expands to
    (2015, 2020, 2025, 2030), and "2015-2020:1" expands to
    (2015, 2016, 2017, 2018, 2019, 2020). When a range is given, the
    tuple is replaced with a sequence of tuples naming each year explicitly.
    Typical usage is ``for year, price in expandYearRanges(values): ...``.

    :param seq_or_dict:
        The sequence of (year, value) tuples, or any object with an
        items() method that returns (year, value) pairs.
    :return:
        A list of tuples with the expanded sequence.
    """
    result = []
    try:
        seq = list(seq.items())     # convert dict or Series to list of pairs
    except:                         # or quietly fail, and just use 'seq' as is
        pass

    for year, value in seq:
        value = float(value)
        if isinstance(year, six.string_types) and '-' in year:
            m = re.search('^(\d{4})-(\d{4})(:(\d+))?$', year)
            if not m:
                raise SetupException('Unrecognized year range specification: %s' % year)

            startYear = int(m.group(1))
            endYear   = int(m.group(2))
            stepStr = m.group(4)
            step = int(stepStr) if stepStr else 5
            expanded = [[y, value] for y in range(startYear, endYear+step, step)]
            result.extend(expanded)
        else:
            result.append((int(year), value))

    return result

# TBD: maybe xmlSetup should be the only approach rather than supporting original setup subclasses.
# TBD: this way we can assume scenario definition exists in xml format and create an API to get the
# TBD: information about any scenario definition from xmlSetup.py.
#
# TBD: The question is whether command-line override capability is required, or if all should be in XML.
# TBD: Need to think through alternative use cases.
#
# TBD: should be no need to pass baseline since this can be inferred from scenario and scenarioGroup.
# TBD: also can tell if it's a baseline; if not, find and cache ref to baseline
class ScenarioInfo(object):
    def __init__(self, scenarioGroup, scenarioName, scenarioSubdir,
                 xmlSourceDir, xmlGroupSubdir, sandboxRoot, sandboxGroupSubdir):

        self.scenarioGroup  = scenarioGroup
        self.scenarioName   = scenarioName
        self.scenarioSubdir = scenarioSubdir or scenarioName

        self.xmlSourceDir = xmlSourceDir
        self.xmlGroupSubdir = xmlGroupSubdir or scenarioGroup

        self.sandboxRoot  = sandboxRoot
        self.sandboxGroupSubdir = sandboxGroupSubdir or scenarioGroup

        self.isBaseline = False # TBD

        if not self.isBaseline:
            self.baselineName = 'something'
            self.baselineInfo = self.fromXmlSetup(scenarioGroup, self.baselineName)

        # TBD: after setting self.x for all x:
        self.configPath = pathjoin(self.scenarioDir(), 'config.xml', realPath=True)

    @classmethod
    def fromXmlSetup(cls, scenarioGroup, scenarioName):
        # TBD: lookup the group and scenario, grab all data and
        # TBD: return ScenarioInfo(...)
        pass

    def absPath(self, x):
        pass

    def relPath(self, y):
        pass

    def scenarioXmlSourceDir(self, xmlSubdir=True):
        xmlDir = 'xml' if xmlSubdir else ''
        return pathjoin(self.xmlSourceDir, self.xmlGroupSubdir, self.scenarioSubdir, xmlDir)

    def scenarioXmlOutputDir(self):
        return pathjoin(self.xmlOutputDir, self.scenarioGroup, self.scenarioName)

    def scenarioXmlSourceFiles(self):
        # These two versions handle legacy case with extra 'xml' subdir and new approach, without
        files = glob.glob(self.scenarioXmlSourceDir(xmlSubdir=False) + '/*.xml')
        files += glob.glob(self.scenarioXmlSourceDir(xmlSubdir=True) + '/*.xml')
        return files

    def cfgPath(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        if not self.configPath:
            # compute the first time, then cache it
            self.configPath = unixPath(os.path.realpath(pathjoin(self.scenario_dir_abs, 'config.xml')))

        return self.configPath

class XMLEditor(object):
    '''
    Base class for scenario setup. Custom scenario processing classes must
    subclass this. Represents the information required to setup a scenario, i.e.,
    to generate and/or copy the required XML files into the XML output dir.
    '''
    # TBD: consider whether init should take an object describing the scenario
    # TBD: that can be populated from a scenario instance from xmlSetup.py or something
    # TBD: specific to the task. All these args are a pain, and there's no method API
    # TBD: to perform common ops.
    # TBD:
    def __init__(self, baseline, scenario, xmlOutputRoot, xmlSourceDir, refWorkspace,
                 groupDir, srcGroupDir, subdir, parent=None):
        self.name = name = scenario or baseline # if no scenario stated, assume baseline
        self.baseline = baseline
        self.scenario = scenario
        self.xmlOutputRoot = xmlOutputRoot
        self.refWorkspace = refWorkspace
        self.xmlSourceDir = xmlSourceDir
        self.sandboxExeDir = pathjoin(getParam('GCAM.SandboxRefWorkspace'), 'exe')
        self.parent = parent
        self.mcsMode = None
        self.mcsValues = None

        self.setupArgs = None

        # TBD: this would be just ../local-xml "project/scenario" occurs once, above
        # Allow scenario name to have arbitrary subdirs between "../local-xml" and
        # the scenario name, e.g., "../local-xml/project/scenario"
        self.subdir = subdir or ''
        self.groupDir = groupDir
        self.srcGroupDir = srcGroupDir or groupDir

        self.configPath = None

        # TBD: xmlOutputRoot is now just scenario dir, so this parameter can disappear
        self.local_xml_abs = makeDirPath((xmlOutputRoot, LOCAL_XML_NAME), create=True)
        self.dyn_xml_abs   = makeDirPath((xmlOutputRoot, DYN_XML_NAME), create=True) # TBD eliminate

        self.local_xml_rel = pathjoin("..", LOCAL_XML_NAME)
        self.dyn_xml_rel   = pathjoin("..", DYN_XML_NAME)   # TBD eliminate

        self.trial_xml_rel = self.trial_xml_abs = None      # used by MCS only

        # TBD: order changes using ScenarioInfo API
        self.scenario_dir_abs = makeDirPath((self.local_xml_abs, groupDir, name), create=True)
        self.scenario_dir_rel = pathjoin(self.local_xml_rel, groupDir, name)

        # Get baseline from ScenarioGroup and use ScenarioInfo API to get this type of info
        self.baseline_dir_rel = pathjoin(self.local_xml_rel, groupDir, self.parent.name) if self.parent else None

        # TBD eliminate
        self.scenario_dyn_dir_abs = makeDirPath((self.dyn_xml_abs, groupDir, name), create=True)
        self.scenario_dyn_dir_rel = pathjoin(self.dyn_xml_rel, groupDir, name)

        # Store commonly-used paths
        gcam_xml = pathjoin('input', getParam('GCAM.DataDir'), 'xml')
        self.gcam_prefix_abs = prefix_abs = pathjoin(refWorkspace, gcam_xml)
        self.gcam_prefix_rel = prefix_rel = pathjoin('../', gcam_xml)

        version = parse_version_info()
        if version > VersionInfo(5, 1, 0):
            # subdirs have been removed in v5.1
            self.aglu_dir_abs = ''
            self.emissions_dir_abs = ''
            self.energy_dir_abs = ''
            self.modeltime_dir_abs = ''
            self.socioeconomics_dir_abs = ''

            self.aglu_dir_rel = ''
            self.emissions_dir_rel = ''
            self.energy_dir_rel = ''
            self.modeltime_dir_rel = ''
            self.socioeconomics_dir_rel = ''
        else:
            # TBD: maybe no need to store these since computable from rel paths
            self.aglu_dir_abs           = pathjoin(prefix_abs, 'aglu-xml')
            self.emissions_dir_abs      = pathjoin(prefix_abs, 'emissions-xml')
            self.energy_dir_abs         = pathjoin(prefix_abs, 'energy-xml')
            self.modeltime_dir_abs      = pathjoin(prefix_abs, 'modeltime-xml')
            self.socioeconomics_dir_abs = pathjoin(prefix_abs, 'socioeconomics-xml')

            self.aglu_dir_rel           = pathjoin(prefix_rel, 'aglu-xml')
            self.emissions_dir_rel      = pathjoin(prefix_rel, 'emissions-xml')
            self.energy_dir_rel         = pathjoin(prefix_rel, 'energy-xml')
            self.modeltime_dir_rel      = pathjoin(prefix_rel, 'modeltime-xml')
            self.socioeconomics_dir_rel = pathjoin(prefix_rel, 'socioeconomics-xml')

        # TBD: add climate and policy subdirs?
        self.solution_prefix_abs = pathjoin(refWorkspace, "input", "solution")
        self.solution_prefix_rel = pathjoin("..", "input", "solution")

    def absPath(self, relPath):
        """
        Convert `relPath` to an absolute path by treating it as relative to
        the current scenario's "exe" directory.

        :param relPath: (str) a path relative to the current "exe" directory
        :return: (str) the absolute path corresponding to `relPath`.
        """
        return pathjoin(self.xmlOutputRoot, 'exe', relPath, normpath=True)

    @staticmethod
    def recreateDir(path):
        removeTreeSafely(path)
        mkdirs(path)

    def setupDynamic(self, args):
        """
        Create dynamic XML files in dyn-xml. These files are generated for policy
        scenarios when XML file contents must be computed from baseline results.

        :param args: (argparse.Namespace) arguments passed from the top-level call
            to setup sub-command
        :return: none
        """

        _logger.info("Generating dyn-xml for scenario %s" % self.name)

        # Delete old generated scenario files
        dynDir = self.scenario_dyn_dir_abs
        self.recreateDir(dynDir)

        scenDir = self.scenario_dir_abs
        xmlFiles = glob.glob("%s/*.xml" % scenDir)

        # TBD: no need to link or copy if all in one place. [But dyn are per-trial; local are not]
        if xmlFiles:
            mode = 'Copy' if getParamAsBoolean('GCAM.CopyAllFiles') else 'Link'
            _logger.info("%s %d static XML files in %s to %s", mode, len(xmlFiles), scenDir, dynDir)

            for xml in xmlFiles:
                base = os.path.basename(xml)
                dst = pathjoin(dynDir, base)
                src = pathjoin(scenDir, base)
                symlinkOrCopyFile(src, dst)
        else:
            _logger.info("No XML files to link in %s", unixPath(scenDir, abspath=True))

        CachedFile.decacheAll()

    def setupStatic(self, args):
        """
        Create static XML files in local-xml. By "static", we mean files whose contents are
        independent of baseline results. In comparison, policy scenarios may generate dynamic
        XML files whose contents are computed from baseline results.

        :param args: (argparse.Namespace) arguments passed from the top-level call to setup
            sub-command.
        :return: none
        """
        _logger.info("Generating local-xml for scenario %s" % self.name)

        scenDir = self.scenario_dir_abs
        mkdirs(scenDir)

        # TBD: there's nothing else now in these dirs, so "xml" subdir is not really needed
        topDir = pathjoin(self.xmlSourceDir, self.srcGroupDir, self.subdir or self.name)
        subDir = pathjoin(topDir, 'xml') # legacy only
        xmlFiles = glob.glob("{}/*.xml".format(topDir)) + glob.glob("{}/*.xml".format(subDir))

        if xmlFiles:
            _logger.info("Copy {} static XML files from {} to {}".format(len(xmlFiles), topDir, scenDir))
            for src in xmlFiles:
                shutil.copy2(src, scenDir)     # copy2 preserves metadata, e.g., timestamp
        else:
            _logger.info("No XML files to copy in %s", unixPath(topDir, abspath=True))

        configPath = self.cfgPath()

        parent = self.parent
        parentConfigPath = parent.cfgPath() if parent else getParam('GCAM.RefConfigFile')

        _logger.info("Copy %s\n      to %s" % (parentConfigPath, configPath))
        shutil.copy(parentConfigPath, configPath)
        os.chmod(configPath, 0o664)

        # set the scenario name
        self.updateConfigComponent('Strings', 'scenarioName', self.name)

        # This is inherited from baseline by policy scenarios; no need to redo this
        if not self.parent:
            self.makeScenarioComponentsUnique()

        # For the following configuration file settings, no action is taken when value is None
        if args.stopPeriod is not None:
            self.setStopPeriod(args.stopPeriod)

        # For the following boolean arguments, we first check if there is any value. If
        # not, no change is made. If a value is given, the parameter is set accordingly.
        if getParam('GCAM.WritePrices'):
            self.updateConfigComponent('Bools', 'PrintPrices', int(getParamAsBoolean('GCAM.WritePrices')))

        if getParam('GCAM.WriteDebugFile'):
            self.updateConfigComponent('Files', 'xmlDebugFileName', value=None,
                                       writeOutput=getParamAsBoolean('GCAM.WriteDebugFile'))

        if getParam('GCAM.WriteXmlOutputFile'):
            self.updateConfigComponent('Files', 'xmlOutputFileName', value=None,
                                       writeOutput=getParamAsBoolean('GCAM.WriteXmlOutputFile'))

        version = parse_version_info()

        if version < VersionInfo(5, 1, 2):
            # this option was removed in gcam-v5.1.2
            if getParam('GCAM.WriteOutputCsv'):
                self.updateConfigComponent('Files', 'outFileName', value=None,
                                           writeOutput=getParamAsBoolean('GCAM.WriteOutputCsv'))

        if version >= VersionInfo(5, 1, 2):
            if getParam('GCAM.WriteRestartFiles'):
                self.updateConfigComponent('Files', 'restart', value=None,
                                           writeOutput=getParamAsBoolean('GCAM.WriteRestartFiles'))

        CachedFile.decacheAll()

    def setup(self, args):
        """
        Calls setupStatic and/or setupDynamic, depending on flags set in args.

        :param args: (argparse.Namespace) arguments passed from the top-level call
            to setup
        :return: none
        """
        _logger.debug('Called XMLEditor.setup(%s)', args)
        self.setupArgs = args   # some subclasses/functions might want access to these

        if not args.dynamicOnly:
            self.setupStatic(args)

        if not args.staticOnly:
            self.setupDynamic(args)

        CachedFile.decacheAll()

    def makeScenarioComponentsUnique(self):
        """
        Give all reference ScenarioComponents a unique "name" tag to facilitate
        manipulation via XPath queries. This is a no-op in GCAM version >= 4.3.

        :return: none
        """
        version = parse_version_info()

        # no longer necessary in 4.3. For 4.2, we reset names to those used in 4.3
        if version < VersionInfo(4, 3, 0):
            self.renameScenarioComponent("interest_rate", pathjoin(self.socioeconomics_dir_rel, "interest_rate.xml"))
            self.renameScenarioComponent("socioeconomics", pathjoin(self.socioeconomics_dir_rel, "socioeconomics_GCAM3.xml"))

            self.renameScenarioComponent("industry", pathjoin(self.energy_dir_rel, "industry.xml"))
            self.renameScenarioComponent("industry_income_elas", pathjoin(self.energy_dir_rel, "industry_incelas_gcam3.xml"))

            self.renameScenarioComponent("cement", pathjoin(self.energy_dir_rel, "cement.xml"))
            self.renameScenarioComponent("cement_income_elas", pathjoin(self.energy_dir_rel, "cement_incelas_gcam3.xml"))

            self.renameScenarioComponent("fertilizer_energy", pathjoin(self.energy_dir_rel, "en_Fert.xml"))
            self.renameScenarioComponent("fertilizer_agriculture", pathjoin(self.aglu_dir_rel, "ag_Fert.xml"))

            for i in (1,2,3):
                tag = 'land%d' % i
                filename = 'land_input_%d.xml' % i
                self.renameScenarioComponent(tag, pathjoin(self.aglu_dir_rel, filename))

                if i > 1:
                    tag = 'protected_' + tag
                    filename = 'protected_' + filename
                    self.renameScenarioComponent(tag, pathjoin(self.aglu_dir_rel, filename))

    def cfgPath(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        if not self.configPath:
            # compute the first time, then cache it
            self.configPath = unixPath(os.path.realpath(pathjoin(self.scenario_dir_abs, 'config.xml')))

        return self.configPath

    def componentPath(self, tag, configPath=None):
        configPath = configPath or self.cfgPath()
        pathname = xmlSel(configPath, '//Value[@name="%s"]' % tag, asText=True)

        if pathname is None:
            raise PygcamException("Failed to find scenario component with tag '%s' in %s" % (tag, configPath))

        return pathname

    def getLocalCopy(self, configTag):
        """
        Get the filename for the most local version (in terms of scenario hierarchy)
        of the XML file identified in the configuration file with `configTag`, and
        copy the file to our scenario dir if not already there.

        :param configTag: (str) the configuration file tag (name="xxx") of an XML file
        :return: (str, str) a tuple of the relative and absolute path of the
          local (i.e., within the current scenario) copy of the file.
        """
        # if configTag.endswith('.xml'):
            # It's not a tag, but a filename

        pathname = self.componentPath(configTag)
        srcAbsPath = pathjoin(self.sandboxExeDir, pathname, abspath=True)

        # TBD: test this
        if not os.path.lexists(srcAbsPath):
            _logger.debug("Didn't find %s; checking reference files" % srcAbsPath)
            # look to sandbox workspace if not found locally
            refWorkspace  = getParam('GCAM.SandboxRefWorkspace')
            refConfigFile = getParam('GCAM.RefConfigFile')

            pathname = self.componentPath(configTag, configPath=refConfigFile)
            srcAbsPath = pathjoin(refWorkspace, 'exe', pathname, abspath=True)

        # If path includes /*-xml/* (e.g., '/energy-xml/', '/aglu-xml/'), retain
        # this subdir in destination, else just use the basename of the path.
        matches = list(re.finditer(XmlDirPattern, srcAbsPath))
        if matches:
            m = matches[-1]
            suffix = os.path.basename(srcAbsPath) if m.group(0) == '/local-xml/' else srcAbsPath[m.start()+1:]   # from after '/' to end
        else:
            suffix = os.path.basename(srcAbsPath)

        dstAbsPath = pathjoin(self.scenario_dir_abs, suffix)
        dstRelPath = pathjoin(self.scenario_dir_rel, suffix)

        copyIfMissing(srcAbsPath, dstAbsPath, makedirs=True)

        return dstRelPath, dstAbsPath

    def updateConfigComponent(self, group, name, value=None, writeOutput=None, appendScenarioName=None):
        """
        Update the value of an arbitrary element in GCAM's configuration.xml file, i.e.,
        ``<{group}><Value name="{name}>{value}</Value></{group}>``

        Optional args are used only for ``<Files>`` group, which has entries like
        ``<Value write-output="1" append-scenario-name="0" name="outFileName">outFile.csv</Value>``
        Values for the optional args can be passed as any of ``[0, 1, "0", "1", True, False]``.

        :param group: (str) the name of a group of config elements in GCAM's configuration.xml
        :param name: (str) the name of the element to be updated
        :param value: (str) the value to set between the ``<Value></Value>`` elements
        :param writeOutput: (coercible to int) for ``<Files>`` group, this sets the optional ``write-output``
           attribute
        :param appendScenarioName: (coercible to int) for ``<Files>`` group, this sets the optional
          ``append-scenario-name`` attribute.
        :return: none
        """
        textArgs = "name='%s'" % name
        if writeOutput is not None:
            textArgs += " write-output='%d'" % (int(writeOutput))
        if appendScenarioName is not None:
            textArgs += " append-scenario-name='%d'" % (int(appendScenarioName))

        _logger.debug("Update <%s><Value %s>%s</Value>" % (group, textArgs, '...' if value is None else value))

        cfg = self.cfgPath()

        prefix = "//%s/Value[@name='%s']" % (group, name)
        pairs = []

        if value is not None:
            pairs.append((prefix, value))

        if writeOutput is not None:
            pairs.append((prefix + "/@write-output", int(writeOutput)))

        if appendScenarioName is not None:
            pairs.append((prefix + "/@append-scenario-name", int(appendScenarioName)))

        xmlEdit(cfg, pairs)

    @callableMethod
    def setClimateOutputInterval(self, years):
        """
        Sets the the frequency at which climate-related outputs are
        saved to the XML database to the given number of years,
        e.g., ``<Value name="climateOutputInterval">1</Value>``.
        **Callable from XML setup files.**

        :param years: (coercible to int) the number of years to set as the climate (GHG)
           output interval
        :return: none
        """
        self.updateConfigComponent('Ints', 'climateOutputInterval', coercible(years, int))

    def addScenarioComponent(self, name, xmlfile):
        """
        Add a new ``<ScenarioComponent>`` to the configuration file, at the end of the list
        of components.

        :param name: (str) the name to assign to the new scenario component
        :param xmlfile: (str) the location of the XML file, relative to the `exe` directory
        :return: none
        """
        # Ensure no duplicates tags
        self.deleteScenarioComponent(name)

        xmlfile = unixPath(xmlfile)
        _logger.info("Add ScenarioComponent name='%s', xmlfile='%s'" % (name, xmlfile))

        cfg = self.cfgPath()
        item = CachedFile.getFile(cfg)
        item.setEdited()

        elt = item.tree.find('//ScenarioComponents')
        node = ET.SubElement(elt, 'Value')
        node.set('name', name)
        node.text = xmlfile

    def insertScenarioComponent(self, name, xmlfile, after):
        """
        Insert a ``<ScenarioComponent>`` to the configuration file, following the
        entry named by ``after``.

        :param name: (str) the name to assign to the new scenario component
        :param xmlfile: (str) the location of the XML file, relative to the `exe` directory
        :param after: (str) the name of the element after which to insert the new component
        :return: none
        """
        # Ensure no duplicates tags
        self.deleteScenarioComponent(name)

        xmlfile = unixPath(xmlfile)
        _logger.info("Insert ScenarioComponent name='%s', xmlfile='%s' after value '%s'" % (name, xmlfile, after))

        cfg = self.cfgPath()
        item = CachedFile.getFile(cfg)
        item.setEdited()

        elt = item.tree.find('//ScenarioComponents')
        afterNode = elt.find('Value[@name="%s"]' % after)
        if afterNode is None:
            raise SetupException("Can't insert %s after %s, as the latter doesn't exist" % (name, after))

        index = elt.index(afterNode) + 1

        node = ET.Element('Value')
        node.set('name', name)
        node.text = xmlfile
        elt.insert(index, node)

    def updateScenarioComponent(self, name, xmlfile):
        """
        Set a new filename for a ScenarioComponent identified by the ``<Value>`` element name.

        :param name: (str) the name of the scenario component to update
        :param xmlfile: (str) the location of the XML file, relative to the `exe` directory, that
           should replace the existing value
        :return: none
        """
        xmlfile = unixPath(xmlfile)

        self.updateConfigComponent('ScenarioComponents', name, xmlfile)

    def deleteScenarioComponent(self, name, useCache=True):
        """
        Delete a ``<ScenarioComponent>`` identified by the ``<Value>`` element name.

        :param name: (str) the name of the ScenarioComponent to delete
        :return: none
        """
        _logger.info("Delete ScenarioComponent name='%s' for scenario" % name)
        cfg = self.cfgPath()
        item = CachedFile.getFile(cfg)

        elt = item.tree.find("//ScenarioComponents")
        valueNode = elt.find("Value[@name='%s']" % name)
        if valueNode is not None:
            elt.remove(valueNode)
            item.setEdited()

    def renameScenarioComponent(self, name, xmlfile):
        """
        Modify the name of a ``ScenarioComponent``, located by the XML file path it holds.
        This is used in to create a local reference XML that has unique names
        for all scenario components, which allows all further modifications to refer
        only to the (now unique) names.

        :param name: (str) the new name for the scenario component
        :param xmlfile: (str) the XML file path used to locate the scenario component
        :return: none
        """
        xmlfile = unixPath(xmlfile)
        _logger.debug("Rename ScenarioComponent name='%s', xmlfile='%s'" % (name, xmlfile))
        cfg = self.cfgPath()

        xmlEdit(cfg, [("//ScenarioComponents/Value[text()='%s']/@name" % xmlfile, name)])

    @callableMethod
    def multiply(self, tag, xpath, value):
        """
        Run the `xpath` query on the XML file with `tag` in the config file, and
        replace all values found with the result of multiplying them by `value`.

        :param tag: (str) the tag identifying a scenario component
        :param xpath: (str) an XPath query to run against the file indicated by `tag`
        :param value: (float) a value to multiply results of the `xpath` query by.
        :return: none
        """
        _logger.info("multiply: tag='{}', xpath='{}', value={}".format(tag, xpath, value))

        fileRel, fileAbs = self.getLocalCopy(tag)

        xmlEdit(fileAbs, [(xpath, value)], op='multiply')
        self.updateScenarioComponent(tag, fileRel)

    @callableMethod
    def add(self, tag, xpath, value):
        """
        Run the `xpath` query on the XML file with `tag` in the config file, and
        replace all values found with the result of adding `value` to them.

        :param tag: (str) the tag identifying a scenario component
        :param xpath: (str) an XPath query to run against the file indicated by `tag`
        :param value: (float) a value to multiply results of the `xpath` query by.
        :return: none
        """
        _logger.info("add: tag='{}', xpath='{}', value={}".format(tag, xpath, value))

        fileRel, fileAbs = self.getLocalCopy(tag)

        xmlEdit(fileAbs, [(xpath, value)], op='add')
        self.updateScenarioComponent(tag, fileRel)

    # TBD dynamic keyword might still be useful if subdir e.g. local-xml/dynamic but policy file would be in local-xml anyway
    @callableMethod
    def addMarketConstraint(self, target, policy, dynamic=False,
                            baselinePolicy=False): # TBD: should be able to eliminate this arg
        """
        Adds references to a pair of files comprising a policy, i.e., a policy definition
        file and a constraint file. References to the two files--assumed to be named ``XXX-{subsidy,tax}.xml``
        and ``XXX-{subsidy,tax}-constraint.xml`` for policy `target` ``XXX``--are added to the configuration file.
        **Callable from XML setup files.**

        :param target: (str) the subject of the policy, e.g., corn-etoh, cell-etoh, ft-biofuel, biodiesel
        :param policy: (str) one of ``subsidy`` or ``tax``
        :param dynamic: (str) True if the XML file was dynamically generated, and thus found in ``dyn-xml``
           rather than ``local-xml``
        :param baselinePolicy: (bool) if True, the policy file is linked to the baseline directory
           rather than this scenario's own directory.
        :return: none
        """
        _logger.info("Add market constraint: %s %s for %s" % (target, policy, self.name))

        cfg = self.cfgPath()

        basename = "%s-%s" % (target, policy)	# e.g., biodiesel-subsidy

        policyTag     = target + "-policy"
        constraintTag = target + "-constraint"

        reldir = self.scenario_dyn_dir_rel if dynamic else self.scenario_dir_rel

        # TBD: Could look for file in scenario, but if not found, look in baseline, eliminating this flag
        policyReldir = self.baseline_dir_rel if baselinePolicy else reldir

        policyXML     = pathjoin(policyReldir, basename + ".xml") # TBD: "-market.xml" for symmetry?
        constraintXML = pathjoin(reldir, basename + "-constraint.xml")

        # See if element exists in config file (-Q => quiet; just report exit status)
        xpath = '//ScenarioComponents/Value[@name="%s"]' % policyTag

        # If we've already added files for policy/constraint on this target,
        # we replace the old values with new ones. Otherwise, we add them.
        addOrUpdate = self.updateScenarioComponent if xmlSel(cfg, xpath) else self.addScenarioComponent
        addOrUpdate(policyTag, policyXML)
        addOrUpdate(constraintTag, constraintXML)

    @callableMethod
    def delMarketConstraint(self, target, policy):
        """
        Delete the two elements defining a market constraint from the configuration file.
        The filenames are constructed as indicated in the `addMarketConstraint` method.
        **Callable from XML setup files.**

        :param target: (str) the subject of the policy, e.g., corn-etoh, cell-etoh,
            ft-biofuel, biodiesel
        :param policy: (str) one of ``subsidy`` or ``tax``
        :return: none
        """
        _logger.info("Delete market constraint: %s %s for %s" % (target, policy, self.name))
        cfg = self.cfgPath()

        # if policy == "subsidy":
        #     policy = "subs"	# use shorthand in filename

        policyTag     = target + "-" + policy
        constraintTag = target + "-constraint"

        # See if element exists in config file (-Q => quiet; just report exit status)
        xpath = '//ScenarioComponents/Value[@name="%s"]' % policyTag

        if xmlSel(cfg, xpath):
            # found it; delete the elements
            self.deleteScenarioComponent(policyTag)
            self.deleteScenarioComponent(constraintTag)

    @callableMethod
    def setStopPeriod(self, yearOrPeriod):
        """
        Sets the model stop period. If `stopPeriod` is <= 22, the stop period is set to
        the given value. If the value > 2000, the value is treated as a year and converted
        to the correct stop period for the configuration file.
        **Callable from XML setup files.**

        :param yearOrPeriod: (coercible to int) this argument is treated as a literal
          stop period if the value is < 1000. (N.B. 2015 = step 4, 2020 = step 5, and so
          on.) If yearOrPeriod >= 1000, it is treated as a year and converted
          to a stopPeriod for use in the GCAM configuration file.
        :return: none
        :raises: SetupException
        """
        value = coercible(yearOrPeriod, int)
        stopPeriod = value if 1 < value < 1000 else 1 + (value - 2000)//5

        self.updateConfigComponent('Ints', 'stop-period', stopPeriod)

    @callableMethod
    def setInterpolationFunction(self, region, supplysector, subsector, fromYear, toYear,
                                 funcName='linear', applyTo='share-weight', stubTechnology=None,
                                 delete=False):
        """
        Set the interpolation function for the share-weight of the `subsector`
        of `supplysector` to `funcName` between years `fromYear` to `toYear`
        in `region`. **Callable from XML setup files.**

        :param region: (str) the GCAM region to operate on
        :param supplysector: (str) the name of a supply sector
        :param subsector: (str) the name of a sub-sector
        :param fromYear: (str or int) the year to start interpolating
        :param toYear: (str or int) the year to stop interpolating
        :param funcName: (str) the name of an interpolation function
        :param applyTo: (str) what the interpolation function is applied to
        :param stubTechnology: (str) the name of a technology to apply function to
        :param delete: (bool) if True, set delete="1", otherwise don't.
        :return: none
        """
        _logger.info("Set interpolation function for '%s' : '%s' to '%s'" % (supplysector, subsector, funcName))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)

        # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/interpolation-rule
        prefix = '//region[@name="%s"]/supplysector[@name="%s"]/subsector[@name="%s"]%s/interpolation-rule[@apply-to="%s"]' % \
                 (region, supplysector, subsector,
                  '/stub-technology[@name="%s"]' % stubTechnology if stubTechnology else '',
                  applyTo)

        args = [(prefix + '/@from-year', str(fromYear)),
                (prefix + '/@to-year', str(toYear)),
                (prefix + '/interpolation-function/@name', funcName)]

        if delete:
            args.append((prefix + '/@delete', "1"))

        xmlEdit(enTransFileAbs, args)

        self.updateScenarioComponent("energy_transformation", enTransFileRel)

    @callableMethod
    def setupSolver(self, solutionTolerance=None, broydenTolerance=None,
                    maxModelCalcs=None, maxIterations=None):
        """
        Set the model solution tolerance to the given values for the solver
        "driver" (`solutionTolerance`) and, optionally for the Broyden component
        (`broydenTolerance`).
        **Callable from XML setup files.**

        :param solutionTolerance: (coercible to float, > 0.0) the value to set for the driver tolerance
        :param broydenTolerance: (coercible to float, > 0.0) the value to set for the Broyden component
            tolerance. (If both are provided, the function requires that
            componentTolerance <= driverTolerance.)
        :param maxModelCalcs: (coercible to int, > 0) maximum number of calculations to run in the driver
        :param maxIterations: (coercible to int, > 0) maximum number of iterations to allow in the
            Broyden component
        :return: none
        """
        def coercibleAndPositive(name, value, requiredType):
            if value is None:
                return None

            value = coercible(value, requiredType)
            if value <= 0:
                raise SetupException(name + ' must be greater than zero')

            _logger.info("Set %s to %s", name, value)
            return value

        solutionTol = coercibleAndPositive('Driver solution tolerance', solutionTolerance, float)
        broydenTol  = coercibleAndPositive('Broyden component tolerance', broydenTolerance, float)

        if solutionTol and broydenTol:
            if broydenTol > solutionTol:
                raise SetupException('Broyden component tolerance cannot be greater than driver solution tolerance')

        maxModelCalcs = coercibleAndPositive('maxModelCalcs', maxModelCalcs, int)
        maxIterations = coercibleAndPositive('maxIterations', maxIterations, int)

        solverFile = 'cal_broyden_config.xml'
        solverFileRel, solverFileAbs = self.getLocalCopy(SOLVER_TAG)

        prefix = "//scenario/user-configurable-solver[@year>=2010]/"
        pairs = []

        if solutionTolerance:
            pairs.append((prefix + 'solution-tolerance', solutionTolerance))

        if broydenTolerance:
            pairs.append((prefix + 'broyden-solver-component/ftol', broydenTolerance))

        if maxModelCalcs:
            pairs.append((prefix + 'max-model-calcs', maxModelCalcs))

        if maxIterations:
            pairs.append((prefix + 'broyden-solver-component/max-iterations', maxIterations))

        xmlEdit(solverFileAbs, pairs)

        self.updateScenarioComponent("solver", solverFileRel)

    @callableMethod
    def dropLandProtection(self, dropEmissions=True):
        self.deleteScenarioComponent("protected_land2")
        self.deleteScenarioComponent("protected_land3")

        if dropEmissions:
            version = parse_version_info()
            if version > VersionInfo(5, 0, 0):
                # drop emissions for protected land
                self.deleteScenarioComponent("nonco2_aglu_prot")

    @callableMethod
    def protectLand(self, fraction, landClasses=None, otherArable=False,
                    regions=None, unprotectFirst=False):
        """
        Modify land_input files to protect a constant fraction of unmanaged
        land of the given classes, in the given regions.
        **Callable from XML setup files.**

        :param fraction: (float) the fraction of land in the given land classes
               to protect
        :param landClasses: a string or a list of strings, or None. If None, all
               "standard" unmanaged land classes are modified.
        :param otherArable: (bool) if True, land class 'OtherArableLand' is
            included in default land classes.
        :param regions: a string or a list of strings, or None. If None, all
               regions are modified.
        """
        from .landProtection import protectLand

        _logger.info("Protecting %d%% of land globally", int(fraction * 100))

        # NB: this code depends on these being the tags assigned to the land files
        # as is currently the case in XmlEditor.makeScenarioComponentsUnique()
        for num in [2, 3]:
            fileTag  = 'land%d' % num
            landFileRel, landFileAbs = self.getLocalCopy(fileTag)

            protectLand(landFileAbs, landFileAbs, fraction, landClasses=landClasses,
                        otherArable=otherArable, regions=regions, unprotectFirst=unprotectFirst)
            self.updateScenarioComponent(fileTag, landFileRel)

    # TBD: test
    @callableMethod
    def protectionScenario(self, scenarioName, unprotectFirst=True):
        """
        Implement the protection scenario `scenarioName`, defined in the file given
        by config variable `GCAM.LandProtectionXmlFile`.
        **Callable from XML setup files.**

        :param scenarioName: (str) the name of a scenario defined in the land
           protection XML file.
        :param unprotectFirst: (bool) if True, make all land "unprotected" before
           protecting.
        :return: none
        """
        from .landProtection import runProtectionScenario

        _logger.info("Using protection scenario %s", scenarioName)

        landXmlFiles = []

        # NB: this code depends on these being the tags assigned to the land files
        # as is currently the case in XmlEditor.makeScenarioComponentsUnique()
        for num in [2, 3]:
            fileTag  = 'land%d' % num
            landFileRel, landFileAbs = self.getLocalCopy(fileTag)

            landXmlFiles.append(landFileAbs)
            self.updateScenarioComponent(fileTag, landFileRel)

        # TBD: revisit this; it's a bit of a hack for Oct 16 deliverable
        scenarioFile = pathname = getParam('GCAM.LandProtectionXmlFile')
        if self.mcsMode == 'trial':
            basename = os.path.basename(pathname)
            scenario = self.scenario or self.baseline
            scenarioFile = unixPath(pathjoin(self.trial_xml_abs, 'local-xml',
                                             self.groupDir, scenario, basename))

        runProtectionScenario(scenarioName, scenarioFile=scenarioFile, inPlace=True,
                              xmlFiles=landXmlFiles, unprotectFirst=unprotectFirst)

    def getScenarioOrTrialDirs(self, subdir=''):
        dirRel = pathjoin(self.trial_xml_rel, subdir) if self.mcsMode == 'trial' \
            else self.scenario_dir_rel

        dirAbs = pathjoin(self.trial_xml_abs, subdir) if self.mcsMode == 'trial' \
            else self.scenario_dir_abs

        return dirRel, dirAbs

    @callableMethod
    def taxCarbon(self, value, startYear=2020, endYear=2100, timestep=5,
                  rate=0.05, regions=GCAM_32_REGIONS, market='global'):
        '''
        Generate an XML file defining a global carbon tax starting
        at `value` and increasing by `rate` annually. Generate values
        for the give `years`. The first year in `years` is assumed to be
        the year at which the tax starts at `value`. The generated file
        is named 'carbon-tax-{market}.xml' and is added to the configuration.
        **Callable from XML setup files.**

        :param value: (float) the initial value of the tax ($/tonne)
        :param years: (list(int)) years to set carbon taxes. Default is 2020-2100
           at 10 year time-steps.
        :param rate: (float) annual rate of increase. Default is 0.05.
        :param regions: (list(str)) the regions for which to create a C tax market.
             Default is all 32 GCAM regions.
        :param market: (str) the name of the market to create. Default is 'global'.
        :return: none
        '''
        from .carbonTax import genCarbonTaxFile

        tag = 'carbon-tax-' + market
        filename = tag + '.xml'

        # TBD: need to generalize this since any modification can be per-trial or universal
        dirRel, dirAbs = self.getScenarioOrTrialDirs(subdir='local-xml')

        fileRel = pathjoin(dirRel, filename)
        fileAbs = pathjoin(dirAbs, filename)

        genCarbonTaxFile(fileAbs, value, startYear=startYear, endYear=endYear,
                         timestep=timestep, rate=rate, regions=regions, market=market)
        self.addScenarioComponent(tag, fileRel)

    @callableMethod
    def taxBioCarbon(self, market='global', regions=None, forTax=True, forCap=False):
        """
        Create the XML for a linked policy to include LUC CO2 in a CO2 cap or tax policy (or both).
        This function generates the equivalent of any of the 4 files in input/policy/:
        global_ffict.xml               (forTax=False, forCap=False)
        global_ffict_in_constraint.xml (forTax=False, forCap=True)
        global_uct.xml                 (forTax=True,  forCap=False)
        global_uct_in_constraint.xml   (forTax=True,  forCap=True)

        However, unlike those files, the market need not be global, and the set of regions to
        which to apply the policy can be specified.

        :param market: (str) the name of the market for which to create the linked policy
        :param regions: (list of str or None) the regions to apply the policy to, or None
          to indicate all regions.
        :param forTax: (bool) True if the linked policy should apply to a CO2 tax
        :param forCap: (bool) True if the linked policy should apply to a CO2 cap
        :return: (str) the generated XML text
        """
        from .carbonTax import genLinkedBioCarbonPolicyFile

        tag = 'bio-carbon-tax-' + market
        filename = tag + '.xml'

        # TBD: need to generalize this since any modification can be per-trial or universal
        dirRel, dirAbs = self.getScenarioOrTrialDirs(subdir='local-xml')

        fileRel = pathjoin(dirRel, filename)
        fileAbs = pathjoin(dirAbs, filename)

        genLinkedBioCarbonPolicyFile(fileAbs, market=market, regions=regions,
                                     forTax=forTax, forCap=forCap)
        self.addScenarioComponent(tag, fileRel)

    # TBD: test
    @callableMethod
    def setRegionPopulation(self, region, values):
        """
        Set the population for the given region to the values for the given years.
        **Callable from XML setup files.**

        :param region: (str) the name of one of GCAM's regions.
        :param values: (dict-like or iterable of tuples of (year, pop)), specifying
           the population to set for each year given.
        :return: none
        """
        # msg = "Set population for %s in %s to:" % (region, self.name)
        # printSeries(values, region, header=msg, loglevel='INFO')

        tag = 'socioeconomics'
        #path = self.componentPath(tag)
        # fileRel, fileAbs = self.getLocalCopy(path)
        fileRel, fileAbs = self.getLocalCopy(tag)

        prefix = '//region[@name="%s"]/demographics/populationMiniCAM' % region
        pairs = []
        for year, pop in expandYearRanges(values):
            pairs.append((prefix + ('[@year="%s"]/totalPop' % year), int(round(pop))))

        xmlEdit(fileAbs, pairs)
        self.updateScenarioComponent(tag, fileRel)

    # TBD: test
    @callableMethod
    def setGlobalTechNonEnergyCost(self, sector, subsector, technology, values):
        """
        Set the non-energy cost of for technology in the global-technology-database,
        given a list of values of (year, price). The price is applied to all years
        indicated by the range.
        **Callable from XML setup files.**

        :param sector: (str) the name of a GCAM sector
        :param subsector: (str) the name of a GCAM subsector within `sector`
        :param technology: (str) the name of a GCAM technology in `subsector`
        :param values: (dict-like or iterable of tuples of (year, price)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.items() after
            which the rest of the explanation above applies. The `price` can be
            anything coercible to float.
        :return: none
        """
        msg = "Set non-energy-cost of %s for %s to:" % (technology, self.name)
        _logger.info(printSeries(values, technology, header=msg, asStr=True))

        #_logger.info("Set non-energy-cost of %s for %s to %s" % (technology, self.name, values))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)

        prefix = '//global-technology-database/location-info[@sector-name="%s" and @subsector-name="%s"]/technology[@name="%s"]' % \
                 (sector, subsector, technology)
        suffix = '/minicam-non-energy-input[@name="non-energy"]/input-cost'

        pairs = []
        for year, price in expandYearRanges(values):
            pairs.append((prefix + ('/period[@year="%s"]' % year) + suffix, price))

        xmlEdit(enTransFileAbs, pairs)

        self.updateScenarioComponent("energy_transformation", enTransFileRel)

    # TBD: Test
    @callableMethod
    def setGlobalTechShutdownRate(self, sector, subsector, technology, values):
        """
        Create a modified version of en_transformation.xml with the given shutdown
        rates for `technology` in `sector` based on the data in `values`.
        **Callable from XML setup files.**

        :param sector: (str) the name of a GCAM sector
        :param subsector: (str) the name of a GCAM subsector within `sector`
        :param technology: (str) the name of a GCAM technology in `subsector`
        :param values: (dict-like or iterable of tuples of (year, shutdownRate)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.items() after
            which the rest of the explanation above applies. The `shutdownRate` can be
            anything coercible to float.
        :param xmlBasename: (str) the name of an xml file in the energy-xml folder to edit.
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This must match `xmlBasename`.
        :return: none
        """
        _logger.info("Set shutdown rate for (%s, %s) to %s for %s" % (sector, technology, values, self.name))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)

        prefix = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                 (sector, subsector, technology)

        pairs = []

        for year, value in expandYearRanges(values):
            pairs.append((prefix + "/period[@year='%s']/phased-shutdown-decider/shutdown-rate" % year,
                         coercible(value, float)))

        xmlEdit(enTransFileAbs, pairs)
        self.updateScenarioComponent("energy_transformation", enTransFileRel)

    #
    # //region[@name=""]/energy-final-demand[@name=""]/price-elasticity[@year=""]
    #
    # names of energy-final-demand:
    # 'aglu-xml/demand_input.xml': "Exports_Meat", "FoodDemand_Crops", "FoodDemand_Meat", "NonFoodDemand_Crops", "NonFoodDemand_Forest", "NonFoodDemand_Meat"
    # 'energy-xml/transportation_UCD.xml': "trn_aviation_intl", "trn_freight", "trn_pass", "trn_shipping_intl"
    # 'energy-xml/cement.xml: "cement"
    # 'energy-xml/industry.xml: "industry"
    #
    @callableMethod
    def setPriceElasticity(self, regions, sectors, configFileTag, values):
        """
        Modify price-elasticity values for the given `regions` and `sectors` in `sector` based on the data in `values`.
        **Callable from XML setup files.**

        :param regions: (str or list of str) the name(s) of a GCAM region or regions, or "global"
           to indicate that price elasticity should be set in all regions. (Or more precisely,
           the change should not be restricted by region.)
        :param sector: (str or list of str) the name of a GCAM (demand) sector. In GCAM v4.3, this
            should be one of {"cement", "industry", "trn_aviation_intl", "trn_freight", "trn_pass",
            "trn_shipping_intl", "Exports_Meat", "FoodDemand_Crops", "FoodDemand_Meat",
            "NonFoodDemand_Crops", "NonFoodDemand_Forest", "NonFoodDemand_Meat"}, however if input
            files have been customized, other values can be used.
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This determines which file is edited, so it must correspond to
           the indicated sector(s).
        :param values: (dict-like or iterable of tuples of (year, elasticity)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.items() after
            which the rest of the explanation above applies. The `elasticity` can be
            anything coercible to float.
        :return: none
        """
        _logger.info("Set price-elasticity for (%s, %s) to %s for %s" % (regions, sectors, values, self.name))

        filenameRel, filenameAbs = self.getLocalCopy(configFileTag)

        def listifyString(value, aliasForNone=None):
            if isinstance(value, six.string_types):
                value = [value]

            # Treat "global" as not restricting by region
            if aliasForNone and len(value) == 1 and value[0] == aliasForNone:
                return None

            return value

        def nameExpression(values):
            '''
            Turn ['a', 'b'] into '@name="a" or @name="b"'
            '''
            names = ['@name="%s"' % v for v in values]
            return ' or '.join(names)

        regions = listifyString(regions, aliasForNone='global')
        nameExpr = '[' + nameExpression(regions) + ']' if regions else ''
        regionExpr = '//region' + nameExpr

        prefix = regionExpr + '/energy-final-demand[%s]' % nameExpression(sectors)

        pairs = []
        for year, value in expandYearRanges(values):
            pairs.append((prefix + '/price-elasticity[@year="%s"]' % year, coercible(value, float)))

        xmlEdit(filenameAbs, pairs)
        self.updateScenarioComponent(configFileTag, filenameRel)

    # TBD: test
    @callableMethod
    def setRegionalShareWeights(self, region, sector, subsector, values,
                               stubTechnology=None,
                               configFileTag=ENERGY_TRANSFORMATION_TAG):
        """
        Create a modified version of en_transformation.xml with the given share-weights
        for `technology` in `sector` based on the data in `values`.
        **Callable from XML setup files.**

        :param region: if not None, changes are made in a specific region, otherwise they're
            made in the global-technology-database.
        :param sector: (str) the name of a GCAM sector
        :param subsector: (str) the name of a GCAM subsector
        :param values: (dict-like or iterable of tuples of (year, shareWeight)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.items() after
            which the rest of the explanation above applies. The `shareWeight` can be
            anything coercible to float.
        :param stubTechnology: (str) the name of a GCAM technology in the global technology database
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This must match `xmlBasename`.
        :return: none
        """
        from .utils import printSeries

        _logger.info("Set share-weights for (%r, %r, %r, %r) for %r",
                     region, sector, subsector, stubTechnology, self.name)
        _logger.info(printSeries(values, 'share-weights', asStr=True))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(configFileTag)

        prefix = "//region[@name='%s']/supplysector[@name='%s']/subsector[@name='%s']" % (region, sector, subsector)

        shareWeight = '/stub-technology[@name="{technology}"]/period[@year="{year}"]/share-weight' \
                      if stubTechnology else '/share-weight[@year="{year}"]'

        pairs = []
        for year, value in expandYearRanges(values):
            pairs.append((prefix + shareWeight.format(technology=stubTechnology, year=year),
                         coercible(value, float)))

        xmlEdit(enTransFileAbs, pairs)
        self.updateScenarioComponent(configFileTag, enTransFileRel)

    # TBD: Test
    @callableMethod
    def setGlobalTechShareWeight(self, sector, subsector, technology, values,
                                 configFileTag=ENERGY_TRANSFORMATION_TAG):
        """
        Create a modified version of en_transformation.xml with the given share-weights
        for `technology` in `sector` based on the data in `values`.
        **Callable from XML setup files.**

        :param sector: (str) the name of a GCAM sector
        :param technology: (str) the name of a GCAM technology in `sector`
        :param values: (dict-like or iterable of tuples of (year, shareWeight)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.items() after
            which the rest of the explanation above applies. The `shareWeight` can be
            anything coercible to float.
        :param xmlBasename: (str) the name of an xml file in the energy-xml folder to edit.
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This must match `xmlBasename`.
        :return: none
        """
        _logger.info("Set share-weights for (%s, %s) to %s for %s" % (sector, technology, values, self.name))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(configFileTag)

        prefix = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                 (sector, subsector, technology)

        pairs = []
        for year, value in expandYearRanges(values):
            pairs.append((prefix + "/period[@year=%s]/share-weight" % year, coercible(value, float)))

        xmlEdit(enTransFileAbs, pairs)
        self.updateScenarioComponent(configFileTag, enTransFileRel)

    # TBD: test
    @callableMethod
    def setEnergyTechnologyCoefficients(self, subsector, technology, energyInput, values):
        '''
        Set the coefficients in the global technology database for the given energy input
        of the given technology in the given subsector.
        **Callable from XML setup files.**

        :param subsector: (str) the name of the subsector
        :param technology: (str)
            The name of the technology, e.g., 'cellulosic ethanol', 'FT biofuel', etc.
        :param energyInput: (str) the name of the minicam-energy-input
        :param values:
            A sequence of tuples or object with ``items`` method returning
            (year, coefficient). For example, to set
            the coefficients for cellulosic ethanol for years 2020 and 2025 to 1.234,
            the pairs would be ((2020, 1.234), (2025, 1.234)).
        :return:
            none
        '''
        _logger.info("Set coefficients for %s in global technology %s, subsector %s: %s" % \
                     (energyInput, technology, subsector, values))

        enTransFileRel, enTransFileAbs = \
            self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)

        prefix = "//global-technology-database/location-info[@subsector-name='%s']/technology[@name='%s']" % \
                 (subsector, technology)
        suffix = "minicam-energy-input[@name='%s']/coefficient" % energyInput

        pairs = []
        for year, coef in expandYearRanges(values):
            pairs.append(("%s/period[@year='%s']/%s" % (prefix, year, suffix), coef))

        xmlEdit(enTransFileAbs, pairs)
        self.updateScenarioComponent("energy_transformation", enTransFileRel)

    @callableMethod
    def writePolicyMarketFile(self, filename, policyName, region, sector, subsector, technology, years,
                              marketType=DEFAULT_MARKET_TYPE):
        pathname = pathjoin(self.scenario_dir_abs, filename)
        policyMarketXml(policyName, region, sector, subsector, technology, years,
                        marketType=marketType, pathname=pathname)

    @callableMethod
    def writePolicyConstraintFile(self, filename, policyName, region, targets, market=None, minPrice=None,
                                  policyElement=DEFAULT_POLICY_ELT, policyType=DEFAULT_POLICY_TYPE):
        pathname = pathjoin(self.scenario_dir_abs, filename)
        policyConstraintsXml(policyName, region, expandYearRanges(targets), market=market, minPrice=minPrice,
                             policyElement=policyElement, policyType=policyType, pathname=pathname)

