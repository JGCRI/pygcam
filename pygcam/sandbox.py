#
# Support for creation and navigation of GCAM runtime sandboxes.
#
# Copyright (c) 2016 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
#
import glob
import os

from .config import getParam, getParamAsBoolean, pathjoin, unixPath
from .constants import LOCAL_XML_NAME, DYN_XML_NAME, CONFIG_XML
from .error import SetupException
from .log import getLogger

_logger = getLogger(__name__)


def makeDirPath(*elements, require=False, normpath=True, create=False, mode=0o775):
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
    non_empty = [e for e in elements if e]
    path = pathjoin(*non_empty, normpath=normpath)

    if (create or require) and not os.path.lexists(path):
        if create:
            _logger.debug(f"Creating directory '{path}'")
            os.makedirs(path, mode)
        elif require:
            raise SetupException(f"Required path '{path}' does not exist.")

    return path


class GcamPath(object):
    """
    Simple struct to store absolute and relative paths together. Relative
    paths are generally relative to the run-time "exe" directory.
    """
    __slots__ = ['base', 'rel', 'abs']

    def __init__(self, base, rel, create=False):
        self.base = base
        self.rel = unixPath(rel)
        self.abs = makeDirPath(base, rel, create=create)

    def __str__(self):
        return f"<GcamPath base='{self.base}' rel='{self.rel}'>"

    def basename(self):
        return os.path.basename(self.abs)

    def lexists(self):
        return os.path.lexists(self.abs)


# TBD: Transitional; eventually might be able to drop this when GcamPaths are used consistently.
def gcam_path(obj, abs=True):
    """
    Return a path from either a simple pathname (str) or from a
    GcamPath object. In the GcamPath case, the ``abs`` argument
    is used; in the string case, it is ignored.

    :param obj: (str or GcamPath) the object from which to extract a path
    :param abs: (bool) whether to extract the absolute (default) or relative
        path from GcamPath objects. Ignored when ``obj`` is not a GcamPath.
    :return: (str) the extracted pathname
    """
    if isinstance(obj, GcamPath):
        return obj.abs if abs else obj.rel

    return obj  # just return the object

# TBD: Make this a method of Sandbox
def config_path(scenario, sandbox=None, scenarios_dir=None, group_dir='', config_file=None):
    from .utils import getExeDir

    if scenario:
        # Translate scenario name into config file path, assuming that for scenario
        # FOO, the configuration file is {scenariosDir}/{groupDir}/FOO/config.xml
        scenarios_dir = unixPath(scenarios_dir or getParam('GCAM.ScenariosDir') or '.', abspath=True)
        cfg_path = pathjoin(scenarios_dir, group_dir, scenario, CONFIG_XML)
    else:
        cfg_path = unixPath(config_file or pathjoin(getExeDir(sandbox), 'configuration.xml'), abspath=True)

    return cfg_path

