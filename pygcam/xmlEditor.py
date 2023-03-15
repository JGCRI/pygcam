"""
.. Copyright (c) 2016-2023 Richard Plevin

   See the https://opensource.org/licenses/MIT for license details.
"""
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
import shutil
from lxml import etree as ET

from .config import getParam, getParamAsBoolean, unixPath, pathjoin, mkdirs
from .constants import LOCAL_XML_NAME, DYN_XML_NAME, CONFIG_XML, McsMode
from .error import SetupException, PygcamException
from .file_utils import (pushd, symlinkOrCopyFile, removeTreeSafely,
                         removeFileOrTree, copyIfMissing)
from .log import getLogger
from .mcs.mcsSandbox import McsSandbox
from .policy import (policyMarketXml, policyConstraintsXml, DEFAULT_MARKET_TYPE,
                     DEFAULT_POLICY_ELT, DEFAULT_POLICY_TYPE)
from .sandbox import makeDirPath, gcam_path, GcamPath, Sandbox
from .utils import (coercible, printSeries, splitAndStrip, getRegionList)
from .xml_edit import CachedFile, xmlSel, xmlIns, xmlEdit, expandYearRanges

_logger = getLogger(__name__)

# Names of key scenario components in reference GCAM 4.3 configuration.xml file
ENERGY_TRANSFORMATION_TAG = "energy_transformation"
SOLVER_TAG = "solver"

# methods callable from <function name="x">args</function> in
# XML scenario setup scripts.
CallableMethods = {}

# decorator to identify callable methods
def callableMethod(func):
    CallableMethods[func.__name__] = func
    return func

def getCallableMethod(name):
    return CallableMethods.get(name)


