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
import argparse
import re
import collections
from .error import SetupException
from .common import coercible

pathjoin = os.path.join     # "alias" this since it's used frequently

LOCAL_XML_NAME = "local-xml"
DYN_XML_NAME   = "dyn-xml"

Verbosity = 0

def _echo(s):
    if Verbosity:
        print "   ", s

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
            _echo("mkdir %s" % parentDir)
            os.makedirs(parentDir, 0o755)

        _echo("Copy %s\n      to %s" % (src, dst))
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
    if Verbosity > 1:
        _echo(' '.join(args))

    return subprocess.call(args, shell=False) == 0

def xmlEdit(filename, *rest):
    """
    Edit the XML file `filename` in place, using the xmlstarlet arguments passed in `rest`.

    :param filename: the file to edit
    :param rest: (iterable) values to pass as arguments to xmlstarlet
    :return: True on success, else False
    """
    args = ['xml', 'ed', '--inplace'] + list(rest) + [filename]
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
    args = ['xml', 'sel'] + list(rest) + [filename]
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

    _echo("Extract stub-technology for %s (%s) to %s" % (technology, region if fromRegion else 'global', dstFile))

    def attr(element, value): # Simple helper function
        return '-i "//%s" -t attr -n name -v "%s" ' % (element, value)

    if fromRegion:
        xpath = "//region[@name='%s']/%s[@name='%s']/subsector[@name='%s']/stub-technology[@name='%s']" % \
                (region, sectorElement, sector, subsector, technology)
    else:
        xpath = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                (sector, subsector, technology)

    # Surround the extracted XML with the necessary hierarchy
    cmd1 = '''xml sel -t -e scenario -e world -e region -e %s -e subsector -c "%s" "%s"''' % (sectorElement, xpath, srcFile)

    # Insert attribute names to the new hierarchy and rename technology => stub-technology (for global-tech-db case)
    cmd2 = "xml ed " + attr("region", region) + attr(sectorElement, sector) + attr("subsector", subsector) + \
           '''-r "//technology[@name='%s']" -v 'stub-technology' ''' % technology

    # Workaround for parsing error: explicitly name shutdown deciders
    for name in ['phased-shutdown-decider', 'profit-shutdown-decider']:
        cmd2 += ' -d "//%s"' % name  # just delete the redundant definitions...
        #cmd2 += ' -i "//{decider}" -t attr -n name -v "{decider}"'.format(decider=name)

    # Redirect output to the destination file
    cmd = "%s | %s > %s" % (cmd1, cmd2, dstFile)
    if Verbosity:
        _echo(cmd)
    status = subprocess.call(cmd, shell=True)
    return status == 0

# TBD: make this handle dict-like objects (including Series) as well.
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


