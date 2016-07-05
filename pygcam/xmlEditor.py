'''
.. Facilities setting up / customizing GCAM project's XML files.

   Common variables and functions for manipulating XML files.
   Basic approach is to create a directory for each defined scenario,
   in which modified files and a corresponding configuration XML file
   are stored.

   To allow functions to be called in any order or combination, each
   copies (if needed) the source file to the local scenario dir, then
   edits it in place. If was previously modified by another function,
   the copy is skipped, and the new edits are applied to the local,
   already modified file. Each function updates the local config file
   to refer to the modified file. (This may be done multiple times, to
   no ill effect.)

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import shutil
import subprocess
import glob
import re
from .error import SetupException
from .landProtection import protectLand, UnmanagedLandClasses
from .config import getConfig, getParam, getParamAsBoolean, setSection
from .utils import coercible, mkdirs, unixPath
from .log import getLogger, setLogLevel, configureLogs

_logger = getLogger(__name__)

pathjoin = os.path.join     # "alias" this since it's used frequently

LOCAL_XML_NAME = "local-xml"
DYN_XML_NAME   = "dyn-xml"

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

def xmlStarlet(*args):
    """
    Run the XML Starlet executable in a subprocess, passing the given `args`
    and return True if success, else False.

    :param args: (iterable) these values are passed as arguments to xmlstarlet.
        See xmlstarlet documentation for details.
    :return: True if exit status was 0, else False
    """
    args = map(str, args)
    args.insert(0, getParam('GCAM.XmlStarlet'))

    _logger.debug(' '.join(args))

    return subprocess.call(args, shell=False) == 0

def xmlEdit(filename, *rest):
    """
    Edit the XML file `filename` in place, using the xmlstarlet arguments passed in `rest`.

    :param filename: the file to edit
    :param rest: (iterable) values to pass as arguments to xmlstarlet
    :return: True on success, else False
    """
    args = ['ed', '--inplace'] + list(rest) + [filename]
    return xmlStarlet(*args)

def xmlSel(filename, *rest):
    """
    Return True if the XML component identified by the xmlstarlet arguments
    in `rest` exists in `filename`. Useful for deciding whether to edit or
    insert an XML element.

    :param filename: (str) the file to edit
    :param rest: (iterable) values to pass as arguments to xmlstarlet
    :return:
    """
    args = ['sel'] + list(rest) + [filename]
    return xmlStarlet(*args)

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

    def _attr(element, value): # Simple helper function
        return '-i "//%s" -t attr -n name -v "%s" ' % (element, value)

    if fromRegion:
        xpath = "//region[@name='%s']/%s[@name='%s']/subsector[@name='%s']/stub-technology[@name='%s']" % \
                (region, sectorElement, sector, subsector, technology)
    else:
        xpath = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                (sector, subsector, technology)

    exe = getParam('GCAM.XmlStarlet')

    # Surround the extracted XML with the necessary hierarchy
    cmd1 = '''%s sel -t -e scenario -e world -e region -e %s -e subsector -c "%s" "%s"''' % \
           (exe, sectorElement, xpath, srcFile)

    # Insert attribute names to the new hierarchy and rename technology => stub-technology (for global-tech-db case)
    cmd2 = exe + " ed " + _attr("region", region) + _attr(sectorElement, sector) + _attr("subsector", subsector) + \
           '''-r "//technology[@name='%s']" -v stub-technology ''' % technology

    # Workaround for parsing error: explicitly name shutdown deciders
    for name in ['phased-shutdown-decider', 'profit-shutdown-decider']:
        cmd2 += ' -d "//%s"' % name  # just delete the redundant definitions...
        #cmd2 += ' -i "//{decider}" -t attr -n name -v "{decider}"'.format(decider=name)

    # Redirect output to the destination file
    cmd = "%s | %s > %s" % (cmd1, cmd2, dstFile)
    _logger.debug(cmd)
    status = subprocess.call(cmd, shell=True)
    return status == 0


def expandYearRanges(seq):
    """
    Expand a sequence of (year, value) tuples, or a dict keyed by
    year, where the year argument may be a string containing identifying
    range of values with an optional "step" value (default step is 5)
    e.g., "2015-2030", which means (2015, 2020, 2025, 2030), or
    "2015-2020:1", which means (2015, 2016, 2017, 2018, 2019, 2020).
    When a range is given, the tuple is replaced with a sequence of
    tuples naming each years explicitly.

    :param seq_or_dict:
        The sequence of tuples or dict of {year: value} elements
        to expand.
    :return:
        The a list of tuples holding the expanded sequence.
    """
    result = []
    try:
        seq = list(seq.iteritems())     # convert dict or Series to list of pairs
    except:                             # of quietly fail, and just use 'seq' as is
        pass

    for year, value in seq:
        if isinstance(year, basestring) and '-' in year:
            m = re.search('^(\d{4})-(\d{4})(:(\d+))?$', year)
            if not m:
                raise SetupException('Unrecognized year range specification: %s' % year)

            startYear = int(m.group(1))
            endYear   = int(m.group(2))
            stepStr = m.group(4)
            step = int(stepStr) if stepStr else 5
            expanded = map(lambda y: [y, value], xrange(startYear, endYear+step, step))
            result.extend(expanded)
        else:
            result.append((year, value))

    return result


class XMLEditor(object):
    '''
    Base class for scenario setup. Actual scenarios must subclass this.
    Represents the information required to setup a scenario, i.e., to
    generate and/or copy the required XML files into the XML output dir.
    '''
    def __init__(self, baseline, scenario, xmlOutputRoot, xmlSourceDir, refWorkspace, subdir, parent=None):
        self.name = name = scenario or baseline # if no scenario stated, assume it's the baseline
        self.parent = parent
        self.refWorkspace = refWorkspace
        self.xmlSourceDir = xmlSourceDir
        self.configPath = None

        self.local_xml_abs = makeDirPath((xmlOutputRoot, LOCAL_XML_NAME), create=True)
        self.dyn_xml_abs   = makeDirPath((xmlOutputRoot, DYN_XML_NAME), create=True)

        self.local_xml_rel = pathjoin("..", LOCAL_XML_NAME)
        self.dyn_xml_rel   = pathjoin("..", DYN_XML_NAME)

        # Allow scenario name to have arbitrary subdirs between "../local-xml" and
        # the scenario name, e.g., "../local-xml/client/scenario"
        self.subdir = subdir or ''

        # N.B. join helpfully drops out "" components
        self.scenario_dir_abs = makeDirPath((self.local_xml_abs, subdir, name), create=True)
        self.scenario_dir_rel = pathjoin(self.local_xml_rel, subdir, name)
        self.baseline_dir_rel = pathjoin(self.local_xml_rel, subdir, self.parent.name) if self.parent else None

        self.scenario_dyn_dir_abs = makeDirPath((self.dyn_xml_abs, subdir, name), create=True)
        self.scenario_dyn_dir_rel = pathjoin(self.dyn_xml_rel, subdir, name)

        # Store commonly-used paths
        gcam_xml = "input/gcam-data-system/xml"
        self.gcam_prefix_abs = prefix_abs = pathjoin(refWorkspace, gcam_xml)
        self.gcam_prefix_rel = prefix_rel = pathjoin('../', gcam_xml)

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

        self.solution_prefix_abs = pathjoin(refWorkspace, "input", "solution")
        self.solution_prefix_rel = pathjoin("..", "input", "solution")

        # do this last so mixins can access the instance variables set above
        super(XMLEditor, self).__init__()

    def setup(self, args):
        """
        Set-up a scenario based on a "parent" scenario. If dynamic is True (or True-like),
        symlinks are created in the dyn-xml directory to all the XML files in the local-xml
        directory for this scenario so that files generated into the dyn-xml directory can
        refer to them.

        :param stopPeriod: (coercible to int) a period number or a year at which to stop
           running GCAM
        :param args: (argparse.Namespace) arguments passed from the top-level call to setup
        :return: none
        """
        _logger.info("Generating scenario %s" % self.name)

        # Delete old generated scenario files
        scenDir = self.scenario_dir_abs
        dynDir  = self.scenario_dyn_dir_abs
        shutil.rmtree(scenDir)
        shutil.rmtree(dynDir)
        mkdirs(scenDir)
        mkdirs(dynDir)

        xmlSubdir = pathjoin(self.xmlSourceDir, self.subdir, 'xml')
        xmlFiles  = glob.glob("%s/*.xml" % xmlSubdir)

        if xmlFiles:
            _logger.info("Copy static XML files to %s" % scenDir)
            for src in xmlFiles:
                # dst = os.path.join(scenDir, os.path.basename(src))
                shutil.copy2(src, scenDir)     # copy2 preserves metadata, e.g., timestamp

            dynamic = 'dynamic' in args and args.dynamic

            if dynamic:
                for xml in xmlFiles:
                    base = os.path.basename(xml)
                    dst = os.path.join(dynDir, base)
                    src = os.path.join(scenDir, base)
                    os.symlink(src, dst)

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

        # For the following settings, no action is taken when value is None
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

        # According to Pralit, outFile.csv isn't maintained and isn't reliable.
        if getParam('GCAM.WriteOutputCsv'):
            self.updateConfigComponent('Files', 'outFileName', value=None,
                                       writeOutput=getParamAsBoolean('GCAM.WriteOutputCsv'))


    def makeScenarioComponentsUnique(self):
        """
        Give all reference scenario components a unique "name" tag to facilitate manipulation via xmlstarlet.
        """
        self.renameScenarioComponent("socioeconomics_1", pathjoin(self.socioeconomics_dir_rel, "interest_rate.xml"))
        self.renameScenarioComponent("socioeconomics_2", pathjoin(self.socioeconomics_dir_rel, "socioeconomics_GCAM3.xml"))

        self.renameScenarioComponent("industry_1", pathjoin(self.energy_dir_rel, "industry.xml"))
        self.renameScenarioComponent("industry_2", pathjoin(self.energy_dir_rel, "industry_incelas_gcam3.xml"))

        self.renameScenarioComponent("cement_1", pathjoin(self.energy_dir_rel, "cement.xml"))
        self.renameScenarioComponent("cement_2", pathjoin(self.energy_dir_rel, "cement_incelas_gcam3.xml"))

        landFiles = ('land_input_1', 'land_input_2', 'land_input_3', 'protected_land_input_2', 'protected_land_input_3')
        for landFile in landFiles:
            self.renameScenarioComponent(landFile, pathjoin(self.aglu_dir_rel, landFile + '.xml'))

    def cfgPath(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        if not self.configPath:
            # compute the first time, then cache it
            self.configPath = os.path.realpath(pathjoin(self.scenario_dir_abs, 'config.xml'))

        return self.configPath

    def _splitPath(self, path):
        '''
        See if the path refers to a file in our scenario space, and if so,
        return the tail, i.e., the scenario-relative path.
        '''
        def _split(path, prefix):
            '''
            Split off the tail of path relative to prefix, and return the tail
            and the corresponding absolute path. If not recognized, return None.
            '''
            if path.startswith(prefix):
                tail = path[len(prefix):]
                if tail[0] == os.path.sep:      # skip leading slash, if any
                    tail = tail[1:]

                return tail

            return None

        result = _split(path, self.scenario_dir_rel)

        if not result:
            if self.parent:
                result = self.parent._splitPath(path)
            else:
                # At the top of the parent chain we check 2 standard GCAM locations
                result = (_split(path, self.gcam_prefix_rel) or
                          _split(path, self.solution_prefix_rel))
        return result

    def _closestCopy(self, tail):
        '''
        See if the path refers to a file in our scenario space, and if so,
        return the tail, i.e., the scenario-relative path.
        '''
        def _check(absDir):
            absPath = pathjoin(absDir, tail)
            return absPath if os.path.lexists(absPath) else None

        absPath = _check(self.scenario_dir_abs)

        if not absPath:
            if self.parent:
                absPath = self.parent._closestCopy(tail)
            else:
                # At the top of the parent chain we check 2 standard GCAM locations
                absPath = (_check(self.gcam_prefix_abs) or
                           _check(self.solution_prefix_abs))

        return absPath

    def parseRelPath(self, relPath):
        '''
        Parse a relative pathname and return a tuple with the scenario prefix, the
        tail part (after the prefix) and the absolute path to this file. If a
        scenario doesn't recognize the prefix as its own, it recursively asks its
        parent, unless the parent is None, in which case the standard GCAM prefix
        is checked, and if not present, and error is raised.

        :param relPath: (str) a relative pathname
        '''
        tail = self._splitPath(relPath)
        if not tail:
            raise SetupException('File "%s" was not recognized by any scenario' % relPath)

        result = self._closestCopy(tail)
        if not result:
            raise SetupException('File "%s" was not found in any scenario directory' % relPath)

        return result   # returns (relDir, absDir)

    def getLocalCopy(self, pathname):
        '''
        Get the filename for the most local version (in terms of scenario hierarchy)
        of an XML file, and copy the file to our scenario dir if not already there.
        '''
        tail = self._splitPath(pathname)
        if not tail:
            raise SetupException('File "%s" was not recognized by any scenario' % pathname)

        localAbsPath = pathjoin(self.scenario_dir_abs, tail)
        localRelPath = pathjoin(self.scenario_dir_rel, tail)

        if not os.path.lexists(localAbsPath):   # if we don't already have a local copy, copy it
            absPath = self._closestCopy(tail)
            if not absPath:
                raise SetupException('File "%s" was not found in any scenario directory' % pathname)

            # if localRelPath == pathname:
            #     raise SetupException("Referenced file does not exist: %s" % pathname)

            copyIfMissing(absPath, localAbsPath, makedirs=True)

        return localRelPath, localAbsPath


    def updateConfigComponent(self, group, name, value=None, writeOutput=None, appendScenarioName=None):
        """
        Update the value of an arbitrary element in GCAM's configuration.xml file, i.e.,
        ``<{group}><Value name="{name}>{value}</Value></{group}>``

        Optional args are used only for ``<Files>`` group, which has entries like
        ``<Value write-output="1" append-scenario-name="0" name="outFileName">outFile.csv</Value>``
        Values for the optional args can be passed as any of ``[0, 1, "0", "1", True, False]``.

        :param group: the name of a group of config elements in GCAM's configuration.xml
        :param name: the name of the element to be updated
        :param value: the value to set between the ``<Value></Value>`` elements
        :param writeOutput: for ``<Files>`` group, this sets the optional ``write-output`` attribute
        :param appendScenarioName: for ``<Files>`` group, this sets the optional ``append-scenario-name``
          attribute.
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
        args = [cfg]

        if value is not None:
            args += ['-u', prefix,
                     '-v', str(value)]

        if writeOutput is not None:
            args += ['-u', prefix + "/@write-output",
                     '-v', str(int(writeOutput))]

        if appendScenarioName is not None:
            args += ['-u', prefix + "/@append-scenario-name",
                     '-v', str(int(appendScenarioName))]

        xmlEdit(*args)

    def setClimateOutputInterval(self, years):
        """
        Sets the climate output interval (the frequency at which climate-related
        outputs are saved to the XML database) to the given number of years,
        e.g., ``<Value name="climateOutputInterval">1</Value>``.

        :param years: (coercable to int) the number of years
        :return: none
        """
        self.updateConfigComponent('Ints', 'climateOutputInterval', coercible(years, int))

    def addScenarioComponent(self, name, xmlfile):
        """
        Add a new ``<ScenarioComponent>`` to the configuration file, at the end of the list
        of components.

        :param name: the name to assign to the new scenario component
        :param xmlfile: the location of the XML file, relative to the `exe` directory
        :return: none
        """
        xmlfile = unixPath(xmlfile)
        _logger.info("Add ScenarioComponent name='%s', xmlfile='%s'" % (name, xmlfile))
        cfg = self.cfgPath()

        xmlEdit(cfg,
                '-s', '//ScenarioComponents',
                '-t', 'elem',
                '-n', 'TMP',
                '-v', '',
                '-i', '//ScenarioComponents/TMP',
                '-t', 'attr',
                '-name', 'name',
                '-v', name,
                '-u', '//ScenarioComponents/TMP',
                '-v', xmlfile,
                '-r', '//ScenarioComponents/TMP',
                '-v', 'Value')

    def insertScenarioComponent(self, name, xmlfile, after):
        """
        Insert a ``<ScenarioComponent>`` to the configuration file, following the
        entry named by ``after``.

        :param name: the name to assign to the new scenario component
        :param xmlfile: the location of the XML file, relative to the `exe` directory
        :param after: the name of the element after which to insert the new component
        :return: none
        """
        xmlfile = unixPath(xmlfile)
        _logger.info("Insert ScenarioComponent name='%s', xmlfile='%s' after value '%s'" % (name, xmlfile, after))
        cfg = self.cfgPath()

        xmlEdit(cfg,
                '-a', '//ScenarioComponents/Value[@name="%s"]' % after,
                '-t', 'elem',
                '-n', 'TMP',
                '-v', '',
                '-i', '//ScenarioComponents/TMP',
                '-t', 'attr',
                '-name', 'name',
                '-v', name,
                '-u', '//ScenarioComponents/TMP',
                '-v', xmlfile,
                '-r', '//ScenarioComponents/TMP',
                '-v', 'Value')

    def updateScenarioComponent(self, name, xmlfile):
        """
        Set a new filename for a ScenarioComponent identified by the ``<Value>`` element name.

        :param name: the name of the scenario component to update
        :param xmlfile: the location of the XML file, relative to the `exe` directory, that
           should replace the existing value
        :return: none
        """
        xmlfile = unixPath(xmlfile)
        _logger.info("Update ScenarioComponent name='%s', xmlfile='%s'" % (name, xmlfile))

        self.updateConfigComponent('ScenarioComponents', name, xmlfile)

    def delScenarioComponent(self, name):
        """
        Delete a ``<ScenarioComponent>`` identified by the ``<Value>`` element name.

        :param name: the name of the component to delete
        :return: none
        """
        _logger.info("Delete ScenarioComponent name='%s' for scenario" % name)
        cfg = self.cfgPath()

        xmlEdit(cfg, '-d', "//ScenarioComponents/Value[@name='%s']" % name)

    def renameScenarioComponent(self, name, xmlfile):
        """
        Modify the name of a ``ScenarioComponent``, located by the XML file path it holds.
        This is used in to create a local reference XML that has unique names
        for all scenario components, which allows all further modifications to refer
        only to the (now unique) names.

        :param name: the new name for the scenario component
        :param xmlfile: the XML file path used to locate the scenario component
        :return: none
        """
        xmlfile = unixPath(xmlfile)
        _logger.debug("Rename ScenarioComponent name='%s', xmlfile='%s'" % (name, xmlfile))
        cfg = self.cfgPath()

        xmlEdit(cfg,
                '-u', "//ScenarioComponents/Value[text()='%s']/@name" % xmlfile,
                '-v', name)

    def addMarketConstraint(self, target, policy, dynamic=False):
        """
        Adds references to a pair of files comprising a policy, i.e., a policy definition
        file and a constraint file. References to the two files--assumed to be named ``XXX-{subsidy,tax}.xml``
        and ``XXX-{subsidy,tax}-constraint.xml`` for policy `target` ``XXX``--are added to the configuration file.

        :param target: the subject of the policy, e.g., corn-etoh, cell-etoh, ft-biofuel, biodiesel
        :param policy: one of ``subsidy`` or ``tax``
        :param dynamic: True if the XML file was dynamically generated, and thus found in ``dyn-xml``
           rather than ``local-xml``
        :return: none
        """
        _logger.info("Add market constraint: %s %s for %s" % (target, policy, self.name))

        cfg = self.cfgPath()

        # if policy == "subsidy":
        #     policy="subs"	# use shorthand in filename

        basename = "%s-%s" % (target, policy)	# e.g., corn-etoh-subsidy

        policyTag     = target + "-policy"
        constraintTag = target + "-constraint"

        reldir = self.scenario_dyn_dir_rel if dynamic else self.scenario_dir_rel

        policyXML     = pathjoin(reldir, basename + ".xml")
        constraintXML = pathjoin(reldir, basename + "-constraint.xml")

        # See if element exists in config file (-Q => quiet; just report exit status)
        args = ['-Q', '-t', '-v', '//ScenarioComponents/Value[@name="%s"]' % policyTag]

        # If we've already added files for policy/constraint on this target,
        # we replace the old values with new ones. Otherwise, we add them.
        if xmlSel(cfg, *args):
            # found it; update the elements
            self.updateScenarioComponent(policyTag, policyXML)
            self.updateScenarioComponent(constraintTag, constraintXML)
        else:
            # didn't find it; add the elements
            self.addScenarioComponent(policyTag, policyXML)
            self.addScenarioComponent(constraintTag, constraintXML)

    def delMarketConstraint(self, target, policy):
        """
        Delete the two elements defining a market constraint from the configuration file. The filenames
        are constructed as indicated in

        :param target: the subject of the policy, e.g., corn-etoh, cell-etoh, ft-biofuel, biodiesel
        :param policy: one of ``subsidy`` or ``tax``
        :return: none
        """
        _logger.info("Delete market constraint: %s %s for %s" % (target, policy, self.name))
        cfg = self.cfgPath()

        # if policy == "subsidy":
        #     policy = "subs"	# use shorthand in filename

        policyTag     = target + "-" + policy
        constraintTag = target + "-constraint"

        # See if element exists in config file (-Q => quiet; just report exit status)
        args = ['-Q', '-t', '-v', '//ScenarioComponents/Value[@name="%s"]' % policyTag]

        if xmlSel(cfg, args):
            # found it; delete the elements
            self.delScenarioComponent(policyTag)
            self.delScenarioComponent(constraintTag)

    # deprecated
    # def setScenarioName(self):
    #     """
    #     Set the name of the scenario based on the value passed to __init__
    #
    #     :return: none
    #     """
    #     self.updateConfigComponent('Strings', 'scenarioName', self.name)

    def setStopPeriod(self, yearOrPeriod):
        """
        Sets the model stop period. If `stopPeriod` is <= 22, the stop period is set to
        the given value. If the value > 2000, the value is treated as a year and converted
        to the correct stop period for the configuration file.

        :param yearOrPeriod: (coercible to int) this argument is treated as a literal
          stop period if the value is < 23. (N.B. 2015 = step 4, 2020 = step 5, and so
          on.) If 2000 < `yearOrPeriod` <= 2100, it is treated as a year, and converted
          to a stopPeriod. If the value is in neither range, a SetupException is raised.
        :return: none
        :raises: SetupException
        """
        value = coercible(yearOrPeriod, int)
        stopPeriod = value if 1< value < 23 else 1+ (value - 2000)/5

        self.updateConfigComponent('Ints', 'stop-period', stopPeriod)

    def setInterpolationFunction(self, region, supplysector, subsector, fromYear, toYear,
                                 funcName, applyTo='share-weight', stubTechnology=None):
        """
        Set the interpolation function for the share-weight of the `subsector`
        of `supplysector` to `funcName` between years `fromYear` to `toYear`
        in `region`.

        :param region: the GCAM region to operate on
        :param supplysector: the name of a supply sector
        :param subsector: the name of a sub-sector
        :param fromYear: the year to start interpolating
        :param toYear: the year to stop interpolating
        :param funcName: the name of an interpolation function
        :param applyTo: what the interpolation function is applied to
        :return: none
        """
        _logger.info("Set interpolation function for '%s' : '%s' to '%s'" % (supplysector, subsector, funcName))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))

        # /scenario/world/region[@name='USA']/supplysector[@name='refining']/subsector[@name='biomass liquids']/interpolation-rule
        prefix = '//region[@name="%s"]/supplysector[@name="%s"]/subsector[@name="%s"]%s/interpolation-rule[@apply-to="%s"]' % \
                 (region, supplysector, subsector,
                  '/stub-technology[@name="%s"]' % stubTechnology if stubTechnology else '',
                  applyTo)

        xmlEdit(enTransFileAbs,
                '-u', prefix + '/@from-year',
                '-v', fromYear,
                '-u', prefix + '/@to-year',
                '-v', toYear,
                '-u', prefix + '/interpolation-function/@name',
                '-v', funcName)

        self.updateScenarioComponent("energy_transformation", enTransFileRel)

    def setupSolver(self, solutionTolerance=None, broydenTolerance=None,
                    maxModelCalcs=None, maxIterations=None):
        """
        Set the model solution tolerance to the given values for the solver
        "driver" (`solutionTolerance`) and, optionally for the Broyden component
        (`broydenTolerance`).

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
        solverFileRel, solverFileAbs = self.getLocalCopy(pathjoin(self.solution_prefix_rel, solverFile))

        prefix = "//scenario/user-configurable-solver[@year>=2010]/"
        args = [solverFileAbs]

        if solutionTolerance:
            args += ['-u', prefix + 'solution-tolerance',
                     '-v', str(solutionTolerance)]

        if broydenTolerance:
            args += ['-u', prefix + 'broyden-solver-component/ftol',
                     '-v', str(broydenTolerance)]

        if maxModelCalcs:
            args += ['-u', prefix + 'max-model-calcs',
                     '-v', str(maxModelCalcs)]

        if maxIterations:
            args += ['-u', prefix + 'broyden-solver-component/max-iterations',
                     '-v', str(maxIterations)]

        xmlEdit(*args)

        self.updateScenarioComponent("solver", solverFileRel)


    def dropLandProtection(self):
        self.delScenarioComponent("protected_land_input_2")
        self.delScenarioComponent("protected_land_input_3")

    def protectLand(self, fraction, landClasses=None, otherArable=False, regions=None):
        """
        Modify land_input files to protect a constant fraction of unmanaged
        land of the given classes, in the given regions.

        :param fraction: (float) the fraction of land in the given land classes
               to protect
        :param landClasses: a string or a list of strings, or None. If None, all
               "standard" unmanaged land classes are modified.
        :param otherArable: (bool) if True, land class 'OtherArableLand' is
            included in default land classes.
        :param regions: a string or a list of strings, or None. If None, all
               regions are modified.
        """
        _logger.info("Protecting %d%% of land globally", int(fraction * 100))

        # NB: this code depends on these being the tags assigned to the land files
        # as is currently the case in XmlEditor.makeScenarioComponentsUnique()
        landFiles = ['land_input_2', 'land_input_3']
        for landFile in landFiles:
            filename = landFile + '.xml'
            landFileRel, landFileAbs = self.getLocalCopy(pathjoin(self.aglu_dir_rel, filename))

            protectLand(landFileAbs, landFileAbs, fraction, landClasses=landClasses,
                        otherArable=otherArable, regions=regions)
            self.updateScenarioComponent(landFile, landFileRel)

    # TBD: normalize so that all (year, value) args behave like the pairs, in all fns?
    # TBD: or handle both dict-like vs 'list of pairs' cases? If it has iteritems, then
    # TBD: it's dict-like enough for our purposes. Else, it should be [(year, val), (year, val)]
    #
    # TBD: optional arg to indicate delta rather than absolute value. More useful but will
    # TBD: require lxml rather than xmlstarlet. See code for land protection.
    #
    # TBD: have this and related functions handle both regional and GTDB cases?
    # TBD: test
    def setGlobalTechNonEnergyCost(self, sector, subsector, technology, values):
        """
        Set the non-energy cost of for technology in the global-technology-database,
        given a list of values of (year, price). The price is applied to all years
        indicated by the range.

        :param sector: (str) the name of a GCAM sector
        :param subsector: (str) the name of a GCAM subsector within `sector`
        :param technology: (str) the name of a GCAM technology in `subsector`
        :param values: (dict-like or iterable of tuples of (year, price)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.iteritems() after
            which the rest of the explanation above applies. The `price` can be
            anything coercible to float.
        """
        _logger.info("Set non-energy-cost of %s for %s to %s" % (technology, self.name, values))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))

        prefix = '//global-technology-database/location-info[@sector-name="%s" and @subsector-name="%s"]/technology[@name="%s"]' % \
                 (sector, subsector, technology)
        suffix = '/minicam-non-energy-input[@name="non-energy"]/input-cost'

        args = [enTransFileAbs]
        for year, price in expandYearRanges(values):
            args += ['-u',
                     prefix + ('/period[@year="%s"]' % year) + suffix,
                     '-v', str(price)]

        xmlEdit(*args)

        self.updateScenarioComponent("energy_transformation", enTransFileRel)

    # TBD: Test
    def setGlobalTechShutdownRate(self, sector, subsector, technology, values):
        """
        Create a modified version of en_transformation.xml with the given shutdown
        rates for `technology` in `sector` based on the data in `values`.

        :param sector: (str) the name of a GCAM sector
        :param subsector: (str) the name of a GCAM subsector within `sector`
        :param technology: (str) the name of a GCAM technology in `subsector`
        :param values: (dict-like or iterable of tuples of (year, shutdownRate)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.iteritems() after
            which the rest of the explanation above applies. The `shutdownRate` can be
            anything coercible to float.
        :param xmlBasename: (str) the name of an xml file in the energy-xml folder to edit.
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This must match `xmlBasename`.
        :return: none
        """
        _logger.info("Set shutdown rate for (%s, %s) to %s for %s" % (sector, technology, values, self.name))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))

        prefix = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                 (sector, subsector, technology)

        args = [enTransFileAbs]

        for year, value in expandYearRanges(values):
            args += ['-u', prefix + "/period[@year='%s']/phased-shutdown-decider/shutdown-rate" % year,
                     '-v', coercible(value, float)]

        xmlEdit(*args)

        self.updateScenarioComponent("energy_transformation", enTransFileRel)

    def setRegionalShareWeights(self, region, sector, subsector, values,
                               stubTechnology=None,
                               xmlBasename='en_transformation.xml',
                               configFileTag='energy_transformation'):
        """
        Create a modified version of en_transformation.xml with the given share-weights
        for `technology` in `sector` based on the data in `values`.

        :param region: if not None, changes are made in a specific region, otherwise they're
            made in the global-technology-database.
        :param sector: (str) the name of a GCAM sector
        :param technology: (str) the name of a GCAM technology in `sector`
        :param values: (dict-like or iterable of tuples of (year, shareWeight)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.iteritems() after
            which the rest of the explanation above applies. The `shareWeight` can be
            anything coercible to float.
        :param xmlBasename: (str) the name of an xml file in the energy-xml folder to edit.
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This must match `xmlBasename`.
        :return: none
        """
        if _logger.level.lower() in ['debug', 'info']:
            from .utils import printSeries

            _logger.info("Set share-weights for (%s, %s, %s) for %s" % \
                  (region, sector, stubTechnology, self.name))
            printSeries(values, 'share-weights')

        if not xmlBasename.endswith('.xml'):
            xmlBasename += '.xml'

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, xmlBasename))

        prefix = "//region[@name='%s']/supplysector[@name='%s']/subsector[@name='%s']" % (region, sector, subsector)

        shareWeight = '/stub-technology[@name="{technology}"]/period[@year="{year}"]/share-weight' \
                      if stubTechnology else '/share-weight[@year="{year}"]'

        args = [enTransFileAbs]
        for year, value in expandYearRanges(values):
            args += ['-u', prefix + shareWeight.format(technology=stubTechnology, year=year),
                     '-v', coercible(value, float)]

        xmlEdit(*args)

        self.updateScenarioComponent(configFileTag, enTransFileRel)

    # TBD: Test
    def setGlobalTechShareWeight(self, sector, subsector, technology, values,
                                 xmlBasename='en_transformation.xml',
                                 configFileTag='energy_transformation'):
        """
        Create a modified version of en_transformation.xml with the given share-weights
        for `technology` in `sector` based on the data in `values`.

        :param sector: (str) the name of a GCAM sector
        :param technology: (str) the name of a GCAM technology in `sector`
        :param values: (dict-like or iterable of tuples of (year, shareWeight)) `year` can
            be a single year (as string or int), or a string specifying a range of
            years, of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s",
            which provides an alternative timestep. If `values` is dict-like (e.g. a
            pandas Series) a list of tuples is created by calling values.iteritems() after
            which the rest of the explanation above applies. The `shareWeight` can be
            anything coercible to float.
        :param xmlBasename: (str) the name of an xml file in the energy-xml folder to edit.
        :param configFileTag: (str) the 'name' of a <File> element in the <ScenarioComponents>
           section of a config file. This must match `xmlBasename`.
        :return: none
        """
        _logger.info("Set share-weights for (%s, %s) to %s for %s" % (sector, technology, values, self.name))

        if not xmlBasename.endswith('.xml'):
            xmlBasename += '.xml'

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, xmlBasename))

        prefix = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                 (sector, subsector, technology)

        args = [enTransFileAbs]
        for year, value in expandYearRanges(values):
            args += ['-u', prefix + "/period[@year=%s]/share-weight" % year,
                     '-v', coercible(value, float)]

        xmlEdit(*args)

        self.updateScenarioComponent(configFileTag, enTransFileRel)

    # TBD -- test this!
    def _addTimeStepYear(self, year, timestep=5):

        _logger.info("Add timestep year %s" % year)

        year = int(year)
        modeltimeFileRel, modeltimeFileAbs = self.getLocalCopy(pathjoin(self.modeltime_dir_rel, "modeltime.xml"))

        xmlEdit(modeltimeFileAbs,
                '-i', '//modeltime/inter-year[1]',
                '-t', 'elem',
                '-n', 'TMP',
                '-v', str(year),
                '-i', '//TMP',
                '-t', 'attr',
                '-n', 'time-step',
                '-v', str(timestep  - year % timestep),
                '-r', '//TMP',
                '-v', 'inter-year',
                '-i', '//modeltime/inter-year[1]',
                '-t', 'elem',
                '-n', 'TMP',
                '-v', str(year - year % timestep),
                '-i', '//TMP',
                '-t', 'attr',
                '-n', 'time-step',
                '-v', str(year % timestep),
                '-r', '//TMP',
                '-v', 'inter-year')

        nextStep = year + timestep - year % timestep
        args = ['-Q', '-t', '-v', '//model-time/inter-year[text()="%d"]' % nextStep]
        if not xmlSel(modeltimeFileAbs, *args):
            xmlEdit(modeltimeFileAbs,
                    '-i', '//modeltime/inter-year[1]',
                    '-t', 'elem',
                    '-n', 'TMP',
                    '-v', str(nextStep),
                    '-i', '//TMP',
                    '-t', 'attr',
                    '-n', 'time-step',
                    '-v', str(timestep),
                    '-r', '//TMP',
                    '-v', 'inter-year')

        cfg = self.cfgPath()
        xmlEdit(cfg,
                '-u', "//Files/Value[@name='xmlInputFileName']",
                '-v', modeltimeFileRel)

    parser = None