class XMLEditor(object):
    """
    Base class for scenario setup. Custom scenario processing classes must
    subclass this. Represents the information required to set up a scenario, i.e.,
    to generate and/or copy the required XML files into the XML output dir.
    """

    # TBD: init should take a Sandbox describing the scenario and assoc'd dirs. For now,
    #   we create the Sandbox object here to avoid having to change all subclasses.
    #   ----
    #   def __init__(self, sbx, mcsMode=None, cleanXML=True):

    def __init__(self, baseline, scenario, xmlOutputRoot, xmlSourceDir, refWorkspace,
                 groupDir, srcGroupDir, subdir, parent=None, mcsMode=None, cleanXML=True):

        # TBD: eventually sbx will be an arg to __init__()
        sbx_class = Sandbox if mcsMode is None else McsSandbox
        sbx = sbx_class(baseline, scenario, refWorkspace=refWorkspace,
                        scenarioGroup=groupDir, useGroupDir=True, # TBD: useGroupDir?
                        projectName=None, projectXmlsrc=xmlSourceDir,
                        createDirs=True)

        self.name = name = scenario or baseline # if no scenario stated, assume baseline
        self.baseline = baseline
        self.scenario = scenario
        self.xmlOutputRoot = xmlOutputRoot
        self.refWorkspace = refWorkspace
        self.xmlSourceDir = xmlSourceDir
        self.sandboxExeDir = pathjoin(getParam('GCAM.SandboxWorkspace'), 'exe')
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
        self.local_xml_abs = makeDirPath(xmlOutputRoot, LOCAL_XML_NAME, create=create)
        self.dyn_xml_abs   = makeDirPath(xmlOutputRoot, DYN_XML_NAME, create=create)   # TBD eliminate

        self.local_xml_rel = pathjoin("..", LOCAL_XML_NAME)
        self.dyn_xml_rel   = pathjoin("..", DYN_XML_NAME)   # TBD eliminate?

        self.trial_xml_rel = self.trial_xml_abs = None      # used by MCS only TBD: use GcamPath

        self.scenario_dir_abs = makeDirPath(self.local_xml_abs, groupDir, name, create=True)
        self.scenario_dir_rel = pathjoin(self.local_xml_rel, groupDir, name)

        # Get baseline from ScenarioGroup and use ScenarioInfo API to get this type of info
        self.baseline_dir_rel = pathjoin(self.local_xml_rel, groupDir, self.parent.name) if self.parent else None

        # TBD eliminate
        self.scenario_dyn_dir_abs = makeDirPath(self.dyn_xml_abs, groupDir, name, create=True)
        self.scenario_dyn_dir_rel = pathjoin(self.dyn_xml_rel, groupDir, name)

        # Store commonly-used paths
        gcam_xml = 'input/gcamdata/xml'
        self.gcam_prefix_abs = pathjoin(refWorkspace, gcam_xml)
        self.gcam_prefix_rel = pathjoin('../', gcam_xml)

        # TBD: self.gcam_prefix = GcamPath(ctx.refExeDir, '../input/gcamdata/xml')

        # TBD: add climate and policy subdirs?
        self.solution_prefix_abs = pathjoin(refWorkspace, "input", "solution")
        self.solution_prefix_rel = pathjoin("..", "input", "solution")
        # TBD: self.solution_prefix = GcamPath(ctx.refExeDir, '../input/solution')

        # Remove stale files from local-xml folder for scenarios, but avoiding doing
        # this when an XmlEditor is created for the baseline to run a non-baseline,
        # which is identified by scenario being None. Skip this in MCS trial mode:
        # config files are generated by gensim and re-used for each trial.
        if cleanXML and scenario and self.mcsMode != McsMode.TRIAL:
            with pushd(self.scenario_dir_abs):
                files = glob.glob('*')
                if files:
                    _logger.debug("Deleting old files from %s: %s", self.scenario_dir_abs, files)
                    for name in files:
                        removeFileOrTree(name)

    def setupDynamic(self, args):
        """
        Create dynamic XML files in dyn-xml. These files are generated for policy
        scenarios when XML file contents must be computed from baseline results.

        :param args: (argparse.Namespace) arguments passed from the top-level call
            to setup sub-command
        :return: none
        """

        _logger.info("Generating dyn-xml for scenario %s", self.name)

        # Delete old generated scenario files and recreate the directory
        dynDir = self.scenario_dyn_dir_abs
        removeTreeSafely(dynDir)
        mkdirs(dynDir)

        scenDir = self.scenario_dir_abs
        xmlFiles = glob.glob(f"{scenDir}/*.xml")

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

        CachedFile.decacheAll()     # TBD: this shouldn't be necessary

    def setupStatic(self, args):
        """
        Create static XML files in local-xml. By "static", we mean files whose contents are
        constant, independent of baseline results. In comparison, policy scenarios may generate
        dynamic XML files whose contents are computed from baseline results. While static XML
        files can be shared across trials in an MCS, dynamic XMLs are distinct by trial.

        :param args: (argparse.Namespace) arguments passed from the top-level call to setup
            sub-command.
        :return: none
        """
        _logger.info("Generating %s for scenario %s", LOCAL_XML_NAME, self.name)

        scenDir = self.scenario_dir_abs
        mkdirs(scenDir)

        topDir = pathjoin(self.xmlSourceDir, self.srcGroupDir, self.subdir or self.name)
        xmlFiles = glob.glob(f"{topDir}/*.xml")

        if xmlFiles:
            _logger.info(f"Copy {len(xmlFiles)} static XML files from {topDir} to {scenDir}")
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

        # For the following configuration file settings, no action is taken when value is None
        if args.stopYear is not None:
            self.setStopYear(args.stopYear)

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

    def cfgPath(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        if not self.configPath:
            # compute the first time, then cache it
            self.configPath = pathjoin(self.scenario_dir_abs, CONFIG_XML, realpath=True)

        return self.configPath

    def cachedConfig(self, edited=None):
        path = self.cfgPath()
        item = CachedFile.getFile(path)

        if edited is not None:
            item.edited = edited

        return item

    def componentPath(self, tag, configPath=None):
        configPath = configPath or self.cfgPath()
        pathname = xmlSel(configPath, f'//Value[@name="{tag}"]', asText=True)

        if pathname is None:
            raise PygcamException(f"Failed to find scenario component with tag '{tag}' in {configPath}")

        return pathname

    def getLocalCopy(self, configTag, gp=None):
        """
        Get the filename for the most local version (in terms of scenario hierarchy)
        of the XML file identified in the configuration file with ``configTag``, and
        copy the file to our scenario dir if not already there. This is generally the
        first step in the XMLEditor methods that modify XML file content.

        :param configTag: (str) the configuration file tag (name="xxx") of an XML file
        :param gp: (bool) whether to return the result as a GcamPath instance. If false,
            (the default) return a tuple of the relative and absolute pathnames.
        :return: (GcamPath) a GcamPath instance
        """
        sbx = self.sandbox

        pathname = self.componentPath(configTag)
        srcAbsPath = pathjoin(self.sandboxExeDir, pathname, abspath=True)

        srcPath = GcamPath(sbx.sandbox_exe_dir, pathname)     # TBD: compare to above

        if not srcPath.lexists():
            pass

        # TBD: test this
        if not os.path.lexists(srcAbsPath):
            _logger.debug("Didn't find %s; checking reference files", srcAbsPath)
            # look to sandbox workspace if not found locally
            sboxWorkspace = getParam('GCAM.SandboxWorkspace')
            refConfigFile = getParam('GCAM.RefConfigFile')  # main RefWorkspace, not SandboxWorkspace

            assert sbx.ref_workspace == sboxWorkspace        # TBD: remove after testing

            pathname = self.componentPath(configTag, configPath=refConfigFile)
            srcAbsPath = pathjoin(sboxWorkspace, 'exe', pathname, abspath=True)

            srcPath = GcamPath(sbx.sandbox_workspace_exe_dir, pathname)

        suffix = os.path.basename(srcAbsPath)
        suffix2 = srcPath.basename()
        assert suffix == suffix2    # TBD: remove after testing


        dstAbsPath = pathjoin(self.scenario_dir_abs, suffix)
        dstRelPath = pathjoin(self.scenario_dir_rel, suffix)

        # copyIfMissing(sbx.scenario_dir.abs, dstAbsPath, makedirs=True)
        copyIfMissing(srcAbsPath, dstAbsPath, makedirs=True)

        return GcamPath(self.sandboxExeDir, pathname)

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
        # use GcamPath
        xmlFile = self.getLocalCopy(tag, gp=True)
        xmlEdit(xmlFile, [(xpath, str(value))])
        self.updateScenarioComponent(tag, xmlFile)

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
        textArgs = f"name='{name}'"
        if writeOutput is not None:
            textArgs += " write-output='%d'" % (int(writeOutput))
        if appendScenarioName is not None:
            textArgs += " append-scenario-name='%d'" % (int(appendScenarioName))

        _logger.debug("Update <%s><Value %s>%s</Value>", group, textArgs, '...' if value is None else value)

        item = self.cachedConfig()

        prefix = f"//{group}/Value[@name='{name}']"
        pairs = []

        if value is not None:
            pairs.append((prefix, value))

        if writeOutput is not None:
            pairs.append((prefix + "/@write-output", int(writeOutput)))

        if appendScenarioName is not None:
            pairs.append((prefix + "/@append-scenario-name", int(appendScenarioName)))

        xmlEdit(item, pairs)

    @callableMethod
    def setClimateOutputInterval(self, years):
        """
        Sets the frequency at which climate-related outputs are
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
        item = self.cachedConfig(edited=True)

        _logger.info("stringReplace('%s', '%s', '%s')", xpath, oldstr, newstr)

        nodes = item.tree.xpath(xpath)
        if nodes is None:
            raise SetupException(f"stringReplace: No config elements match xpath '{xpath}'")

        for node in nodes:
            node.text = node.text.replace(oldstr, newstr)

    @callableMethod
    def setConfigValue(self, section, name, value):
        """
        Set the value of the item with `name` in `section` to the given `value`. Numeric
        values are converted to strings automatically.

        :param section: (str) the name of a section in the configuration.xml file,
            e.g., "Strings", "Bools", "Ints", etc.
        :param name: (str) the name of the attribute on the element to change
        :param value: the new value to set for the identified element
        :return: none
        """
        item = self.cachedConfig(edited=True)

        _logger.info("setConfigValue('%s', '%s', '%s')", section, name, value)

        xpath = f'//{section}/Value[@name="{name}"]'

        elt = item.tree.find(xpath)
        if elt is None:
            raise SetupException(f"setConfigValue: No config elements match xpath '{xpath}'")

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

        xmlfile = gcam_path(xmlfile, abs=False)
        xmlfile = unixPath(xmlfile) # TBD: not needed after converting all to GcamPath

        _logger.info("Add ScenarioComponent name='%s', xmlfile='%s'", name, xmlfile)

        item = self.cachedConfig(edited=True)
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

        xmlfile = gcam_path(xmlfile, abs=False)
        xmlfile = unixPath(xmlfile) # TBD: not needed after converting all to GcamPath

        _logger.info("Insert ScenarioComponent name='%s', xmlfile='%s' after value '%s'", name, xmlfile, after)

        item = self.cachedConfig(edited=True)
        elt = item.tree.find('//ScenarioComponents')
        afterNode = elt.find('Value[@name="%s"]' % after)
        if afterNode is None:
            raise SetupException(f"Can't insert {name} after {after}, as the latter doesn't exist")

        index = elt.index(afterNode) + 1

        node = ET.Element('Value')
        node.set('name', name)
        node.text = xmlfile
        elt.insert(index, node)

    # TBD: if xmlfile is GcamPath use rel_path
    def updateScenarioComponent(self, name, xmlfile):
        """
        Set a new filename for a ScenarioComponent identified by the ``<Value>`` element name.

        :param name: (str) the name of the scenario component to update
        :param xmlfile: (str) the location of the XML file, relative to the `exe` directory, that
           should replace the existing value
        :return: none
        """
        xmlfile = gcam_path(xmlfile, abs=False)
        xmlfile = unixPath(xmlfile) # TBD: not needed after converting all to GcamPath

        _logger.info(f"Update scenario component name '{name}' to refer to '{xmlfile}'")
        self.updateConfigComponent('ScenarioComponents', name, xmlfile)

    def deleteScenarioComponent(self, name):
        """
        Delete a ``<ScenarioComponent>`` identified by the ``<Value>`` element name.

        :param name: (str) the name of the ScenarioComponent to delete
        :return: none
        """
        _logger.info("Delete ScenarioComponent name='%s' for scenario", name)
        item = self.cachedConfig()

        elt = item.tree.find("//ScenarioComponents")
        valueNode = elt.find(f"Value[@name='{name}']")
        if valueNode is not None:
            elt.remove(valueNode)
            item.setEdited()

    # Deprecated? Appears to be unused.
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
        xmlfile = gcam_path(xmlfile, abs=False)
        xmlfile = unixPath(xmlfile) # TBD: delete after switching to GcamPaths

        _logger.debug("Rename ScenarioComponent name='%s', xmlfile='%s'", name, xmlfile)
        item = self.cachedConfig()
        xmlEdit(item, [(f"//ScenarioComponents/Value[text()='{xmlfile.rel}']/@name", name)])

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

        xml_file = self.getLocalCopy(tag, gp=True)

        xmlEdit(xml_file, [(xpath, value)], op='multiply')
        self.updateScenarioComponent(tag, xml_file)

    @callableMethod
    def add(self, tag, xpath, value):
        """
        Run the `xpath` query on the XML file with `tag` in the config file, and
        replace all values found with the result of adding `value` to them.

        :param tag: (str) the tag identifying a scenario component
        :param xpath: (str) an XPath query to run against the file indicated by `tag`
        :param value: (float) a value to add to the results of the `xpath` query.
        :return: none
        """
        _logger.info(f"add: tag='{tag}', xpath='{xpath}', value={value}")

        xml_file = self.getLocalCopy(tag, gp=True)

        xmlEdit(xml_file, [(xpath, value)], op='add')
        self.updateScenarioComponent(tag, xml_file)

    # TBD dynamic keyword might still be useful if subdir e.g. local-xml/dynamic but
    #  policy file would be in local-xml anyway
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

        item = self.cachedConfig(edited=True)

        basename = target + '-' + policy	# e.g., biodiesel-subsidy

        policyTag     = target + "-policy"
        constraintTag = target + "-constraint"

        reldir = self.scenario_dyn_dir_rel if dynamic else self.scenario_dir_rel

        # TBD: Could look for file in scenario, but if not found, look in baseline, eliminating this flag
        policyReldir = self.baseline_dir_rel if baselinePolicy else reldir

        policyXML     = pathjoin(policyReldir, basename + ".xml") # TBD: "-market.xml" for symmetry?
        constraintXML = pathjoin(reldir, basename + "-constraint.xml")

        # See if element exists in config file (-Q => quiet; just report exit status)
        xpath = f'//ScenarioComponents/Value[@name="{policyTag}"]'

        # If we've already added files for policy/constraint on this target,
        # we replace the old values with new ones. Otherwise, we add them.
        addOrUpdate = self.updateScenarioComponent if xmlSel(item, xpath) else self.addScenarioComponent
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
        item = self.cachedConfig()

        policyTag     = target + "-" + policy
        constraintTag = target + "-constraint"

        # See if element exists in config file (-Q => quiet; just report exit status)
        xpath = f'//ScenarioComponents/Value[@name="{policyTag}"]'

        if xmlSel(item, xpath):
            # found it; delete the elements
            self.deleteScenarioComponent(policyTag)
            self.deleteScenarioComponent(constraintTag)

    # TBD: recent versions of GCAM allow stop-year to be set directly; simplify this
    @callableMethod
    def setStopPeriod(self, yearOrPeriod):
        raise PygcamException("The callableMethod 'setStopPeriod' is deprecated. Please use 'setStopYear' instead.")

    # Documentation in utils/source/util.cpp:
    #
    # Reconciliation between -period and -year uses the following rules:
    # - If year is not set then the period is used (even if it is -1 which indicates RUN_ALL_YEARS).
    # - If no model time is available, which may happen when running in batch mode, then
    #   Scenario::UNINITIALIZED_RUN_PERIODS is returned.
    # - If year is set but not a valid year then Scenario::UNINITIALIZED_RUN_PERIODS
    # - If only year is set then it will be converted to period using the model time and be used.
    # - If both are set the year will be converted to period and used but a warning will be issued if
    #   they are inconsistent.
    #
    @callableMethod
    def setStopYear(self, year):
        self.updateConfigComponent('Ints', 'stop-year', year)


    @callableMethod
    def setupSolver(self, solutionTolerance=None, broydenTolerance=None,
                    maxModelCalcs=None, maxIterations=None, year=2020):
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

        xml_file = self.getLocalCopy(SOLVER_TAG, gp=True)

        prefix = f"//scenario/user-configurable-solver[@year={year}]/"
        pairs = []

        if solutionTolerance:
            pairs.append((prefix + 'solution-tolerance', solutionTolerance))

        if broydenTolerance:
            pairs.append((prefix + 'broyden-solver-component/ftol', broydenTolerance))

        if maxModelCalcs:
            pairs.append((prefix + 'max-model-calcs', maxModelCalcs))

        if maxIterations:
            pairs.append((prefix + 'broyden-solver-component/max-iterations', maxIterations))

        xmlEdit(xml_file, pairs)

        self.updateScenarioComponent("solver", xml_file)

    @callableMethod
    def dropLandProtection(self, dropEmissions=True):
        self.deleteScenarioComponent("protected_land2")
        self.deleteScenarioComponent("protected_land3")

        if dropEmissions:
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
        :param unprotectFirst: (bool) whether to first remove all protection
            before applying new protections. Default is False.
        """
        from .landProtection import protectLand

        _logger.info("Protecting %d%% of land globally", int(fraction * 100))

        # NB: this code depends on these being the tags assigned to the land files
        # as is currently the case in XmlEditor.makeScenarioComponentsUnique()
        for num in [2, 3]:
            fileTag  = 'land' + str(num)
            landFile = self.getLocalCopy(fileTag, gp=True)

            protectLand(landFile.abs, landFile.abs, fraction, landClasses=landClasses,
                        otherArable=otherArable, regions=regions, unprotectFirst=unprotectFirst)
            self.updateScenarioComponent(fileTag, landFile)

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
                fileTag = f'{prefix}land{num}'
                landFile = self.getLocalCopy(fileTag, gp=True)

                landXmlFiles.append(landFile.abs)
                self.updateScenarioComponent(fileTag, landFile)

        # TBD: revisit this; it's a bit of a hack for Oct 16, 2019(?) deliverable
        scenarioFile = pathname = getParam('GCAM.LandProtectionXmlFile')
        if self.mcsMode == McsMode.TRIAL:
            basename = os.path.basename(pathname)
            scenario = self.scenario or self.baseline
            scenarioFile = unixPath(pathjoin(self.trial_xml_abs, LOCAL_XML_NAME,
                                             self.groupDir, scenario, basename))

        runProtectionScenario(scenarioName, scenarioFile=scenarioFile, inPlace=True,
                              xmlFiles=landXmlFiles, unprotectFirst=unprotectFirst)

    def getScenarioOrTrialDirs(self, subdir=''):
        dirRel = pathjoin(self.trial_xml_rel, subdir) if self.mcsMode == McsMode.TRIAL \
            else self.scenario_dir_rel

        dirAbs = pathjoin(self.trial_xml_abs, subdir) if self.mcsMode == McsMode.TRIAL \
            else self.scenario_dir_abs

        return dirRel, dirAbs

    @callableMethod
    def taxCarbon(self, value, startYear=2020, endYear=2100, timestep=5,
                  rate=0.05, regions=None, market='global'):
        """
        Generate an XML file defining a global carbon tax starting
        at `value` and increasing by `rate` annually. Generate values
        for the give `years`. The first year in `years` is assumed to be
        the year at which the tax starts at `value`. The generated file
        is named 'carbon-tax-{market}.xml' and is added to the configuration.
        **Callable from XML setup files.**

        :param value: (float) the initial value of the tax ($/tonne)
        :param startYear: (int) The first year in which to set carbon taxes.
        :param endYear: (int) The last year in which to set carbon taxes.
        :param timestep: (int) The time-step to use between start and end years.
            Default is 5 years.
        :param rate: (float) annual rate of increase. Default is 0.05.
        :param regions: (list(str)) the regions for which to create a C tax market.
             Default is all defined GCAM regions.
        :param market: (str) the name of the market to create. Default is 'global'.
        :return: none
        """
        from .carbonTax import genCarbonTaxFile

        tag = 'carbon-tax-' + market
        filename = tag + '.xml'

        # TBD: use GcamPath
        # TBD: need to generalize this since any modification can be per-trial or universal
        dirRel, dirAbs = self.getScenarioOrTrialDirs(subdir=LOCAL_XML_NAME)

        fileRel = pathjoin(dirRel, filename)
        fileAbs = pathjoin(dirAbs, filename)

        genCarbonTaxFile(fileAbs, value, startYear=startYear, endYear=endYear,
                         timestep=timestep, rate=rate, regions=regions, market=market)
        self.addScenarioComponent(tag, fileRel)

    @callableMethod
    def taxBioCarbon(self, market='global', regions=None, forTax=True, forCap=False):
        """
        Create the XML for a linked policy to include LUC CO2 in a CO2 cap or tax policy (or both).
        This function generates the equivalent of the 4 files in input/policy/:
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

        # TBD: use GcamPath
        # TBD: need to generalize this since any modification can be per-trial or universal
        dirRel, dirAbs = self.getScenarioOrTrialDirs(subdir=LOCAL_XML_NAME)

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
        xml_file = self.getLocalCopy(tag, gp=True)

        prefix = f'//region[@name="{region}"]/demographics/populationMiniCAM'
        pairs = []
        for year, pop in expandYearRanges(values):
            pairs.append((f'{prefix}[@year="{year}"]/totalPop', int(round(pop))))

        xmlEdit(xml_file, pairs)
        self.updateScenarioComponent(tag, xml_file)

    @callableMethod
    def freezeRegionPopulation(self, region, year, endYear=2100):
        """
        Freeze population after `year` at the value for that year.
        """
        tag = 'socioeconomics'
        xml_file = self.getLocalCopy(tag, gp=True)

        item = CachedFile.getFile(xml_file)
        tree = item.tree

        xpath = f'//region[@name="{region}"]/demographics/populationMiniCAM[@year="{year}"]/totalPop'
        popNode = tree.find(xpath)
        population = popNode.text

        _logger.info("Freezing pop in %s to %s value of %s", region, year, population)
        values = [(y, population) for y in range(year+5, endYear+1, 5)]

        self.setRegionPopulation(region, values)

    @callableMethod
    def freezeGlobalPopulation(self, year, endYear=2100):
        for region in getRegionList():
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
        msg = f"Set non-energy-cost of {technology} for {self.name} to:"
        _logger.info(printSeries(values, technology, header=msg, asStr=True))

        xml_file = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG, gp=True)

        prefix = '//global-technology-database/location-info[@sector-name="%s" and @subsector-name="%s"]/technology[@name="%s"]' % \
                 (sector, subsector, technology)
        suffix = '/minicam-non-energy-input[@name="non-energy"]/input-cost'

        pairs = [(f'{prefix}/period[@year="{year}"]{suffix}', price) for year, price in expandYearRanges(values)]

        xmlEdit(xml_file, pairs)
        self.updateScenarioComponent(ENERGY_TRANSFORMATION_TAG, xml_file)

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

        xml_file = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG, gp=True)

        prefix = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                 (sector, subsector, technology)

        pairs = [(f"{prefix}/period[@year='{year}']/phased-shutdown-decider/shutdown-rate", coercible(value, float))
                    for year, value in expandYearRanges(values)]

        xmlEdit(xml_file, pairs)
        self.updateScenarioComponent(ENERGY_TRANSFORMATION_TAG, xml_file)

    #
    # //region[@name=""]/energy-final-demand[@name=""]/price-elasticity[@year=""]
    #
    # names of energy-final-demand:
    # 'aglu-xml/demand_input.xml': "Exports_Meat", "FoodDemand_Crops", "FoodDemand_Meat", "NonFoodDemand_Crops",
    #                              "NonFoodDemand_Forest", "NonFoodDemand_Meat"
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
        :param sectors: (str or list of str) the name of a GCAM (demand) sector. In GCAM v4.3, this
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

        xml_file = self.getLocalCopy(configFileTag, gp=True)

        def listifyString(value, aliasForNone=None):
            if isinstance(value, str):
                value = [value]

            # Treat "global" as not restricting by region
            if aliasForNone and len(value) == 1 and value[0] == aliasForNone:
                return None

            return value

        def nameExpression(values):
            """
            Turn ['a', 'b'] into '@name="a" or @name="b"'
            """
            names = [f'@name="{v}"' for v in values]
            return ' or '.join(names)

        regions = listifyString(regions, aliasForNone='global')
        nameExpr = '[' + nameExpression(regions) + ']' if regions else ''
        regionExpr = '//region' + nameExpr

        prefix = regionExpr + f'/energy-final-demand[{nameExpression(sectors)}]'

        pairs = [(f'{prefix}/price-elasticity[@year="{year}"]', coercible(value, float))
                    for year, value in expandYearRanges(values)]

        xmlEdit(xml_file, pairs)
        self.updateScenarioComponent(configFileTag, xml_file)

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

        xml_file = self.getLocalCopy(configFileTag, gp=True)

        item = CachedFile.getFile(xml_file)
        tree = item.tree

        # convert to a list; if no regions given, get list of regions in this file
        regionList = splitAndStrip(regions, ',') if regions else tree.xpath('//region/@name')

        args = []

        for region in regionList:
            regionElt = f'//region[@name="{region}"]'

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/interpolation-rule
            subsect = f'{regionElt}/{supplysectorTag}[@name="{supplysector}"]/{subsectorTag}[@name="{subsector}"]'

            if stubTechnology:
                rule_parent = subsect + f'/{technologyTag}[@name="{stubTechnology}"]'
            else:
                rule_parent = subsect

            interp_rule = rule_parent + f'/interpolation-rule[@apply-to="{applyTo}"]'

            args += [(interp_rule + '/@from-year', fromYear),
                     (interp_rule + '/@to-year', toYear),
                     (interp_rule + '/interpolation-function/@name', funcName)]

            def set_or_insert_value(to_or_from_tag, value):
                # insert interpolation-rule if not present
                if not xmlSel(item, interp_rule):
                    elt = ET.Element('interpolation-rule', attrib={'apply-to' : applyTo})
                    xmlIns(item, rule_parent, elt)

                # insert interpolation-function if not present
                interp_func = interp_rule + '/interpolation-function'
                if not xmlSel(item, interp_func):
                    elt = ET.Element('interpolation-function', attrib={'name' : funcName})
                    xmlIns(item, interp_rule, elt)

                xpath = interp_rule + '/' + to_or_from_tag
                if xmlSel(item, xpath):               # if element exists, edit it in place
                    args.append((xpath, value))
                else:                                       # otherwise, insert the element
                    elt = ET.Element(to_or_from_tag)
                    elt.text = value
                    xmlIns(item, interp_rule, elt)

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
                    share_parent = rule_parent + f'/period[@year="{toYear}"]'
                    share_weight = share_parent + '/share-weight'

                else: # subsector level
                    share_parent = rule_parent
                    share_weight = share_parent + f'/share-weight[@year="{toYear}"]'

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

        xmlEdit(item, args)
        self.updateScenarioComponent(configFileTag, xml_file)

    @callableMethod
    def insertStubTechRetirement(self, regions, supplysector, subsector, stubTechnologies, type,
                                 steepness, years,supplysectorTag='supplysector',
                                 subsectorTag='subsector', technologyTag='stub-technology',
                                 halflife=0, configFileTag=ENERGY_TRANSFORMATION_TAG):
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
        :param halflife: (int or None) defines the halflife value to use. By default, set to None, but s-curve
            shutdown deciders need a halflife value
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This determines which file is edited, so it must correspond to
           the indicated sector(s). Default is 'energy_transformation'.
        :return: none
        """
        _logger.info("Insert shutdown functions for (%r, %r, %r, %r) for %r",
                     regions, supplysector, subsector, stubTechnologies, self.name)

        xml_file = self.getLocalCopy(configFileTag, gp=True)

        item = CachedFile.getFile(xml_file)
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
            regionElt = f'//region[@name="{region}"]'

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/share-weight
            for stubTechnology in stubTechList:
                stubTech = f'{regionElt}/{supplysectorTag}[@name="{supplysector}"]/{subsectorTag}[@name="{subsector}"]/{technologyTag}[@name="{stubTechnology}"]'

                for year in yearList:

                    period = stubTech + f'/period[@year="{year}"]'
                    shutdown = period + f'/{shutdownTypeDecider}[@name="{type}"]'
                    steep = shutdown + '/steepness'
                    half_life = shutdown + '/half-life'
                    shutdownElement = ET.Element(str(shutdownTypeDecider), attrib={"name": str(type)})
                    # steepnessElement = ET.SubElement(shutdownElement,"steepness")

                    if not xmlSel(item, period):
                        periodElement = ET.Element('period', attrib={'year': str(year)})
                        xmlIns(item, stubTech, periodElement)

                    # if type != "profit":
                    #     halflifeElement = ET.SubElement(shutdownElement,"half-life")

                    xmlIns(item, period, shutdownElement)
                    args.append((steep, coercible(steepness, float)))
                    if type != "profit":
                        args.append((half_life, coercible(halflife, float)))

        xmlEdit(item, args)
        self.updateScenarioComponent(configFileTag, xml_file)

    @callableMethod
    def insertStubTechParameter(self, regions, supplysector, subsector, stubTechnology, nodeName,
                                attributeName, attributeValue, nodeValues, supplysectorTag='supplysector',
                                subsectorTag='subsector', technologyTag='stub-technology',
                                configFileTag=ENERGY_TRANSFORMATION_TAG):
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

        xml_file = self.getLocalCopy(configFileTag, gp=True)

        item = CachedFile.getFile(xml_file)
        tree = item.tree

        # convert to a list; if no region given, get list of regions in this file
        regionList = splitAndStrip(regions, ',') if regions else tree.xpath('//region/@name')

        args = []

        for region in regionList:
            regionElt = f'//region[@name="{region}"]'

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/share-weight
            subsect = f'{regionElt}/{supplysectorTag}[@name="{supplysector}"]/{subsectorTag}[@name="{subsector}"]'
            for year, value in expandYearRanges(nodeValues):

                stubTech = subsect + f'/{technologyTag}[@name="{stubTechnology}"]'
                param_parent = stubTech + f'/period[@year="{year}"]'
                parameter = param_parent + f'/{nodeName}[@{attributeName}="{attributeValue}"]'

                if not xmlSel(item, parameter):
                    parameterElement = ET.Element(str(nodeName), {str(attributeName): str(attributeValue)})
                    xmlIns(item, param_parent, parameterElement)

                args.append((parameter, coercible(value, float)))

        xmlEdit(item, args)
        self.updateScenarioComponent(configFileTag, xml_file)

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
        :param attributeValue: (str) defines any attribute values that need to be added (e.g. name="coal") (optional)
        :param nodeValue: (string or float) values to insert into the node
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
            section of a config file. This determines which file is edited, so it must correspond to
            the indicated sector(s). Default is 'energy_transformation'.
        :return: none
        """

        _logger.info("Insert nodes and attributes for (%r, %r, %r) for %r",
                     regions, supplysector, subsector, self.name)
        # from .utils import printSeries
        # _logger.info(printSeries(values, 'share-weights', asStr=True))

        xml_file = self.getLocalCopy(configFileTag, gp=True)

        item = CachedFile.getFile(xml_file)
        tree = item.tree

        # convert to a list; if no region given, get list of regions in this file
        regionList = splitAndStrip(regions, ',') if regions else tree.xpath('//region/@name')

        args = []

        for region in regionList:
            regionElt = f'//region[@name="{region}"]'

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/share-weight
            subsect = f'{regionElt}/{supplysectorTag}[@name="{supplysector}"]/{subsectorTag}[@name="{subsector}"]'
            parameter = subsect + f'/{nodeName}[@{attributeName}="{attributeValue}"]'

            if not xmlSel(item, parameter):
                parameterElement = ET.Element(str(nodeName), {str(attributeName): str(attributeValue)})
                xmlIns(item, subsect, parameterElement)

            args.append((parameter, coercible(nodeValue, float)))

        xmlEdit(item, args)
        self.updateScenarioComponent(configFileTag, xml_file)

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

        xml_file = self.getLocalCopy(configFileTag, gp=True)

        item = CachedFile.getFile(xml_file)
        tree = item.tree

        # convert to a list; if no regions given, get list of regions in this file
        regionList = splitAndStrip(regions, ',') if regions else tree.xpath('//region/@name')

        args = []

        for region in regionList:
            regionElt = f'//region[@name="{region}"]'

            # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/share-weight
            subsect = f'{regionElt}/{supplysectorTag}[@name="{sector}"]/{subsectorTag}[@name="{subsector}"]'

            for year, value in expandYearRanges(values):

                if stubTechnology:
                    stubTech = subsect + f'/{technologyTag}[@name="{stubTechnology}"]'
                    sw_parent = stubTech + f'/period[@year="{year}"]'
                    share_weight = sw_parent + '/share-weight'

                    if not xmlSel(item, sw_parent):
                        elt = ET.Element('period', attrib={'year': str(year)})
                        xmlIns(item, stubTech, elt)

                else:  # subsector level
                    sw_parent = subsect
                    share_weight = sw_parent + f'/share-weight[@year="{year}"]'

                if not xmlSel(item, share_weight):
                    attrib = {} if stubTechnology else {'year': str(year)}
                    elt = ET.Element('share-weight', attrib=attrib)
                    xmlIns(item, sw_parent, elt)

                args.append((share_weight, coercible(value, float)))

        xmlEdit(item, args)
        self.updateScenarioComponent(configFileTag, xml_file)

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
        :param xmlBasename: (str) the name of the xml file in the energy-xml folder to edit.
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This must match `xmlBasename`.
        :return: none
        """
        _logger.info("Set global-technology-database share-weights for (%s, %s) to %s for %s",
                     sector, technology, values, self.name)

        xml_file = self.getLocalCopy(configFileTag, gp=True)

        prefix = f"//global-technology-database/location-info[@sector-name='{sector}' and @subsector-name='{subsector}']/technology[@name='{technology}']"

        pairs = [(f"{prefix}/period[@year={year}]/share-weight", coercible(value, float))
                 for year, value in expandYearRanges(values)]

        xmlEdit(xml_file, pairs)
        self.updateScenarioComponent(configFileTag, xml_file)

    # TBD: test
    @callableMethod
    def setEnergyTechnologyCoefficients(self, subsector, technology, energyInput, values):
        """
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
        """
        _logger.info("Set coefficients for %s in global technology %s, subsector %s: %s",
                     energyInput, technology, subsector, values)

        xml_file = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG, gp=True)

        prefix = f"//global-technology-database/location-info[@subsector-name='{subsector}']/technology[@name='{technology}']"
        suffix = f"minicam-energy-input[@name='{energyInput}']/coefficient"

        pairs = [(f"{prefix}/period[@year='{year}']/{suffix}", coef) for year, coef in expandYearRanges(values)]

        xmlEdit(xml_file, pairs)
        self.updateScenarioComponent("energy_transformation", xml_file)

    @callableMethod
    def writePolicyMarketFile(self, filename, policyName, region, sector, subsector, technology, years,
                              marketType=DEFAULT_MARKET_TYPE):
        pathname = pathjoin(self.scenario_dir_abs, filename)        # TBD: pathjoin(self.sandbox.scenario_dir.abs, filename)
        policyMarketXml(policyName, region, sector, subsector, technology, years,
                        marketType=marketType, pathname=pathname)


    # class variable used by next method only
    _writePolicyConstraintFile_cache = {}

    @callableMethod
    def writePolicyConstraintFile(self, filename, policyName, region, targets, market=None, minPrice=None,
                                  policyElement=DEFAULT_POLICY_ELT, policyType=DEFAULT_POLICY_TYPE,
                                  csvPath=None, scenario=None):
        """
        Generate XML constraint file from the parameters given.

        :param filename: (str) the name of the XML file to create in the local-xml/{scenario} directory.
        :param policyName: (str) the name of the policy, i.e., <policy-portfolio-standard name="{policyName}">
        :param region: (str) the region to on which apply to the constraints
        :param targets: iterable of (year, value) pairs, where year can be an int or a string of the
            form "y1-y2" indicating a year range sharing the same value.
        :param market: (str) the name of the market; default is the region name
        :param minPrice: (int or float) if not None, a <min-price> element is created with the value, using
            the first year in `targets` and fillout="1".
        :param policyElement: (str) Defaults to "policy-portfolio-standard"
        :param policyType: (str) Either "subsidy" or "tax"
        :param csvPath: (str with pathname) the path to a file containing a 'Scenario' column and year
            columns with constraint values. Used to construct `targets` only if `targets` is None.
        :param scenario: (str) the name of the scenario to extract from the `csvFile`. Used only if
            `targets` is None.
        :return: none
        """
        pathname = pathjoin(self.scenario_dir_abs, filename)

        if targets:
            targets = expandYearRanges(targets)

        elif csvPath and scenario:
            # extract the constraints from the CSV file
            import pandas as pd

            # check cache for data
            df = self._writePolicyConstraintFile_cache.get(csvPath)

            if df is None:
                df = pd.read_csv(csvPath)

                if 'Scenario' not in df.columns:
                    raise SetupException(f"writePolicyConstraintFile: {csvPath} does not contain a 'Scenario' column")

                df.set_index('Scenario', inplace=True)

                self._writePolicyConstraintFile_cache[csvPath] = df     # save processed dataframe to cache

            try:
                row = df.loc[scenario]
            except KeyError:
                raise SetupException(f"writePolicyConstraintFile: {csvPath} does not contain scenario '{scenario}'")

            targets = [(year, value) for year, value in row.items() if not pd.isna(value)]
            _logger.debug(f"Extracted targets for scenario '{scenario}': {targets}")
        else:
            raise SetupException("writePolicyConstraintFile: must specify targets or both csvPath and scenario")

        policyConstraintsXml(policyName, region, targets, market=market, minPrice=minPrice,
                             policyElement=policyElement, policyType=policyType, pathname=pathname)

    @callableMethod
    def setRegionalNonCO2Emissions(self, region, sector, subsector, stubTechnology, species, values,
                                   configFileTag="nonco2_energy"):
        """
        Create a modified version of all_energy_emissions.xml with the given values for
        for `technology` in `sector` based on the data in `values`.
        **Callable from XML setup files.**

        :param region: (str) a GCAM region name
        :param sector: (str) the name of a GCAM sector
        :param subsector: (str) the name of the subsector
        :param stubTechnology: (str) the name of a GCAM stub-technology in `sector`
        :param species: (str) the name of the gas for which to set the emissions
        :param values: (dict-like or iterable of tuples of (year, shareWeight)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.items() after
            which the rest of the explanation above applies. The `shareWeight` can be
            anything coercible to float.
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. Default is "nonco2_energy" => all_energy_emissions.xml
        :return: none
        """
        _logger.info("Set Non-CO2 emissions for (%s, %s, %s, %s, %s) to %s for %s",
                     region, sector, subsector, stubTechnology, species, values, self.name)

        xml_file = self.getLocalCopy(configFileTag, gp=True)

        # //region[@name='USA']/supplysector[@name='N fertilizer']/subsector[@name='gas']/stub-technology[@name='gas']/period[@year='2005']/Non-CO2[@name='CH4']/input-emissions
        # NOTE: the following uses '%s' since the list comprehension immediately below substitutes in the year.
        xpath = f"//region[@name='{region}']/supplysector[@name='{sector}']/subsector[@name='{subsector}']/stub-technology[@name='{stubTechnology}']/period[@year='%s']/Non-CO2[@name='{species}']/input-emissions"

        pairs = [(xpath % year, coercible(value, float)) for year, value in expandYearRanges(values)]

        xmlEdit(xml_file, pairs)
        self.updateScenarioComponent(configFileTag, xml_file)

    @callableMethod
    def transportTechEfficiency(self, csvFile, xmlTag='transportation'):
        import pandas as pd

        csvPath = pathjoin(getParam('GCAM.ProjectDir'), 'etc', csvFile)

        _logger.info("Called transportTechEfficiency('%s', '%s')", csvPath, xmlTag)
        df = pd.read_csv(csvPath)
        year_cols = [col for col in df.columns if col.isdigit()]

        xml_file = self.getLocalCopy(xmlTag, gp=True)
        item = CachedFile.getFile(xml_file)
        tree = item.tree

        xml_template = "//region[@name='{region}']/supplysector[@name='{sector}']/tranSubsector[@name='{subsector}']/stub-technology[@name='{technology}']/"

        pairs = []

        for (idx, row) in df.iterrows():
            xpath_prefix = xml_template.format(**row)
            input = row['input']

            for year in year_cols:
                improvement = row[year]
                if improvement == 0:
                    continue

                xpath = xpath_prefix + f"period[@year='{year}']/minicam-energy-input[@name='{input}']/coefficient"
                elts = tree.xpath(xpath)

                if elts is None:
                    raise SetupException(f'XPath query {xpath} on file "{xml_file.abs}" failed to find an element')

                if len(elts) != 1:
                    raise SetupException(f'XPath query {xpath} on file "{xml_file.abs}" returned multiple elements')

                elt = elts[0]
                old_value = float(elt.text)
                # The coefficient in the XML file is in energy per output unit (e.g., vehicle-km or passenger-km).
                # A value of 1 in the CSV template, which indicates a 100% improvement (a doubling) of fuel economy,
                # should drop the coefficient value by 50%. Thus the following calculation:
                new_value = old_value / (1 + improvement)
                pairs.append((xpath, new_value))

        xmlEdit(xml_file, pairs)
        self.updateScenarioComponent(xmlTag, xml_file)

    @callableMethod
    def buildingTechEfficiency(self, csvFile, xmlTag='building_update',
                               xmlFile='building_tech_improvements.xml', mode="mult"):
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
            def compute(old, improvement, _):
                return old + improvement

        else:
            raise SetupException(f"buildingTechEfficiency: mode must be either 'add' or 'mult'; got '{mode}'")

        def runForFile(tag, which):
            xml_file = self.getLocalCopy(tag, gp=True)
            item = CachedFile.getFile(xml_file)
            tree = item.tree

            if which == 'GCAM-USA':
                xml_template = "//global-technology-database/location-info[@sector-name='{sector}' and @subsector-name='{subsector}']/technology[@name='{technology}']/"
            else:
                xml_template = "//region[@name='{region}']/supplysector[@name='{sector}']/subsector[@name='{subsector}']/stub-technology[@name='{technology}']/"

            subdf = df.query(f'which == "{which}"')

            for (idx, row) in subdf.iterrows():
                xpath_prefix = xml_template.format(**row)
                input = row['input']
                subsector = row['subsector']
                pairs = []

                for year in year_cols:
                    improvement = row[year]
                    if improvement == 0:
                        continue

                    xpath = xpath_prefix + f"period[@year='{year}']/minicam-energy-input[@name='{input}']/efficiency"
                    elts = tree.xpath(xpath)

                    if elts is None:
                        raise SetupException(f'XPath query "{xpath}" on file "{xml_file.abs}" failed to find an element')

                    if len(elts) != 1:
                        raise SetupException(f'XPath query "{xpath}" on file "{xml_file.abs}" returned multiple elements')

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
            runForFile('bld_usa', 'GCAM-USA')

        xmlAbs = pathjoin(self.scenario_dir_abs, xmlFile)   # TBD: update to use Scenario object and GcamPath
        xmlRel = pathjoin(self.scenario_dir_rel, xmlFile)

        scenarioElt = ET.Element('scenario')
        worldElt = ET.SubElement(scenarioElt, 'world')

        # find or create the sub-element described
        def getSubElement(elt, tag, attr, value):
            xpath = f'./{tag}[@{attr}="{value}"]'
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
            raise SetupException(f"industryTechEfficiency: mode must be either 'add' or 'mult'; got '{mode}'")

        def runForFile(tag, which):
            xml_file = self.getLocalCopy(tag, gp=True)
            item = CachedFile.getFile(xml_file)
            tree = item.tree

            xml_template = "//global-technology-database/location-info[@sector-name='{sector}' and @subsector-name='{subsector}']/technology[@name='{technology}']/"