class ConfigEditor(object):
    '''
    Base class for scenario setup. Actual scenarios must subclass this.
    Represents the information required to setup a scenario, i.e., to
    generate and/or copy the required XML files into the XML output dir.
    '''
    def __init__(self, name, parent, xmlOutputRoot, xmlSourceDir, workspaceDir, subdir=""):

        self.name = name
        self.parent = parent
        self.workspaceDir = workspaceDir
        self.xmlSourceDir = xmlSourceDir

        self.local_xml_abs = makeDirPath((xmlOutputRoot, LOCAL_XML_NAME), create=True)
        self.dyn_xml_abs   = makeDirPath((xmlOutputRoot, DYN_XML_NAME), create=True)

        self.local_xml_rel = pathjoin("..", LOCAL_XML_NAME)
        self.dyn_xml_rel   = pathjoin("..", DYN_XML_NAME)

        # Allow scenario name to have arbitrary subdirs between "../local-xml" and
        # the scenario name, e.g., "../local-xml/client/scenario"
        self.subdir = subdir

        # N.B. join helpfully drops out "" components
        self.scenario_dir_abs = makeDirPath((self.local_xml_abs, subdir, name), create=True)
        self.scenario_dir_rel = pathjoin(self.local_xml_rel, subdir, name)

        self.scenario_dyn_dir_abs = makeDirPath((self.dyn_xml_abs, subdir, name), create=True)
        self.scenario_dyn_dir_rel = pathjoin(self.dyn_xml_rel, subdir, name)

        # Store commonly-used paths
        gcam_xml = "input/gcam-data-system/xml"
        self.gcam_prefix_abs = prefix_abs = pathjoin(workspaceDir, gcam_xml)
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

        self.solution_prefix_abs = pathjoin(workspaceDir, "input", "solution")
        self.solution_prefix_rel = pathjoin("..", "input", "solution")

        # do this last so mixins can access the instance variables set above
        super(ConfigEditor, self).__init__()

    def setup(self, stopPeriod=None, dynamic=False, writeDebugFile=None,
              writePrices=None, writeOutputCsv=None, writeXmlOutputFile=None):
        """
        Set-up a scenario based on a "parent" scenario. If dynamic is True (or True-like),
        symlinks are created in the dyn-xml directory to all the XML files in the local-xml
        directory for this scenario so that files generated into the dyn-xml directory can
        refer to them.

        :param stopPeriod: (coercible to int) a period number or a year at which to stop
           running GCAM
        :param dynamic: (bool) if True, symlinks are created in dyn-xml to the files
            written to local-xml
        :param writeDebugFile: (bool) sets whether GCAM should generate a debug file
        :param writePrices: (bool) sets whether GCAM should generate a price file
        :param writeOutputCsv: (bool) sets whether GCAM should generate outFile.csv
        :param writeXmlOutputFile: (bool) sets whether the GCAM should generate the
          large XML file with the combined data from all input files.
        :return: none
        """
        _echo("\nGenerating scenario %s" % self.name)

        # Delete old generated files in case the baseline we're working from has changed
        scenDir = self.scenario_dir_abs
        dynDir  = self.scenario_dyn_dir_abs
        cmd = "rm -rf %s/* %s/*" % (scenDir, dynDir)
        _echo(cmd)
        status = subprocess.call(cmd, shell=True)
        assert status == 0, 'Command failed with status %d: %s' % (status, cmd)

        xmlSubdir = pathjoin(self.xmlSourceDir, 'xml')
        xmlFiles  = glob.glob("%s/*.xml" % xmlSubdir)

        if xmlFiles:
            _echo("Copy static XML files to %s" % scenDir)
            subprocess.call("cp -p %s/*.xml %s" % (xmlSubdir, scenDir), shell=True)

            if dynamic:
                subprocess.call("ln -s %s/*.xml %s" % (scenDir, dynDir), shell=True)

        configPath = self.cfgPath()

        parent = self.parent
        parentConfigPath = parent.cfgPath() if parent else pathjoin(self.workspaceDir, 'exe', 'configuration_ref.xml')

        _echo("Copy %s\n      to %s" % (parentConfigPath, configPath))
        shutil.copy(parentConfigPath, configPath)
        os.chmod(configPath, 0o664)

        # set the scenario name
        self.updateConfigComponent('Strings', 'scenarioName', self.name)

        # This is inherited from baseline by policy scenarios; no need to redo this
        if not self.parent:
            self.makeScenarioComponentsUnique()

        # For the following settings, no action is taken when value is None
        if stopPeriod is not None:
            self.setStopPeriod(stopPeriod)

        if writeDebugFile is not None:
            self.updateConfigComponent('Files', 'xmlDebugFileName', value=None, writeOutput=writeDebugFile)

        if writePrices is not None:
            self.updateConfigComponent('Bools', 'PrintPrices', int(writePrices))

        if writeXmlOutputFile is not None:
            self.updateConfigComponent('Files', 'xmlOutputFileName', value=None, writeOutput=writeXmlOutputFile)

        # According to Pralit, outFile.csv isn't maintained and isn't reliable. We set the
        # output filename to /dev/null to avoid wasting space (and some time) writing it.
        # Note that using a blank (empty) filename causes a runtime error.
        if writeOutputCsv is not None:
            self.updateConfigComponent('Files', 'outFileName', value=None, writeOutput=writeOutputCsv)


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

        self.renameScenarioComponent("land_1", pathjoin(self.aglu_dir_rel, "land_input_1.xml"))
        self.renameScenarioComponent("land_2", pathjoin(self.aglu_dir_rel, "land_input_2.xml"))
        self.renameScenarioComponent("land_3", pathjoin(self.aglu_dir_rel, "land_input_3.xml"))

        self.renameScenarioComponent("protected_land_2", pathjoin(self.aglu_dir_rel, "protected_land_input_2.xml"))
        self.renameScenarioComponent("protected_land_3", pathjoin(self.aglu_dir_rel, "protected_land_input_3.xml"))

    def cfgPath(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        path = os.path.realpath(pathjoin(self.scenario_dir_abs, 'config.xml'))
        return path

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

        _echo("Update <%s><Value %s>%s</Value>" % (group, textArgs, '...' if value is None else value))

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
        _echo("Add ScenarioComponent name='%s', xmlfile='%s'" % (name, xmlfile))
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
        _echo("Insert ScenarioComponent name='%s', xmlfile='%s' after value '%s'" % (name, xmlfile, after))
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
        self.updateConfigComponent('ScenarioComponents', name, xmlfile)

        # _echo("Update ScenarioComponent name='%s', xmlfile='%s'" % (name, xmlfile))
        # cfg = self.cfgPath()
        #
        # xmlEdit(cfg,
        #         '-u', "//ScenarioComponents/Value[@name='%s']" % name,
        #         '-v', xmlfile)

    def delScenarioComponent(self, name):
        """
        Delete a ``<ScenarioComponent>`` identified by the ``<Value>`` element name.

        :param name: the name of the component to delete
        :return: none
        """
        _echo("Delete ScenarioComponent name='%s' for scenario" % name)
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
        _echo("Rename ScenarioComponent name='%s', xmlfile='%s'" % (name, xmlfile))
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
        _echo("Add market constraint: %s %s for %s" % (target, policy, self.name))

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
        _echo("Delete market constraint: %s %s for %s" % (target, policy, self.name))
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
        _echo("Set interpolation function for '%s' : '%s' to '%s'" % (supplysector, subsector, funcName))

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

    # TBD: Test
    def setSolutionTolerance(self, tolerance):
        """
        Set the model solution tolerance to the given value.

        :param tolerance: (coercible to float) the value to set
        :return: none
        """
        _echo("Set solution tolerance to %s" % tolerance)

        value = coercible(tolerance, float)
        self.updateConfigComponent('Doubles', 'SolutionTolerance', value)


    def dropLandProtection(self):
        self.delScenarioComponent("protected_land_2")
        self.delScenarioComponent("protected_land_3")

    # TBD: normalize so that all (year, value) args behave like the pairs, in all fns?
    # TBD: or handle both dict-like vs 'list of pairs' cases? If it has iteritems, then
    # TBD: it's dict-like enough for our purposes. Else, it should be [(year, val), (year, val)]
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
        _echo("Set non-energy-cost of %s for %s to %s" % (technology, self.name, values))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))

        prefix = "//global-technology-database/location-info[@sector-name='%s' and subsector[@name='%s']/technology[@name='%s']" % \
                 (sector, subsector, technology)
        suffix = "/minicam-non-energy-input[@name='non-energy']/input-cost"

        args = [enTransFileAbs]
        for year, price in expandYearRanges(values):
            args += ['-u',
                     prefix + ("/period[@year='%s']" % year) + suffix,
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
        _echo("Set shutdown rate for (%s, %s) to %s for %s" % (sector, technology, values, self.name))

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
        if Verbosity:
            from .constraints import printSeries

            _echo("Set share-weights for (%s, %s, %s) for %s" % \
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
        _echo("Set share-weights for (%s, %s) to %s for %s" % (sector, technology, values, self.name))

        if not xmlBasename.endswith('.xml'):
            xmlBasename += '.xml'

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, xmlBasename))

        prefix = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s]/technology[@name='%s']" % \
                 (sector, subsector, technology)

        args = [enTransFileAbs]
        for year, value in expandYearRanges(values):
            args += ['-u', prefix + "/period[@year=%s]/share-weight" % year,
                     '-v', coercible(value, float)]

        xmlEdit(*args)

        self.updateScenarioComponent(configFileTag, enTransFileRel)

    # TBD -- test this!
    def _addTimeStepYear(self, year, timestep=5):

        _echo("Add timestep year %s" % year)

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

    @classmethod
    def parseArgs(cls, baseline=None, scenario=None):
        cls.parser = argparse.ArgumentParser(description='')

        cls.addArgs()      # allow subclasses to modify parser; they must call super
        ns = argparse.Namespace(baseline=baseline, scenario=scenario)
        args = cls.parser.parse_args(namespace=ns)

        global Verbosity
        Verbosity = args.verbosity

        return args

    @classmethod
    def addArgs(cls, baseline=None, scenario=None):
        defaultYears = '2015-2100'
        parser = cls.parser

        parser.add_argument('-b', '--baseline', default=baseline,
                            help='Identify the baseline the selected scenario is based on')

        # parser.add_argument('-c', '--configSection', type=str, default=DEFAULT_SECTION,
        #                     help='''The name of the section in the config file to read from.
        #                     Defaults to %s''' % DEFAULT_SECTION)

        parser.add_argument('-g', '--group', default=None,
                            help='The scenario group to process. Defaults to the group labeled default="1".')

        parser.add_argument('-G', '--noGenerate', action='store_true',
                            help='Do not generate constraints (useful before copying files for Monte Carlo simulation)')

        parser.add_argument('-R', '--resultsDir', default=None,
                            help='The parent directory holding the GCAM output workspaces')

        parser.add_argument('-s', '--scenario', default=scenario,
                            help='Identify the scenario to run (N.B. The name is hardwired in some scripts)')

        parser.add_argument('-v', '--verbosity', action='count',
                            help='Set the diagnostic level. Use multiple -v flags to increase verbosity')

        # parser.add_argument('-x', '--xmlOutputRoot', default=None,
        #                      help='''The root directory into which to generate XML files.''')

        parser.add_argument('-y', '--years', default=defaultYears,
                            help='''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "%s"''' % defaultYears)

        return parser   # for auto-doc generation
