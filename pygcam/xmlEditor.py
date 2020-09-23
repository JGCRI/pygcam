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
from .constants import LOCAL_XML_NAME, DYN_XML_NAME
from .error import SetupException, PygcamException
from .log import getLogger
from .policy import (policyMarketXml, policyConstraintsXml, DEFAULT_MARKET_TYPE,
                     DEFAULT_POLICY_ELT, DEFAULT_POLICY_TYPE)
from .utils import (coercible, mkdirs, printSeries, symlinkOrCopyFile, removeTreeSafely,
                    removeFileOrTree, pushd, splitAndStrip, getRegionList)

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
            raise SetupException("Required path '{}' does not exist.".format(path))

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
            _logger.debug("mkdir '%s'", parentDir)
            os.makedirs(parentDir, 0o755)

        _logger.info("Copy %s\n      to %s", src, dst)
        shutil.copy(src, dst)
        os.chmod(dst, 0o644)

class CachedFile(object):
    parser = ET.XMLParser(remove_blank_text=True)

    # Store parsed XML trees here and use with xmlSel/xmlEdit if useCache is True
    cache = {}

    def __init__(self, filename):
        self.filename = filename = os.path.realpath(filename)
        self.edited = False

        _logger.debug("Reading '%s'", filename)
        self.tree = ET.parse(filename, self.parser)
        self.cache[filename] = self

    @classmethod
    def getFile(cls, filename):
        filename = os.path.realpath(filename)  # operate on canonical pathnames

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

    return (result is not None)