#            if which == 'GCAM-USA':
#                xml_template = "//global-technology-database/location-info[@sector-name='{sector}' and @subsector-name='{subsector}']/technology[@name='{technology}']/"
#            else:
#                xml_template = "//region[@name='{region}']/supplysector[@name='{sector}']/subsector[@name='{subsector}']/stub-technology[@name='{technology}']/"

            subdf = df.query(f'which == "{which}"')

            for (idx, row) in subdf.iterrows():
                xpath_prefix = xml_template.format(**row)
                input = row['input']
                subsector  = row['subsector']
                pairs = []

                for year in year_cols:
                    improvement = row[year]
                    if improvement == 0:
                        continue

                    xpath = xpath_prefix + f"period[@year='{year}']/minicam-energy-input[@name='{input}']/efficiency"
                    elts = tree.xpath(xpath)

                    if elts is None:
                        raise SetupException(f'XPath query {xpath} on file "{xml_file.abs}" failed to find an element')

                    if len(elts) == 0:
                        raise SetupException(f'XPath query {xpath} on file "{xml_file.abs}" returned zero elements')

                    if len(elts) != 1:
                        raise SetupException(f'XPath query {xpath} on file "{xml_file.abs}" returned multiple elements')

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
            xpath = f'./{tag}[@{attr}="{value}"]'
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
