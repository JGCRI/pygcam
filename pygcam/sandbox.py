#
# Support for creation and navigation of GCAM runtime sandboxes.
#
# Copyright (c) 2016 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
#
import glob
import os

from .config import getParam, getParamAsBoolean, setParam, pathjoin, unixPath
from .constants import LOCAL_XML_NAME, CONFIG_XML
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

class Sandbox(object):
    def __init__(self, scenario, projectName=None, scenarioGroup=None,
                 parent=None, createDirs=True):
        """
        Create a Sandbox instance from the given arguments.

        :param scenario: (str) the name of a policy scenario
        :param projectName: (str) the name of the project, defaults to the value of
            config variable `GCAM.DefaultProject`
        :param scenarioGroup: (str) the name of a scenario group defined in scenarios.xml
        :param useGroupDir: (bool) whether to use the ``scenarioGroup`` as an extra directory
            level above scenario sandboxes
        :param parent: (str)
        :param createDirs: (bool) whether to create some dirs
        """
        from .xmlScenario import XMLScenario

        self.scenario = scenario
        self.parent = parent
        self.mcs_mode = getParam('MCS.Mode')

        # Ensure that GCAM.ScenarioGroup is set since system.cfg uses this in path construction
        if scenarioGroup:
            setParam('GCAM.ScenarioGroup', scenarioGroup)

        self.project_name = projectName or getParam('GCAM.ProjectName')
        self.scenarios_file = getParam('GCAM.ScenariosFile')
        self.group = scenarioGroup or ''

        scen_xml = XMLScenario.get_instance(self.scenarios_file)
        group_obj = scen_xml.getGroup(self.group)

        scen_obj = group_obj.getFinalScenario(scenario)
        self.is_baseline = scen_obj.isBaseline

        # TBD
        # self.baseline_context = None if self.is_baseline else self.fromXmlSetup(scenarioGroup, baseline)

        self.copy_workspace = getParamAsBoolean("GCAM.CopyWorkspace")

        self.ref_workspace = getParam("GCAM.RefWorkspace")
        self.ref_workspace_exe_dir = getParam("GCAM.RefExeDir")

        self.sandbox_workspace = getParam('GCAM.SandboxWorkspace')
        self.sandbox_workspace_exe_dir = getParam('GCAM.SandboxWorkspaceExeDir')

        # From system.cfg:
        # GCAM.SandboxDir = %(GCAM.SandboxProjectDir)s/%(GCAM.ProjectSubdir)s/%(GCAM.ScenarioGroup)s
        self.sandbox_dir = getParam('GCAM.SandboxDir')
        self.sandbox_scenario_dir = makeDirPath(self.sandbox_dir, scenario)
        self.sandbox_exe_dir = makeDirPath(self.sandbox_scenario_dir, 'exe', create=createDirs)
        self.sandbox_exe_path = pathjoin(self.sandbox_exe_dir, getParam('GCAM.Executable'))

        # The "local-xml" directory is always found at the same level as scenario dirs
        self.sandbox_local_xml = pathjoin(self.sandbox_scenario_dir, "..", LOCAL_XML_NAME, normpath=True)
        self.sandbox_scenario_xml = makeDirPath(self.sandbox_local_xml, scenario, create=createDirs)

        self.sandbox_dynamic_xml = pathjoin(self.sandbox_scenario_xml, 'dynamic')      # TBD: new subdir under local-xml

        self.sandbox_baseline_xml = (None if self.is_baseline
                                      else makeDirPath(self.sandbox_local_xml, scen_obj.baseline, create=createDirs))

        self.project_xml_src = getParam('GCAM.ProjectXmlsrc')
        self.project_scenario_xml_src = pathjoin(self.project_xml_src, scenario)

        # Directories accessed from configuration XML files (so we store relative-to-exe and
        # absolute paths. Note that gcam_path requires self.sandbox_exe_dir to be set first.
        self.scenario_gcam_xml_dir = self.gcam_path('../input/gcamdata/xml')

        # Store scenario config.xml in '.../project/group/local-xml/scenario/config.xml'
        self.scenario_config_path = pathjoin(self.sandbox_scenario_xml, CONFIG_XML)

    @classmethod
    def fromXmlSetup(cls, scenarioGroup, scenario):
        # TBD: lookup the group and scenario, grab all data and return Sandbox(...)
        return ''

    def gcam_path(self, *rel_path_elements, create=False):
        """
        Create a GcamPath instance by joining ``rel_path_elements`` into a path relative
        to the sandbox's "exe" directory. N.B. Requires self.sandbox_exe_dir to be set.

        :param rel_path_elements: (tuple of str) path elements
        :param create: (bool) if True, create the directory if it doesn't already exist.
        :return: a DirectoryPath instance
        """
        rel_path = pathjoin(*rel_path_elements)
        return GcamPath(self.sandbox_exe_dir, rel_path, create=create)

    def gcam_path_from_abs(self, abs_path, create=False):
        rel_path = os.path.relpath(abs_path, start=self.sandbox_exe_dir)
        return GcamPath(self.sandbox_exe_dir, rel_path, create=create)

    # TBD: unused...
    def scenario_xmlsrc_files(self):
        files = glob.glob(self.project_scenario_xml_src + '/*.xml')
        return files

    def cfgPath(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        return self.scenario_config_path # self.scenario_config_path2

    def create_dir_structure(self):
        """
        Create the directories required in the runtime structure for non-MCS GCAM runs.
        Optionally, this includes a local copy of the full reference workspace, to
        ensure isolation from changes to the reference workspace.

        :return: nothing
        """
        pass

    def create_sandbox(self, forceCreate=False):
        """
        Set up a run-time sandbox in which to run GCAM. This involves copying
        from or linking to files and directories in `workspace`, which defaults
        to the value of config parameter GCAM.SandboxWorkspace.

        :param forceCreate: (bool) if True, delete and recreate the sandbox
        :return: nothing
        """
        pass

    def editor_class(self, scenario, moduleSpec=None, modulePath=None):
        from importlib import import_module
        from .utils import loadModuleFromPath

        setupXml = getParam('GCAM.ScenariosFile')
        if setupXml:
            from .xmlScenario import createXmlEditorSubclass

            _logger.debug(f"Setup using '{setupXml}'")
            cls = createXmlEditorSubclass(setupXml)     # uses 'GCAM.ScenarioSetupClass' if defined
            return cls

        # If GCAM.ScenariosFile is not set, we attempt to load xmlsrc/scenarios.py,
        # which should contain a "scenarioMapper" dict that yields a subclass of XMLEditor.
        try:
            if moduleSpec:
                module = import_module(moduleSpec, package=None)
            else:
                modulePath = modulePath or pathjoin(self.project_xml_src, 'scenarios.py')
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