# TBD: incomplete
#   -
#   Maybe xmlSetup should be the only approach rather than supporting original setup subclasses.
#   (Though this is the method for users to add @callable methods called from scenarios.xml.)
#   This way we can assume scenario definition exists in xml format and create an API to get the
#   information about any scenario definition from xmlSetup.py.
#   -
#   The question is whether command-line override capability is required, or if all should be in XML.
#   Need to think through alternative use cases.
#   -
#   Should be no need to pass baseline since this can be inferred from scenario and scenarioGroup.
#   also can tell if it's a baseline; if not, find and cache ref to baseline
#
# TBD: other thoughts
#   -
#   Perhaps __init__ takes only vars apart from policy scenarios, since the rest would be common
#   to all scenarios. It could take a baseline, since that's needed by policy scenarios.
#
class Sandbox(object):
    def __init__(self, baseline, scenario, projectName=None, refWorkspace=None,
                 # Scenario group is used when running scenarios.xml, so we have flag
                 # to indicate whether to also use this as a subdir above scenarios.
                 # The <scenarioGroup> element has a "useGroupDir" attribute that sets this
                 # flag in scenarios.xml.
                 scenarioGroup=None, useGroupDir=False,
                 projectXmlsrc=None, xmlsrcSubdir=None,
                 sandboxRoot=None, sandboxSubdir=None,
                 parent=None, createDirs=True):

        # TBD: rename sandboxSubdir as project_subdir, an optional directory level above scenario
        #  group. New sandbox layout for non-MCS is: /project/[proj_subdir]/[scen_group]/scenario
        #  Alternatively, proj_subdir could be expressed entirely in config vars as with Analysis.
        #  It would be simpler to rely on config vars rather than lots of custom cmdline args. The
        #  config vars can always be set on the cmdline (--set Analysis=series_69) if needed.
        #  -
        #  This implies defining the set of config vars used to locate sandbox and workspace bits.
        #  GCAM.ProjectName not used directly, only via GCAM.ProjectDir, GCAM.ProjectEtc
        #  GCAM.SandboxProjectDir, GCAM.SandboxDir
        #  -
        #  Note that the definition below doesn't allow for ScenarioGroup to be used in scenarios.xml
        #  but *not* in pathname construction.
        #  GCAM.SandboxDir = %(GCAM.SandboxProjectDir)s/%(GCAM.ScenarioGroup)s
        #  -
        #  Maybe simplify option by always using scenario group in dir structure if one is defined.
        #  This would eliminate the useGroupDir flag, and allow more path construction in config.

        self.use_group_dir = useGroupDir
        self.group = scenarioGroup or ''
        self.scenario = scenario or baseline    # if no scenario stated, assume baseline
        self.baseline = baseline
        self.is_baseline = (self.scenario == baseline)
        self.baseline_context = None if self.is_baseline else self.fromXmlSetup(scenarioGroup, baseline)      # TBD
        self.project_name = projectName or getParam('GCAM.ProjectName')
        self.parent = parent

        self.copy_workspace = getParamAsBoolean("GCAM.CopyWorkspace")

        # self.xmlOutputRoot = xmlOutputRoot # TBD: default was self.dyn_xml_abs a defunct file
        # self.xmlOutputDir  = None # TBD: what is this used for? Apparently only used for generated xml, e.g., policies in constraints.py
        #self.scenarioSubdir = scenarioSubdir or scenario   # TBD: Is scenario subdir ever used?

        self.projectXmlsrc  = projectXmlsrc or getParam('GCAM.ProjectXmlsrc')

        # If useGroupDir is True, and no specific xmlsrcSubdir or sandboxSubdir are
        # specified, the scenarioGroup
        self.xmlsrcSubdir = xmlsrcSubdir or (self.group if useGroupDir else '')
        self.sandbox_group_subdir = sandboxSubdir or (self.group if useGroupDir else '')

        self.refWorkspace = refWorkspace or getParam("GCAM.RefWorkspace")
        self.refExeDir = pathjoin(self.refWorkspace, "exe")

        self.sandbox_root = sandboxRoot or getParam('GCAM.SandboxRoot')
        self.sandbox_workspace = getParam('GCAM.SandboxRefWorkspace')
        self.sandbox_workspace_exe_dir = makeDirPath(self.sandbox_workspace, 'exe')

        self.sandbox_dir = makeDirPath(self.sandbox_root, self.project_name, self.sandbox_group_subdir, self.scenario)
        self.sandbox_exe_dir = makeDirPath(self.sandbox_dir, 'exe', create=createDirs)
        self.sandbox_exe_path = pathjoin(self.sandbox_exe_dir, getParam('GCAM.Executable'))

        # self.scenarioXmlOutputDir = makeDirPath(self.xmlOutputDir, self.xmlsrcSubdir, scenario, create=createDirs)
        self.scenario_xmlsrc_dir = makeDirPath(self.projectXmlsrc, self.xmlsrcSubdir, self.scenario, create=createDirs)

        # directories accessed from configuration XML files (so we store relative-to-exe and absolute paths
        self.scenario_gcam_xml_dir = self.gcam_path('../input/gcamdata/xml')

        # TBD: this version is to the link in gcam-mcs/base/local-xml, which points to a directory with subdirs "base/local-xml", which is very confusing.
        # TBD: Does this also need sandbox_group_subdir?
        self.local_xml = self.gcam_path("..", LOCAL_XML_NAME, create=createDirs)

        # TBD: this produces '.../sandboxes/gcam_mcs/group1/policy/local-xml/group1/policy' with redundant "group1/policy". Eliminate this redudancy.
        self.scenario_local_xml_dir = self.gcam_path(self.local_xml.rel, self.xmlsrcSubdir, self.scenario, create=createDirs)

        # TBD: This produces, e.g., '/Users/rjp/ws/group1/policy/local-xml/group1/policy/config.xml'. Simplify dir structure.
        # self.scenario_config_path = pathjoin(self.scenario_dir.abs, CONFIG_XML)

        # TBD: Maybe store in exe dir, i.e., '.../ws/project/group/scenario/exe/config.xml' rather than storing in sandbox_dir/Workspace?
        self.scenario_config_path = pathjoin(self.sandbox_exe_dir, CONFIG_XML)

    @classmethod
    def fromXmlSetup(cls, scenarioGroup, scenario):
        # TBD: lookup the group and scenario, grab all data and return Sandbox(...)
        return ''

    def gcam_path(self, *rel_path_elements, create=False):
        """
        Create a GcamPath instance by joining ``rel_path_elements`` into a path relative
        to the sandbox's "exe" directory.

        :param rel_path_elements: (tuple of str) path elements
        :param create: (bool) if True, create the directory if it doesn't already exist.
        :return: a DirectoryPath instance
        """
        rel_path = pathjoin(*rel_path_elements)
        return GcamPath(self.sandbox_exe_dir, rel_path, create=create)

    # TBD: unused...
    def scenario_xmlsrc_files(self):
        files = glob.glob(self.scenario_xmlsrc_dir + '/*.xml')
        return files

    def cfgPath(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        return self.scenario_config_path

    def create_dir_structure(self):
        """
        Create the directories required in the runtime structure for non-MCS GCAM runs.
        Optionally, this includes a local copy of the full reference workspace, to
        ensure isolation from changes to the reference workspace.

        :return: nothing
        """
        pass

    def create_sandbox(self, scenario, sandbox=None, forceCreate=False, mcsMode=None):
        """
        Create a sandbox to run ``scenario`` given the parameters passed in the
        call to __init__().

        :param scenario: (str) The name of a baseline or policy scenario.
        :return: nothing
        """
        pass

    def editor_class(self, scenario, moduleSpec=None, modulePath=None):
        from importlib import import_module
        from .utils import loadModuleFromPath

        setupXml = getParam('GCAM.ScenarioSetupFile')
        if setupXml:
            from .xmlScenario import createXmlEditorSubclass
            _logger.debug(f"Setup using '{setupXml}'")
            cls = createXmlEditorSubclass(setupXml)     # uses 'GCAM.ScenarioSetupClass' if defined
            return cls

        # If GCAM.ScenarioSetupFile is not set, we attempt to load xmlsrc/scenarios.py,
        # which should contain a "scenarioMapper" dict that yields a subclass of XMLEditor.
        try:
            if moduleSpec:
                module = import_module(moduleSpec, package=None)
            else:
                modulePath = modulePath or pathjoin(self.scenario_xmlsrc_dir, 'scenarios.py')
                _logger.debug(f'Setup using {modulePath}')
                module = loadModuleFromPath(modulePath)

        except Exception as e:
            moduleName = moduleSpec or modulePath
            raise SetupException(f"Failed to load scenarioMapper or ClassMap from module '{moduleName}': {e}")

        try:
            # TBD: document this logic
            # First look for a function called scenarioMapper
            scenarioMapper = getattr(module, 'scenarioMapper', None)
            if scenarioMapper:
                cls = scenarioMapper(scenario)

            else:
                # Look for 'ClassMap' in the specified module
                classMap = getattr(module, 'ClassMap')
                cls = classMap[scenario]

        except KeyError:
            raise SetupException(f"Failed to map scenario '{scenario}' to a class in '{module.__file__}'")

        return cls