def xmlIns(filename, xpath, elt):
    """
    Insert the element `elt` as a child to the node found with `xpath`.
    :param filename: (str) the file to edit
    :param xpath: (str) the xml element(s) to search for
    :param elt: (etree.Element) the node to insert
    :return: none
    """
    item = CachedFile.getFile(filename)
    item.setEdited()

    parentElt = item.tree.find(xpath)
    if parentElt is None:
        raise SetupException("xmlIns: failed to find parent element at {} in {}".format(xpath, filename))

    parentElt.append(elt)

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
    _logger.info("Extract stub-technology for %s (%s) to %s", technology, region if fromRegion else 'global', dstFile)

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
        raise PygcamException('XPath "{}" failed'.format(xpath))

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
                raise SetupException('Unrecognized year range specification: {}'.format(year))

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
                 groupDir, srcGroupDir, subdir, parent=None, mcsMode=None, cleanXML=True):
        self.name = name = scenario or baseline # if no scenario stated, assume baseline
        self.baseline = baseline
        self.scenario = scenario
        self.xmlOutputRoot = xmlOutputRoot
        self.refWorkspace = refWorkspace
        self.xmlSourceDir = xmlSourceDir
        self.sandboxExeDir = pathjoin(getParam('GCAM.SandboxRefWorkspace'), 'exe')
        self.parent = parent
        self.mcsMode = mcsMode
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
        create = bool(xmlOutputRoot)  # create it only if a dir is specified
        self.local_xml_abs = makeDirPath((xmlOutputRoot, LOCAL_XML_NAME), create=create)
        self.dyn_xml_abs   = makeDirPath((xmlOutputRoot, DYN_XML_NAME), create=create)   # TBD eliminate

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

        # Remove stale files from local-xml folder for scenarios, but avoiding doing
        # this when an XmlEditor is created for the baseline to run a non-baseline,
        # which is identified by scenario being None. Skip this in MCS trial mode:
        # config files are generated by gensim and re-used for each trial.
        if cleanXML and scenario and self.mcsMode != 'trial':
            with pushd(self.scenario_dir_abs):
                files = glob.glob('*')
                if files:
                    _logger.debug("Deleting old files from %s: %s", self.scenario_dir_abs, files)
                    for name in files:
                        removeFileOrTree(name)

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

        _logger.info("Generating dyn-xml for scenario %s", self.name)

        # Delete old generated scenario files
        dynDir = self.scenario_dyn_dir_abs
        self.recreateDir(dynDir)

        scenDir = self.scenario_dir_abs
        xmlFiles = glob.glob("{}/*.xml".format(scenDir))

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
        _logger.info("Generating local-xml for scenario %s", self.name)

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

        _logger.info("Copy %s\n      to %s", parentConfigPath, configPath)
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

            for i in (1, 2, 3):
                tag = 'land' + str(i)
                filename = 'land_input_{}.xml'.format(i)
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
        pathname = xmlSel(configPath, '//Value[@name="{}"]'.format(tag), asText=True)

        if pathname is None:
            raise PygcamException("Failed to find scenario component with tag '{}' in {}".format(tag, configPath))

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
            _logger.debug("Didn't find %s; checking reference files", srcAbsPath)
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

    @callableMethod
    def replaceValue(self, tag, xpath, value):
        """
        Replace the value indicated by ``xpath`` with ``value`` in the file
        identified with the config file name ``tag``.

        :param tag: (str) the name of a config file element
        :param xpath: (str) an XPath query string
        :param value: the value to use in place of that found by the xpath.
            (the value is converted to string, so you can pass ints or floats.)
        """
        xmlFileRel, xmlFileAbs = self.getLocalCopy(tag)
        xmlEdit(xmlFileAbs, [(xpath, str(value))])

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
        textArgs = "name='{}'".format(name)
        if writeOutput is not None:
            textArgs += " write-output='%d'" % (int(writeOutput))
        if appendScenarioName is not None:
            textArgs += " append-scenario-name='%d'" % (int(appendScenarioName))

        _logger.debug("Update <%s><Value %s>%s</Value>", group, textArgs, '...' if value is None else value)

        cfg = self.cfgPath()

        prefix = "//{}/Value[@name='{}']".format(group, name)
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

    @callableMethod
    def stringReplace(self, xpath, oldstr, newstr):
        """
        Edit the text for the nodes identified by xpath (applied to the current config file),
        and change all occurrences of `oldstr` to `newstr`. Currently does not support regex.
        **Callable from XML setup files.**

        :param xpath: (str) path to elements whose text should be changed
        :param oldstr: (str) the substring to match
        :param newstr: (str) the replacement string
        :return: none
        """
        cfg = self.cfgPath()
        item = CachedFile.getFile(cfg)
        item.setEdited()

        _logger.info("stringReplace('%s', '%s', '%s')", xpath, oldstr, newstr)

        nodes = item.tree.xpath(xpath)
        if nodes is None:
            raise SetupException("stringReplace: No config elements match xpath '{}'".format(xpath))

        for node in nodes:
            node.text = node.text.replace(oldstr, newstr)

    @callableMethod
    def setConfigValue(self, section, name, value):
        """
        Set the value of the item with `name` in `section` to the given `value`. Numeric
        values are converted to strings automatically.

        :param section: (str) the name of a section in the configuration.xml file, e.g., "Strings", "Bools", "Ints", etc.
        :param name: (str) the name of the attribute on the element to change
        :param value: the new value to set for the identified element
        :return: none
        """
        cfg = self.cfgPath()
        item = CachedFile.getFile(cfg)
        item.setEdited()

        _logger.info("setConfigValue('%s', '%s', '%s')", section, name, value)

        xpath = '//{}/Value[@name="{}"]'.format(section, name)

        elt = item.tree.find(xpath)
        if elt is None:
            raise SetupException("setConfigValue: No config elements match xpath '{}'".format(xpath))

        elt.text = str(value)

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
        _logger.info("Add ScenarioComponent name='%s', xmlfile='%s'", name, xmlfile)

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
        _logger.info("Insert ScenarioComponent name='%s', xmlfile='%s' after value '%s'", name, xmlfile, after)

        cfg = self.cfgPath()
        item = CachedFile.getFile(cfg)
        item.setEdited()

        elt = item.tree.find('//ScenarioComponents')
        afterNode = elt.find('Value[@name="%s"]' % after)
        if afterNode is None:
            raise SetupException("Can't insert {} after {}, as the latter doesn't exist".format(name, after))

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
        _logger.info("Update scenario component name '{}' to refer to '{}'".format(name, xmlfile))
        self.updateConfigComponent('ScenarioComponents', name, xmlfile)

    def deleteScenarioComponent(self, name, useCache=True):
        """
        Delete a ``<ScenarioComponent>`` identified by the ``<Value>`` element name.

        :param name: (str) the name of the ScenarioComponent to delete
        :return: none
        """
        _logger.info("Delete ScenarioComponent name='%s' for scenario", name)
        cfg = self.cfgPath()
        item = CachedFile.getFile(cfg)

        elt = item.tree.find("//ScenarioComponents")
        valueNode = elt.find("Value[@name='{}']".format(name))
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
        _logger.debug("Rename ScenarioComponent name='%s', xmlfile='%s'", name, xmlfile)
        cfg = self.cfgPath()

        xmlEdit(cfg, [("//ScenarioComponents/Value[text()='{}']/@name".format(xmlfile), name)])

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
        _logger.info("multiply: tag='%s', xpath='%s', value=%s", tag, xpath, value)

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
        _logger.info("Add market constraint: %s %s for %s", target, policy, self.name)

        cfg = self.cfgPath()

        basename = target + '-' + policy	# e.g., biodiesel-subsidy

        policyTag     = target + "-policy"
        constraintTag = target + "-constraint"

        reldir = self.scenario_dyn_dir_rel if dynamic else self.scenario_dir_rel

        # TBD: Could look for file in scenario, but if not found, look in baseline, eliminating this flag
        policyReldir = self.baseline_dir_rel if baselinePolicy else reldir

        policyXML     = pathjoin(policyReldir, basename + ".xml") # TBD: "-market.xml" for symmetry?
        constraintXML = pathjoin(reldir, basename + "-constraint.xml")

        # See if element exists in config file (-Q => quiet; just report exit status)
        xpath = '//ScenarioComponents/Value[@name="{}"]'.format(policyTag)

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
        _logger.info("Delete market constraint: %s %s for %s", target, policy, self.name)
        cfg = self.cfgPath()

        # if policy == "subsidy":
        #     policy = "subs"	# use shorthand in filename

        policyTag     = target + "-" + policy
        constraintTag = target + "-constraint"

        # See if element exists in config file (-Q => quiet; just report exit status)
        xpath = '//ScenarioComponents/Value[@name="{}"]'.format(policyTag)

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
    def setupSolver(self, solutionTolerance=None, broydenTolerance=None,
                    maxModelCalcs=None, maxIterations=None, year=2015):
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

            _logger.info("Set %s to %s for year %s", name, value, year)
            return value

        solutionTol = coercibleAndPositive('Driver solution tolerance', solutionTolerance, float)
        broydenTol  = coercibleAndPositive('Broyden component tolerance', broydenTolerance, float)

        if solutionTol and broydenTol:
            if broydenTol > solutionTol:
                raise SetupException('Broyden component tolerance cannot be greater than driver solution tolerance')

        maxModelCalcs = coercibleAndPositive('maxModelCalcs', maxModelCalcs, int)
        maxIterations = coercibleAndPositive('maxIterations', maxIterations, int)

        solverFileRel, solverFileAbs = self.getLocalCopy(SOLVER_TAG)

        prefix = "//scenario/user-configurable-solver[@year={}]/".format(year)
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
            if version >= VersionInfo(5, 0, 0):
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
            fileTag  = 'land' + str(num)
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
        for prefix in ('', 'protected_'):
            for num in [2, 3]:
                fileTag  = '{}land{}'.format(prefix, num)
                landFileRel, landFileAbs = self.getLocalCopy(fileTag)

                landXmlFiles.append(landFileAbs)
                self.updateScenarioComponent(fileTag, landFileRel)

        # TBD: revisit this; it's a bit of a hack for Oct 16, 2019(?) deliverable
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
                  rate=0.05, regions=None, market='global'):
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
             Default is all defined GCAM regions.
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
        tag = 'socioeconomics'
        #path = self.componentPath(tag)
        # fileRel, fileAbs = self.getLocalCopy(path)
        fileRel, fileAbs = self.getLocalCopy(tag)

        prefix = '//region[@name="{}"]/demographics/populationMiniCAM'.format(region)
        pairs = []
        for year, pop in expandYearRanges(values):
            pairs.append(('{}[@year="{}"]/totalPop'.format(prefix, year)), int(round(pop)))

        xmlEdit(fileAbs, pairs)
        self.updateScenarioComponent(tag, fileRel)

    @callableMethod
    def freezeRegionPopulation(self, region, year, endYear=2100):
        """
        Freeze population subsequent to `year` at the value for that year.
        """
        tag = 'socioeconomics'
        fileRel, fileAbs = self.getLocalCopy(tag)

        fileObj = CachedFile.getFile(fileAbs)
        tree = fileObj.tree

        xpath = '//region[@name="{}"]/demographics/populationMiniCAM[@year="{}"]/totalPop'.format(region, year)
        popNode = tree.find(xpath)
        population = popNode.text

        _logger.info("Freezing pop in %s to %s value of %s", region, year, population)
        values = [(y, population) for y in range(year+5, endYear+1, 5)]

        self.setRegionPopulation(region, values)

    @callableMethod
    def freezeGlobalPopulation(self, year, endYear=2100):
        for region in GCAM_32_REGIONS:
            self.freezeRegionPopulation(region, year, endYear=endYear)

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
        msg = "Set non-energy-cost of {} for {} to:".format(technology, self.name)
        _logger.info(printSeries(values, technology, header=msg, asStr=True))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)

        prefix = '//global-technology-database/location-info[@sector-name="%s" and @subsector-name="%s"]/technology[@name="%s"]' % \
                 (sector, subsector, technology)
        suffix = '/minicam-non-energy-input[@name="non-energy"]/input-cost'

        pairs = []
        for year, price in expandYearRanges(values):
            pairs.append(('{}/period[@year="{}"]{}'.format(prefix, year, suffix), price))

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
        :return: none
        """
        _logger.info("Set shutdown rate for (%s, %s) to %s for %s", sector, technology, values, self.name)

        enTransFileRel, enTransFileAbs = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)

        prefix = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                 (sector, subsector, technology)

        pairs = []

        for year, value in expandYearRanges(values):
            pairs.append(("{}/period[@year='{}']/phased-shutdown-decider/shutdown-rate".format(prefix, year),
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
        _logger.info("Set price-elasticity for (%s, %s) to %s for %s", regions, sectors, values, self.name)

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
            names = ['@name="{}"'.format(v) for v in values]
            return ' or '.join(names)

        regions = listifyString(regions, aliasForNone='global')
        nameExpr = '[' + nameExpression(regions) + ']' if regions else ''
        regionExpr = '//region' + nameExpr

        prefix = regionExpr + '/energy-final-demand[{}]'.format(nameExpression(sectors))

        pairs = []
        for year, value in expandYearRanges(values):
            pairs.append(('{}/price-elasticity[@year="{}"]'.format(prefix, year), coercible(value, float)))

        xmlEdit(filenameAbs, pairs)
        self.updateScenarioComponent(configFileTag, filenameRel)

    @callableMethod
    def setInterpolationFunction(self, regions, supplysector, subsector, fromYear, toYear,
                                 funcName='linear', applyTo='share-weight', fromValue=None,
                                 toValue=None,  stubTechnology=None, supplysectorTag='supplysector', subsectorTag='subsector',
                                 technologyTag='stub-technology', configFileTag=ENERGY_TRANSFORMATION_TAG, delete=False):
        """
        Set the interpolation function for the share-weight of the `subsector` of `supplysector`
        (and optional technology) to `funcName` between years `fromYear` to `toYear` in `region`.
        **Callable from XML setup files.**

        :param regions(s): (str or None) If a string, the GCAM region(s) to operate on. Value can
            be a single region or a comma-delimited list of regions. If None, the function is applied
            to all regions found in the XML file.
        :param supplysector: (str) the name of a supply sector
        :param supplysectorTag: (str) the tag for the supplysector level. Default is 'supplysector', but
            for electricity, this should be passed as supplysectorTag='pass-through-sector'
        :param subsectorTag: (str) the tag for the subsector level. Default is 'subsector', but
            for transportation, this should be passed as subsectorTag='tranSubsector'
        :param subsector: (str) the name of a sub-sector
        :param fromYear: (str or int) the year to start interpolating
        :param toYear: (str or int) the year to stop interpolating
        :param funcName: (str) the name of an interpolation function
        :param applyTo: (str) what the interpolation function is applied to
        :param fromValue: (str or number) the value to set in the <from-value> element (optional)
        :param toValue: (str or number) the value to set in the <to-value> element (required for
            all but "fixed" interpolation function.)
        :param stubTechnology: (str) the name of a technology to apply function to; if absent,
            the function is applied at the subsector level.
        :param technologyTag: (str) the tag for the technology level. Default is 'stub-technology', but for
            certain sectors it may be 'technology'
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This determines which file is edited, so it must correspond to
           the indicated sector(s). Default is 'energy_transformation'.
        :param delete: (bool) if True, set delete="1", otherwise don't.
        :return: none
        """
        _logger.info("Set interpolation function '%s' for '%s' : '%s%s'",
                     funcName, supplysector, subsector,
                     (' : ' + stubTechnology if stubTechnology else ''))

        toYear = str(toYear)
        fromYear = str(fromYear)

        xmlFileRel, xmlFileAbs = self.getLocalCopy(configFileTag)

        item = CachedFile.getFile(xmlFileAbs)
        tree = item.tree

        # convert to a list; if no regions given, get list of regions in this file
        regionList = splitAndStrip(regions, ',') if regions else tree.xpath('//region/@name')

        args = []

        for region in regionList:
            regionElt = '//region[@name="{}"]'.format(region)

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/interpolation-rule
            subsect = '{}/{}[@name="{}"]/{}[@name="{}"]'.format(regionElt, supplysectorTag, supplysector, subsectorTag, subsector)

            if stubTechnology:
                rule_parent = subsect + '/{}[@name="{}"]'.format(technologyTag, stubTechnology)
            else:
                rule_parent = subsect

            # interp_rule = rule_parent + '/interpolation-rule'
            # prefix = interp_rule + '/interpolation-rule[@apply-to="{}"]'.format(applyTo)
            interp_rule = rule_parent + '/interpolation-rule[@apply-to="{}"]'.format(applyTo)

            args += [(interp_rule + '/@from-year', fromYear),
                     (interp_rule + '/@to-year', toYear),
                     (interp_rule + '/interpolation-function/@name', funcName)]

            def set_or_insert_value(to_or_from_tag, value):
                # insert interpolation-rule if not present
                if not xmlSel(xmlFileAbs, interp_rule):
                    elt = ET.Element('interpolation-rule', attrib={'apply-to' : applyTo})
                    xmlIns(xmlFileAbs, rule_parent, elt)

                # insert interpolation-function if not present
                interp_func = interp_rule + '/interpolation-function'
                if not xmlSel(xmlFileAbs, interp_func):
                    elt = ET.Element('interpolation-function', attrib={'name' : funcName})
                    xmlIns(xmlFileAbs, interp_rule, elt)

                xpath = interp_rule + '/' + to_or_from_tag
                if xmlSel(xmlFileAbs, xpath):               # if element exists, edit it in place
                    args.append((xpath, value))
                else:                                       # otherwise, insert the element
                    elt = ET.Element(to_or_from_tag)
                    elt.text = value
                    xmlIns(xmlFileAbs, interp_rule, elt)

            if fromValue is not None:
                fromValue = str(fromValue)
                set_or_insert_value('from-value', fromValue)

            if toValue is not None:
                toValue = str(toValue)
                set_or_insert_value('to-value', toValue)

                # Check if a share-weight node exists for the toYear; if so, set the value.
                # If not insert a new element for this year before the interpolation rule.
                # For techs, the share-weight appears inside the <period year="xxx"> element,
                # but for subsectors, the year is an attribute, i.e., <share-weight year="xxx">
                if stubTechnology:
                    share_parent = rule_parent + '/period[@year="{}"]'.format(toYear)
                    share_weight = share_parent + '/share-weight'

                else: # subsector level
                    share_parent = rule_parent
                    share_weight = share_parent + '/share-weight[@year="{}"]'.format(toYear)

                share_elt = tree.find(share_weight)

                if share_elt is None:
                    interp_rule_elt = tree.find(interp_rule)
                    rule_parent_elt = tree.find(rule_parent)
                    index = rule_parent_elt.index(interp_rule_elt)

                    attrib = {} if stubTechnology else {'year' : toYear}
                    share_elt = ET.Element('share-weight', attrib=attrib)

                    # insert <share-weight> before <interpolation-rule>
                    share_parent_elt = tree.find(share_parent)
                    share_parent_elt.insert(index, share_elt)

                # Set the value for the toYear
                share_elt.text = toValue

            if delete:
                args.append((interp_rule + '/@delete', "1"))        # TBD: not sure this is correct

        xmlEdit(xmlFileAbs, args)

        self.updateScenarioComponent(configFileTag, xmlFileRel)

    @callableMethod
    def insertStubTechRetirement(self, regions, supplysector, subsector, stubTechnologies, type, steepness, years,
                        supplysectorTag='supplysector',
                        subsectorTag='subsector', technologyTag='stub-technology',  halflife=0, configFileTag=ENERGY_TRANSFORMATION_TAG):

        """
        Insert a parameter for a given region/supplysector/subsector/stub-technology/period.
        **Callable from XML setup files.**

        :param regions: (str or None) If a string, the GCAM region(s) to operate on. If None,
            the function is applied to all regions. Arg can be comma-delimited list of regions.
        :param supplysector: (str) the name of a supply sector
        :param supplysectorTag: (str) the tag for the supplysector level. Default is 'supplysector', but
            for electricity, this should be passed as supplysectorTag='pass-through-sector'
        :param subsectorTag: (str) the tag for the subsector level. Default is 'subsector', but
            for transportation, this should be passed as subsectorTag='tranSubsector'
        :param subsector: (str) the name of a sub-sector
         :param stubTechnologies: (str) the name of a technology to apply function to; if absent,
            the function is applied at the subsector level (optional)
        :param technologyTag: (str) the tag for the technology level. Default is 'stub-technology', but for
            certain sectors it may be 'technology'
        :param type: (str) defines the type of shutdown function. Can be either 'profit' or 's-curve'
        :param steepness: (float) defines the steepness value used in the function
        :param years: (string or int) the years to which to apply to the shutdown function
        :param halflife: (int or None) defines the halflife value to use. By default set to None, but s-curve shutdown
            deciders need a halflife value
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This determines which file is edited, so it must correspond to
           the indicated sector(s). Default is 'energy_transformation'.
        :return: none
        """
        _logger.info("Insert shutdown functions for (%r, %r, %r, %r) for %r",
                     regions, supplysector, subsector, stubTechnologies, self.name)

        xmlFileRel, xmlFileAbs = self.getLocalCopy(configFileTag)

        item = CachedFile.getFile(xmlFileAbs)
        tree = item.tree

        # convert to a list; if no region given, get list of regions in this file
        regionList = splitAndStrip(regions, ',') if regions else tree.xpath('//region/@name')
        stubTechList = splitAndStrip(stubTechnologies,',')
        yearList = splitAndStrip(years,',')
        if type == "profit":
            shutdownTypeDecider = "profit-shutdown-decider"
        else:
            shutdownTypeDecider="s-curve-shutdown-decider"

        args = []

        for region in regionList:
            regionElt = '//region[@name="{}"]'.format(region)

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/share-weight
            for stubTechnology in stubTechList:
                stubTech = '{}/{}[@name="{}"]/{}[@name="{}"]/{}[@name="{}"]'.format(regionElt, supplysectorTag, supplysector, subsectorTag,
                                                                    subsector,technologyTag,stubTechnology)
                for year in yearList:

                    period = stubTech + '/period[@year="{}"]'.format(year)
                    shutdown = period + '/{}[@name="{}"]'.format(shutdownTypeDecider, type)
                    steep = shutdown + '/steepness'
                    half_life = shutdown + '/half-life'
                    shutdownElement = ET.Element(str(shutdownTypeDecider), attrib={"name": str(type)})
                    steepnessElement = ET.SubElement(shutdownElement,"steepness")

                    if not xmlSel(xmlFileAbs, period):
                        periodElement = ET.Element('period', attrib={'year': str(year)})
                        xmlIns(xmlFileAbs, stubTech, periodElement)

                    if type != "profit":
                        halflifeElement = ET.SubElement(shutdownElement,"half-life")
                    xmlIns(xmlFileAbs, period, shutdownElement)
                    args.append((steep, coercible(steepness, float)))
                    if type != "profit":
                        args.append((half_life, coercible(halflife, float)))

        xmlEdit(xmlFileAbs, args)
        self.updateScenarioComponent(configFileTag, xmlFileRel)

    @callableMethod
    def insertStubTechParameter(self, regions, supplysector, subsector, stubTechnology, nodeName, attributeName,
                        attributeValue, nodeValues, supplysectorTag='supplysector',
                        subsectorTag='subsector', technologyTag='stub-technology',  configFileTag=ENERGY_TRANSFORMATION_TAG):

        """
        Insert a parameter for a given region/supplysector/subsector/stub-technology/period.
        **Callable from XML setup files.**

        :param regions: (str or None) If a string, the GCAM region(s) to operate on. If None,
            the function is applied to all regions. Arg can be comma-delimited list of regions.
        :param supplysector: (str) the name of a supply sector
        :param supplysectorTag: (str) the tag for the supplysector level. Default is 'supplysector', but
            for electricity, this should be passed as supplysectorTag='pass-through-sector'
        :param subsectorTag: (str) the tag for the subsector level. Default is 'subsector', but
            for transportation, this should be passed as subsectorTag='tranSubsector'
        :param subsector: (str) the name of a sub-sector
         :param stubTechnology: (str) the name of a technology to apply function to; if absent,
            the function is applied at the subsector level (optional)
        :param technologyTag: (str) the tag for the technology level. Default is 'stub-technology', but for
            certain sectors it may be 'technology'
        :param nodeName: (str) defines the name of the node to insert.
        :param attributeName: (str) defines any attributes that need to be added (e.g. @name) (optional)
        :param attributeValue: (str) defines any attributevalues that need to be added (e.g. name="coal") (optional)
        :param nodeValues: (dict-like or iterable of tuples of (year, nodeValue)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.items() after
            which the rest of the explanation above applies. The `nodeValue` can be
            anything coercible to float.
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This determines which file is edited, so it must correspond to
           the indicated sector(s). Default is 'energy_transformation'.
        :return: none
        """
        _logger.info("Insert nodes and attributes for (%r, %r, %r, %r) for %r",
                     regions, supplysector, subsector, stubTechnology, self.name)

        xmlFileRel, xmlFileAbs = self.getLocalCopy(configFileTag)

        item = CachedFile.getFile(xmlFileAbs)
        tree = item.tree

        # convert to a list; if no region given, get list of regions in this file
        regionList = splitAndStrip(regions, ',') if regions else tree.xpath('//region/@name')

        args = []

        for region in regionList:
            regionElt = '//region[@name="{}"]'.format(region)

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/share-weight
            subsect = '{}/{}[@name="{}"]/{}[@name="{}"]'.format(regionElt, supplysectorTag, supplysector, subsectorTag,
                                                                subsector)
            for year,value in expandYearRanges(nodeValues):

                stubTech = subsect + '/{}[@name="{}"]'.format(technologyTag, stubTechnology)
                param_parent = stubTech + '/period[@year="{}"]'.format(year)
                parameter = param_parent + '/{}[@{}="{}"]'.format(nodeName, attributeName, attributeValue)

                if not xmlSel(xmlFileAbs, parameter):
                    parameterElement = ET.Element(str(nodeName), {str(attributeName): str(attributeValue)})
                    xmlIns(xmlFileAbs, param_parent, parameterElement)

                args.append((parameter, coercible(value, float)))

        xmlEdit(xmlFileAbs, args)
        self.updateScenarioComponent(configFileTag, xmlFileRel)

    @callableMethod
    def insertSubsectorParameter(self, regions, supplysector, subsector, nodeName, attributeName,
                                 attributeValue, nodeValue, supplysectorTag='supplysector',
                                 subsectorTag='subsector', configFileTag=ENERGY_TRANSFORMATION_TAG):

        """
        Insert a parameter for a given region/supplysector/subsector/stub-technology/period.
        **Callable from XML setup files.**
        :param regions: (str or None) If a string, the GCAM region(s) to operate on. If None,
            the function is applied to all regions. Arg can be comma-delimited list of regions.
        :param supplysector: (str) the name of a supply sector
        :param supplysectorTag: (str) the tag for the supplysector level. Default is 'supplysector', but
            for electricity, this should be passed as supplysectorTag='pass-through-sector'
        :param subsectorTag: (str) the tag for the subsector level. Default is 'subsector', but
            for transportation, this should be passed as subsectorTag='tranSubsector'
        :param subsector: (str) the name of a sub-sector
        :param nodeName: (str) defines the name of the node to insert.
        :param attributeName: (str) defines any attributes that need to be added (e.g. @name) (optional)
        :param attributeValue: (str) defines any attributevalues that need to be added (e.g. name="coal") (optional)
        :param nodeValue: (string or float) values to insert into the node
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This determines which file is edited, so it must correspond to
           the indicated sector(s). Default is 'energy_transformation'.
        :return: none
        """
        from .utils import printSeries

        _logger.info("Insert nodes and attributes for (%r, %r, %r) for %r",
                     regions, supplysector, subsector, self.name)
        # _logger.info(printSeries(values, 'share-weights', asStr=True))

        xmlFileRel, xmlFileAbs = self.getLocalCopy(configFileTag)

        item = CachedFile.getFile(xmlFileAbs)
        tree = item.tree

        # convert to a list; if no region given, get list of regions in this file
        regionList = splitAndStrip(regions, ',') if regions else tree.xpath('//region/@name')

        args = []

        for region in regionList:
            regionElt = '//region[@name="{}"]'.format(region)

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/share-weight
            subsect = '{}/{}[@name="{}"]/{}[@name="{}"]'.format(regionElt, supplysectorTag, supplysector, subsectorTag,
                                                                subsector)
            parameter = subsect + '/{}[@{}="{}"]'.format(nodeName, attributeName, attributeValue)
            parameterElement = ET.Element(str(nodeName), {str(attributeName): str(attributeValue)})

            if not xmlSel(xmlFileAbs, parameter):
                parameterElement = ET.Element(str(nodeName), {str(attributeName): str(attributeValue)})
                xmlIns(xmlFileAbs, subsect, parameterElement)

            args.append((parameter, coercible(nodeValue, float)))

        xmlEdit(xmlFileAbs, args)
        self.updateScenarioComponent(configFileTag, xmlFileRel)

    @callableMethod
    def setRegionalShareWeights(self, regions, sector, subsector, values,
                                stubTechnology=None, supplysectorTag='supplysector', subsectorTag='subsector',
                                technologyTag='stub-technology', configFileTag=ENERGY_TRANSFORMATION_TAG):
        """
        Create a modified version of the indicated file (default is en_transformation.xml) with
        the given share-weights for `technology` in `sector` based on the data in `values`. Note
        that this function affects regional technology definitions only. To affect definitions in
        the global technology database, use the function setGlobalTechShareWeight (below).
        **Callable from XML setup files.**

        :param regions: if not None, changes are made in a specific region, or regions (a comma-delimited
            list of regions) otherwise (if None) they're made in all global GCAM regions.
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
        :param technologyTag: (str) the tag for the technology level. Default is 'stub-technology', but
            for certain sectors it may be 'technology'
        :param supplysectorTag: (str) the tag for the supplysector level. Default is 'supplysector', but
            for electricity, this should be passed as supplysectorTag='pass-through-sector'
        :param subsectorTag: (str) the tag for the subsector level. Default is 'subsector', but
            for transportation, this should be passed as subsectorTag='tranSubsector'
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file.
        :return: none
        """
        _logger.info("Set share-weights for (%r, %r, %r, %r) for %r",
                     regions, sector, subsector, stubTechnology, self.name)
        # _logger.info(printSeries(values, 'share-weights', asStr=True))

        xmlFileRel, xmlFileAbs = self.getLocalCopy(configFileTag)

        item = CachedFile.getFile(xmlFileAbs)
        tree = item.tree

        # convert to a list; if no regions given, get list of regions in this file
        regionList = splitAndStrip(regions, ',') if regions else tree.xpath('//region/@name')

        args = []

        for region in regionList:
            regionElt = '//region[@name="{}"]'.format(region)

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/share-weight
            subsect = '{}/{}[@name="{}"]/{}[@name="{}"]'.format(regionElt, supplysectorTag, sector, subsectorTag, subsector)

            for year, value in expandYearRanges(values):

                if stubTechnology:
                    stubTech = subsect + '/{}[@name="{}"]'.format(technologyTag, stubTechnology)
                    sw_parent = stubTech + '/period[@year="{}"]'.format(year)
                    share_weight = sw_parent + '/share-weight'

                    if not xmlSel(xmlFileAbs, sw_parent):
                        elt = ET.Element('period', attrib={'year': str(year)})
                        xmlIns(xmlFileAbs, stubTech, elt)

                else:  # subsector level
                    sw_parent = subsect
                    share_weight = sw_parent + '/share-weight[@year="{}"]'.format(year)

                if not xmlSel(xmlFileAbs, share_weight):
                    attrib = {} if stubTechnology else {'year': str(year)}
                    elt = ET.Element('share-weight', attrib=attrib)
                    xmlIns(xmlFileAbs, sw_parent, elt)

                args.append((share_weight, coercible(value, float)))

        xmlEdit(xmlFileAbs, args)
        self.updateScenarioComponent(configFileTag, xmlFileRel)

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
        _logger.info("Set global-technology-database share-weights for (%s, %s) to %s for %s",
                     sector, technology, values, self.name)

        enTransFileRel, enTransFileAbs = self.getLocalCopy(configFileTag)

        prefix = "//global-technology-database/location-info[@sector-name='{}' and @subsector-name='{}']/technology[@name='{}']".format(
                 sector, subsector, technology)

        pairs = []
        for year, value in expandYearRanges(values):
            pairs.append(("{}/period[@year={}]/share-weight".format(prefix, year), coercible(value, float)))

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
        _logger.info("Set coefficients for %s in global technology %s, subsector %s: %s",
                     energyInput, technology, subsector, values)

        enTransFileRel, enTransFileAbs = \
            self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)

        prefix = "//global-technology-database/location-info[@subsector-name='%s']/technology[@name='%s']" % \
                 (subsector, technology)
        suffix = "minicam-energy-input[@name='{}']/coefficient".format(energyInput)

        pairs = []
        for year, coef in expandYearRanges(values):
            pairs.append(("{}/period[@year='{}']/{}".format(prefix, year, suffix), coef))

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

    @callableMethod
    def setRegionalNonCO2Emissions(self, region, sector, subsector, stubTechnology, species, values,
                                 configFileTag="nonco2_energy"):
        """
        Create a modified version of all_energy_emissions.xml with the given values for
        for `technology` in `sector` based on the data in `values`.
        **Callable from XML setup files.**

        :param sector: (str) the name of a GCAM sector
        :param stubTechnology: (str) the name of a GCAM stub-technology in `sector`
        :param values: (dict-like or iterable of tuples of (year, shareWeight)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.items() after
            which the rest of the explanation above applies. The `shareWeight` can be
            anything coercible to float.
        :param species: (str) the name of the gas to set the emissions for
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. Default is "nonco2_energy" => all_energy_emissions.xml
        :return: none
        """
        _logger.info("Set Non-CO2 emissions for (%s, %s, %s, %s, %s) to %s for %s",
                     region, sector, subsector, stubTechnology, species, values, self.name)

        xmlFileRel, xmlFileAbs = self.getLocalCopy(configFileTag)

        # //region[@name='USA']/supplysector[@name='N fertilizer']/subsector[@name='gas']/stub-technology[@name='gas']/period[@year='2005']/Non-CO2[@name='CH4']/input-emissions
        xpath = "//region[@name='{region}']/supplysector[@name='{sector}']/subsector[@name='{subsector}']/stub-technology[@name='{stubTechnology}']/period[@year='%s']/Non-CO2[@name='{species}']/input-emissions".\
            format(region=region, sector=sector, subsector=subsector, stubTechnology=stubTechnology, species=species)

        pairs = []
        for year, value in expandYearRanges(values):
            pairs.append((xpath % year, coercible(value, float)))

        xmlEdit(xmlFileAbs, pairs)
        self.updateScenarioComponent(configFileTag, xmlFileRel)

    @callableMethod
    def transportTechEfficiency(self, csvFile, xmlTag='transportation'):
        import pandas as pd

        csvPath = pathjoin(getParam('GCAM.ProjectDir'), 'etc', csvFile)

        _logger.info("Called transportTechEfficiency('%s', '%s')", csvPath, xmlTag)
        df = pd.read_csv(csvPath)
        year_cols = [col for col in df.columns if col.isdigit()]

        xmlFileRel, xmlFileAbs = self.getLocalCopy(xmlTag)
        fileObj = CachedFile.getFile(xmlFileAbs)
        tree = fileObj.tree

        xml_template = "//region[@name='{region}']/supplysector[@name='{sector}']/tranSubsector[@name='{subsector}']/stub-technology[@name='{technology}']/"

        pairs = []

        for (idx, row) in df.iterrows():
            xpath_prefix = xml_template.format(**row)
            input = row['input']

            for year in year_cols:
                improvement = row[year]
                if improvement == 0:
                    continue

                xpath = xpath_prefix + "period[@year='{year}']/minicam-energy-input[@name='{input}']/coefficient".format(
                    year=year, input=input)
                elts = tree.xpath(xpath)

                if elts is None:
                    raise SetupException('XPath query {} on file "{}" failed to find an element'.format(xpath, xmlFileAbs))

                if len(elts) != 1:
                    raise SetupException(
                        'XPath query {} on file "{}" returned multiple elements'.format(xpath, xmlFileAbs))

                elt = elts[0]
                old_value = float(elt.text)
                # The coefficient in the XML file is in energy per output unit (e.g., vehicle-km or passenger-km).
                # A value of 1 in the CSV template, which indicates a 100% improvement (a doubling) of fuel economy,
                # should drop the coefficient value by 50%. Thus the following calculation:
                new_value = old_value / (1 + improvement)
                pairs.append((xpath, new_value))

        xmlEdit(xmlFileAbs, pairs)
        self.updateScenarioComponent(xmlTag, xmlFileRel)

    @callableMethod
    def buildingTechEfficiency(self, csvFile, xmlTag='building_update', xmlFile='building_tech_improvements.xml', mode="mult"):
        """
        Generate an XML file that implements building technology efficiency policies based on
        the CSV input file.

        :param csvFile: (str) The name of the file to read. The given argument is interpreted as
            relative to "{GCAM.ProjectDir}/etc/", but an absolute path can be provided to override
            this.
        :param xmlTag: (str) the tag in the config.xml file to use to find the relevant GCAM input
            XML file.
        :param xmlFile: (str) the name of the XML policy file to generate. The file is written to
            the "local-xml" dir for the current scenario, and it is added to the config.xml file.
        :param mode: (str) Must be "mult" (the default) or "add", controlling how CSV data are processed.
        :return: none
        """
        import pandas as pd

        csvPath = pathjoin(getParam('GCAM.ProjectDir'), 'etc', csvFile)

        _logger.info("Called buildingTechEfficiency('%s', '%s', '%s')", csvPath, xmlTag, xmlFile)

        df = pd.read_csv(csvPath)
        year_cols = [col for col in df.columns if col.isdigit()]

        changes = []

        if mode == 'mult':
            # We treat the improvement as the change in the "inefficiency coefficient",
            # best described by the algebra below...
            def compute(old, improvement, subsector):
                if subsector == 'electricity':
                    return old * (1 + improvement)

                inefficiency = (1 - old)
                coefficient = inefficiency / (1 + improvement)
                efficiency = 1 - coefficient
                return efficiency

        elif mode == 'add':
            def compute(old, improvement, tech):
                return old + improvement

        else:
            raise SetupException("buildingTechEfficiency: mode must be either 'add' or 'mult'; got '{}'".format(mode))

        def runForFile(tag, which):
            fileRel, fileAbs = self.getLocalCopy(tag)
            fileObj = CachedFile.getFile(fileAbs)
            tree = fileObj.tree

            if which == 'GCAM-USA':
                xml_template = "//global-technology-database/location-info[@sector-name='{sector}' and @subsector-name='{subsector}']/technology[@name='{technology}']/"
            else:
                xml_template = "//region[@name='{region}']/supplysector[@name='{sector}']/subsector[@name='{subsector}']/stub-technology[@name='{technology}']/"

            subdf = df.query('which == "{}"'.format(which))

            for (idx, row) in subdf.iterrows():
                xpath_prefix = xml_template.format(**row)
                input = row['input']
                subsector  = row['subsector']
                pairs = []

                for year in year_cols:
                    improvement = row[year]
                    if improvement == 0:
                        continue

                    xpath = xpath_prefix + "period[@year='{year}']/minicam-energy-input[@name='{input}']/efficiency".format(year=year, input=input)
                    elts = tree.xpath(xpath)

                    if elts is None:
                        raise SetupException('XPath query {} on file "{}" failed to find an element'.format(xpath, fileAbs))

                    if len(elts) != 1:
                        raise SetupException('XPath query {} on file "{}" returned multiple elements'.format(xpath, fileAbs))

                    elt = elts[0]
                    old_value = float(elt.text)
                    new_value = compute(old_value, improvement, subsector)
                    pairs.append((year, new_value))

                if pairs:
                    changes.append((row, pairs))

        which_values = set(df.which)

        if 'GCAM-32' in which_values:
            runForFile('building', 'GCAM-32')

        if 'GCAM-USA' in which_values:
            runForFile('bld_usa',  'GCAM-USA')

        xmlAbs = pathjoin(self.scenario_dir_abs, xmlFile)
        xmlRel = pathjoin(self.scenario_dir_rel, xmlFile)

        scenarioElt = ET.Element('scenario')
        worldElt = ET.SubElement(scenarioElt, 'world')

        # find or create the sub-element described
        def getSubElement(elt, tag, attr, value):
            xpath = './{}[@{}="{}"]'.format(tag, attr, value)
            subelt = elt.find(xpath)
            if subelt is None:
                subelt = ET.SubElement(elt, tag, attrib={attr : value})

            return subelt

        for (row, pairs) in changes:
            region  = row['region']
            sector  = row['sector']
            subsect = row['subsector']
            tech    = row['technology']
            input   = row['input']

            regionElt = getSubElement(worldElt, 'region', 'name', region)

            for (year, value) in pairs:
                sectorElt  = getSubElement(regionElt, 'supplysector', 'name', sector)
                subsectElt = getSubElement(sectorElt, 'subsector', 'name', subsect)
                techElt    = getSubElement(subsectElt, 'stub-technology', 'name', tech)
                periodElt  = getSubElement(techElt, 'period', 'year', year)
                inputElt   = getSubElement(periodElt, 'minicam-energy-input', 'name', input)
                efficElt   = ET.SubElement(inputElt, 'efficiency')
                efficElt.text = str(value)

        _logger.info("Writing building tech changes to '%s'", xmlAbs)
        tree = ET.ElementTree(scenarioElt)
        tree.write(xmlAbs, xml_declaration=True, encoding='utf-8', pretty_print=True)

        self.addScenarioComponent(xmlTag, xmlRel)

    @callableMethod
    def buildingElectrification(self, csvFile, xmlTag='building_electrification', xmlFile='building_electrification.xml'):
        """
        Generate a building electrification policy XML file and incorporate it into the scenario's config.xml.

        :param csvFile: (str) the name of the CSV template file to read. Relative paths are assumed relative
            to {GCAM.ProjectDir}/etc. Absolute paths override this.
        :param xmlTag: (str) a config file tag to use for the generated XML file.
        :param xmlFile: (str) the name of the generated XML file.
        :return:
        """
        from .buildingElectrification import generate_building_elec_xml

        csvPath = pathjoin(getParam('GCAM.ProjectDir'), 'etc', csvFile)
        _logger.info("Called buildingElectrification('%s', '%s', '%s')", csvPath, xmlTag, xmlFile)

        xmlAbs = pathjoin(self.scenario_dir_abs, xmlFile)
        xmlRel = pathjoin(self.scenario_dir_rel, xmlFile)

        generate_building_elec_xml(csvPath, xmlAbs)
        self.addScenarioComponent(xmlTag, xmlRel)


    @callableMethod
    def zevPolicy(self, csvFile, xmlTag='zev_policy', xmlFile='zev_policy.xml', transportTag='transportation', pMultiplier=1E9, outputRatio=1E-6):
        from .ZEVPolicy import generate_zev_xml

        csvPath = pathjoin(getParam('GCAM.ProjectDir'), 'etc', csvFile)
        _logger.info("Called zevPolicy('%s', '%s', '%s')", csvPath, xmlTag, xmlFile)

        xmlAbs = pathjoin(self.scenario_dir_abs, xmlFile)
        xmlRel = pathjoin(self.scenario_dir_rel, xmlFile)

        generate_zev_xml(self.scenario, csvPath, xmlAbs, transportTag, pMultiplier, outputRatio)
        self.addScenarioComponent(xmlTag, xmlRel)

    @callableMethod
    def industryTechEfficiency(self, csvFile, xmlTag='industry_update', xmlFile='industry_tech_improvements.xml', mode="mult"):
        """
        Generate an XML file that implements industry technology efficiency policies based on
        the CSV input file.

        :param csvFile: (str) The name of the file to read. The given argument is interpreted as
            relative to "{GCAM.ProjectDir}/etc/", but an absolute path can be provided to override
            this.
        :param xmlTag: (str) the tag in the config.xml file to use to find the relevant GCAM input
            XML file.
        :param xmlFile: (str) the name of the XML policy file to generate. The file is written to
            the "local-xml" dir for the current scenario, and it is added to the config.xml file.
        :param mode: (str) Must be "mult" (the default) or "add", controlling how CSV data are processed.
        :return: none
        """
        import pandas as pd

        csvPath = pathjoin(getParam('GCAM.ProjectDir'), 'etc', csvFile)

        _logger.info("Called industryTechEfficiency('%s', '%s', '%s')", csvPath, xmlTag, xmlFile)

        df = pd.read_csv(csvPath)
        year_cols = [col for col in df.columns if col.isdigit()]

        changes = []

        if mode == 'mult':
            # We treat the improvement as the change in the "inefficiency coefficient",
            # best described by the algebra below...
            def compute(old, improvement, subsector):
                if subsector == 'electricity':
                    return old * (1 + improvement)

                inefficiency = (1 - old)
                coefficient = inefficiency / (1 + improvement)
                efficiency = 1 - coefficient
                return efficiency

        elif mode == 'add':
            def compute(old, improvement, tech):
                return old + improvement

        else:
            raise SetupException("industryTechEfficiency: mode must be either 'add' or 'mult'; got '{}'".format(mode))

        def runForFile(tag, which):
            fileRel, fileAbs = self.getLocalCopy(tag)
            fileObj = CachedFile.getFile(fileAbs)
            tree = fileObj.tree
            xml_template = "//global-technology-database/location-info[@sector-name='{sector}' and @subsector-name='{subsector}']/technology[@name='{technology}']/"
#            if which == 'GCAM-USA':
#                xml_template = "//global-technology-database/location-info[@sector-name='{sector}' and @subsector-name='{subsector}']/technology[@name='{technology}']/"
#            else:
#                xml_template = "//region[@name='{region}']/supplysector[@name='{sector}']/subsector[@name='{subsector}']/stub-technology[@name='{technology}']/"

            subdf = df.query('which == "{}"'.format(which))

            for (idx, row) in subdf.iterrows():
                xpath_prefix = xml_template.format(**row)
                input = row['input']
                subsector  = row['subsector']
                pairs = []

                for year in year_cols:
                    improvement = row[year]
                    if improvement == 0:
                        continue

                    xpath = xpath_prefix + "period[@year='{year}']/minicam-energy-input[@name='{input}']/efficiency".format(year=year, input=input)
                    elts = tree.xpath(xpath)

                    if elts is None:
                        raise SetupException('XPath query {} on file "{}" failed to find an element'.format(xpath, fileAbs))

                    if len(elts) == 0:
                        raise SetupException('XPath query {} on file "{}" returned zero elements'.format(xpath, fileAbs))

                    if len(elts) != 1:
                        raise SetupException('XPath query {} on file "{}" returned multiple elements'.format(xpath, fileAbs))

                    elt = elts[0]
                    old_value = float(elt.text)
                    new_value = compute(old_value, improvement, subsector)
                    pairs.append((year, new_value))

                if pairs:
                    changes.append((row, pairs))

        which_values = set(df.which)

        if 'GCAM-32' in which_values:
            runForFile('industry', 'GCAM-32')

        if 'GCAM-USA' in which_values:
            runForFile('industry',  'GCAM-USA')

        xmlAbs = pathjoin(self.scenario_dir_abs, xmlFile)
        xmlRel = pathjoin(self.scenario_dir_rel, xmlFile)

        scenarioElt = ET.Element('scenario')
        worldElt = ET.SubElement(scenarioElt, 'world')

        # find or create the sub-element described
        def getSubElement(elt, tag, attr, value):
            xpath = './{}[@{}="{}"]'.format(tag, attr, value)
            subelt = elt.find(xpath)
            if subelt is None:
                subelt = ET.SubElement(elt, tag, attrib={attr : value})

            return subelt

        for (row, pairs) in changes:
            region  = row['region']
            sector  = row['sector']
            subsect = row['subsector']
            tech    = row['technology']
            input   = row['input']

            regionElt = getSubElement(worldElt, 'region', 'name', region)

            for (year, value) in pairs:
                sectorElt  = getSubElement(regionElt, 'supplysector', 'name', sector)
                subsectElt = getSubElement(sectorElt, 'subsector', 'name', subsect)
                techElt    = getSubElement(subsectElt, 'stub-technology', 'name', tech)
                periodElt  = getSubElement(techElt, 'period', 'year', year)
                inputElt   = getSubElement(periodElt, 'minicam-energy-input', 'name', input)
                efficElt   = ET.SubElement(inputElt, 'efficiency')
                efficElt.text = str(value)

        _logger.info("Writing industry tech changes to '%s'", xmlAbs)
        tree = ET.ElementTree(scenarioElt)
        tree.write(xmlAbs, xml_declaration=True, encoding='utf-8', pretty_print=True)

        self.addScenarioComponent(xmlTag, xmlRel)
