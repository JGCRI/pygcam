#
# AbstractFileMapper, the base class for FileMapper and SimFileMapper
#
# Created: 24 APR 2023
#
# Copyright (c) 2023 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
#
import os
import shutil

from .config import getParam, getParamAsBoolean, getParamAsPath, pathjoin, mkdirs
from .constants import CONFIG_XML, QRESULTS_DIRNAME, DIFFS_DIRNAME, OUTPUT_DIRNAME
from .error import SetupException, PygcamException
from .file_utils import removeTreeSafely, removeFileOrTree, copyFileOrTree, symlinkOrCopyFile
from .gcam_path import makeDirPath, GcamPath
from .log import getLogger
from .xmlScenario import XMLScenario

_logger = getLogger(__name__)

def workspaceLinkOrCopy(src, srcWorkspace, dstSandbox, copyFiles=False):
    """
    Create a link (or copy) in the new workspace to the
    equivalent file in the given source workspace.
    """
    # Set automatically on Windows for users without symlink permission
    copyFiles = copyFiles or getParamAsBoolean('GCAM.CopyAllFiles')
    linkFiles = not copyFiles

    if os.path.isabs(src):
        # if absolute path, append only the basename to the sandboxWorkspace
        srcPath = src
        dstPath = pathjoin(dstSandbox, os.path.basename(os.path.normpath(src)))
    else:
        # if relative path, append the whole thing to both workspaces
        srcPath = pathjoin(srcWorkspace, src)
        dstPath = pathjoin(dstSandbox, src)

    # Ensure that parent directory exists
    parent = os.path.dirname(dstPath)
    mkdirs(parent)

    # If dstPath is a link, we always remove it and either recreate
    # the link or copy the files as required. If dstPath isn't a
    # link, we remove it only if we are replacing it with a link.
    if os.path.lexists(dstPath) and (linkFiles or os.path.islink(dstPath)):
        removeFileOrTree(dstPath)

    # We've removed dstPath unless we're avoiding re-copying srcPath
    if not os.path.lexists(dstPath):
        if copyFiles:
            _logger.info(f'Copying {srcPath} to {dstPath}')
            copyFileOrTree(srcPath, dstPath)
        else:
            symlinkOrCopyFile(srcPath, dstPath)


def getFilesToCopyAndLink(linkParam):
    reqFiles = getParam('GCAM.RequiredFiles')
    allFiles = set(reqFiles.split())

    # Subtract from the set of all files the ones to link
    toLink = getParam(linkParam)
    filesToLink = toLink.split()
    filesToLinkSet = set(filesToLink)

    unknownFiles = filesToLinkSet - allFiles
    if unknownFiles:
        _logger.warn('Ignoring unknown files specified in %s: %s' % (linkParam, list(unknownFiles)))
        filesToLinkSet -= unknownFiles

    # Copy everything that is not in the filesToLinkSet
    filesToCopy = list(allFiles - filesToLinkSet)
    return filesToCopy, filesToLink


class AbstractFileMapper(object):
    """
    Abstract superclass to classes that provide information of the location of files
    and directories used by pygcam. Subclasses are FileMapper (for non-MCS situations)
    and SimFileMapper (for simulations), which have different structures to account for
    simulation and trial directories and other files required for MCS.
    """
    def __init__(self, scenario, project_name=None, scenario_group=None, parent=None, **kwargs):
        """
        Create a FileMapper instance from the given arguments.

        :param scenario: (str) the name of a policy scenario
        :param baseline: (str) the name of the baseline scenario, if not a baseline.
        :param project_name: (str) the name of the project, defaults to the value of
            config variable `GCAM.DefaultProject`
        :param scenario_group: (str) the name of a scenario group defined in scenarios.xml
        :param parent: (Sandbox) Sandbox parent scenario, generally a baseline in the same group
        :param create_dirs: (bool) whether to create some dirs
        """
        self.scenario = scenario
        self.parent = parent
        self.mcs_mode = None # getParam('MCS.Mode')
        self.project_name = project_name or getParam('GCAM.ProjectName')

        self.scenarios_file = getParamAsPath('GCAM.ScenariosFile')
        self.scenario_group = scenario_group or ''

        # Deprecated?
        # Ensure that GCAM.ScenarioGroup is set since system.cfg uses this in path construction
        # if scenario_group:
        #     setParam('GCAM.ScenarioGroup', scenario_group)

        scen_xml = XMLScenario.get_instance(self.scenarios_file)
        group_obj = scen_xml.getGroup(self.scenario_group)
        scen_obj = scenario and group_obj.getFinalScenario(scenario)

        self.is_baseline = scen_obj and scen_obj.isBaseline
        self.baseline = group_obj.baseline

        self.group_subdir = scenario_group if scenario_group and group_obj.useGroupDir else ''

        self.parent_mapper = None
        if not self.is_baseline:

            # TBD: Modify to support out-of-scenario-group parent after groupSource
            #      logic is moved to ScenarioGroup (see xmlScenario.py)
            # self.parent = group_obj.baselineSource if self.is_baseline else None

            # Create Sandbox (or SimFileMapper) for baseline scenario to access config.xml
            self.parent_mapper = self.__class__(scenario=self.baseline,
                                                project_name=project_name,
                                                scenario_group=scenario_group,
                                                **kwargs)

        self.ref_workspace = getParamAsPath('GCAM.RefWorkspace')
        self.ref_workspace_exe_dir = getParamAsPath("GCAM.RefExeDir")
        self.ref_gcamdata_dir = getParam('GCAM.RefGcamData')    # used if running data system

        # TBD: implement this for MCS?
        # self.copy_workspace = getParamAsBoolean('MCS.CopyWorkspace')

        self.project_etc_dir = getParamAsPath('GCAM.ProjectEtc')
        self.project_xml_src = getParamAsPath('GCAM.ProjectXmlsrc')
        self.project_scenario_xml_src = pathjoin(self.project_xml_src, scenario) if scenario else None

        # The following are set in subclasses
        self.sandbox_dir = None
        self.sandbox_scenario_dir = None
        self.sandbox_exe_dir = None
        self.sandbox_exe_path = None
        self.sandbox_output_dir = None
        self.sandbox_xml_db = None
        self.sandbox_query_results_dir = None
        self.sandbox_diffs_dir = None
        self.sandbox_local_xml = None
        self.sandbox_scenario_xml = None
        self.sandbox_dynamic_xml = None
        self.sandbox_baseline_xml = None
        self.sandbox_workspace = None
        self.scenario_config_path = None

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
    # def scenario_xmlsrc_files(self):
    #     files = glob.glob(self.project_scenario_xml_src + '/*.xml')
    #     return files

    def config_path(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        return self.scenario_config_path

    def get_final_config(self):
        raise PygcamException(f"Called AbstractFileMapper's get_final_config(); subclass {self.__class__.__name__} must implement this.")

    def copy_ref_workspace(self, force_create=False, files_to_link_param=None):
        """
        Copy/link the reference workspace to the given sandbox Workspace directory.

        :return: nothing
        """
        ref_workspace = self.ref_workspace
        new_workspace = self.sandbox_workspace

        sandbox_workspace = new_workspace
        sandbox_workspace_exists = os.path.lexists(sandbox_workspace)

        if sandbox_workspace_exists and os.path.samefile(sandbox_workspace, ref_workspace):
            raise SetupException("Sandbox Workspace is the same as reference workspace; no setup performed")

        semaphore_file = pathjoin(sandbox_workspace, '.creation_semaphore')

        try:
            os.remove(semaphore_file)
            force_create = True  # if we can remove it, last attempt failed
        except OSError as e:
            import errno
            if e.errno != errno.ENOENT:  # ENOENT => no such file exists
                raise

        if sandbox_workspace_exists and not force_create:
            _logger.debug("Sandbox workspace already exists and force_create is False")
            return

        version = getParam('GCAM.VersionNumber')
        _logger.info("Setting up GCAM workspace '%s' for GCAM %s", sandbox_workspace, version)

        if force_create:
            _logger.info("Removing workspace '%s'", sandbox_workspace)
            removeTreeSafely(sandbox_workspace, ignore_errors=True)

        mkdirs(sandbox_workspace)
        open(semaphore_file, 'w').close()  # create empty semaphore file

        # Allows override from SimFileMapper when calling super().__init__()
        files_to_link_param = files_to_link_param or 'GCAM.WorkspaceFilesToLink'
        filesToCopy, filesToLink = getFilesToCopyAndLink(files_to_link_param)

        for filename in filesToCopy:
            workspaceLinkOrCopy(filename, ref_workspace, sandbox_workspace, copyFiles=True)

        for filename in filesToLink:
            workspaceLinkOrCopy(filename, ref_workspace, sandbox_workspace, copyFiles=False)

        # for filename in ['local-xml', 'dyn-xml']:
        #     dirname = pathjoin(sandbox_workspace, filename)
        #     mkdirs(dirname)

        # if successful, remove semaphore
        os.remove(semaphore_file)

    def copy_sandbox_workspace(self):
        """
        Copy/link the sandbox's Workspace copy to the given sandbox scenario directory.

        :return: nothing
        """
        sandbox_workspace = self.sandbox_workspace
        sandbox_scenario_dir = self.sandbox_scenario_dir

        filesToCopy, filesToLink = getFilesToCopyAndLink('GCAM.SandboxFilesToLink')

        for filename in filesToCopy:
            workspaceLinkOrCopy(filename, sandbox_workspace, sandbox_scenario_dir, copyFiles=True)

        for filename in filesToLink:
            workspaceLinkOrCopy(filename, sandbox_workspace, sandbox_scenario_dir, copyFiles=False)

    def create_sandbox(self, force_create=False):
        """
        Set up a run-time sandbox in which to run GCAM. This involves copying
        from or linking to files and directories in sandbox's workspace, which defaults
        to the value of config parameter GCAM.SandboxWorkspace.

        :param force_create: (bool) if True, delete and recreate the sandbox
        :return: nothing
        """
        if force_create:
            _logger.debug(f"Removing sandbox '{self.sandbox_scenario_dir}' before recreating")
            removeTreeSafely(self.sandbox_scenario_dir)

        self.copy_ref_workspace(force_create=force_create)
        self.copy_sandbox_workspace()

        def make_subdirs(parent, *children):
            for child in children:
                pathjoin(parent, child, create=True)

        make_subdirs(self.sandbox_scenario_dir, OUTPUT_DIRNAME)
        make_subdirs(self.sandbox_exe_dir, 'restart', 'logs')

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

class FileMapper(AbstractFileMapper):
    def __init__(self, scenario, project_name=None, scenario_group=None,
                 parent=None, create_dirs=True): # , copy_workspace=False):
        """
        Create a Sandbox instance from the given arguments.

        :param scenario: (str) the name of a policy scenario
        :param project_name: (str) the name of the project, defaults to the value of
            config variable `GCAM.DefaultProject`
        :param scenario_group: (str) the name of a scenario group defined in scenarios.xml
        :param parent: (Sandbox) Sandbox parent scenario, generally a baseline in the same group
        :param create_dirs: (bool) whether to create some dirs
        :param copy_workspace: (bool) if True, copy the entire reference workspace without
            using symlinks. This may provide performance benefits on some cluster file systems.
        """
        super().__init__(scenario, project_name=project_name, scenario_group=scenario_group,
                         parent=parent, create_dirs=create_dirs)

        parent_mapper = self.parent_mapper    # may be computed by superclass
        self.parent_scenario_path = (self.gcam_path_from_abs(parent_mapper.sandbox_scenario_dir)
                                     if parent_mapper else None)

        # TBD: not implemented. Move this to SimFileMapper?
        # self.copy_workspace = copy_workspace or getParamAsBoolean("GCAM.CopyWorkspace")

        self.sandbox_workspace = getParamAsPath('GCAM.SandboxWorkspace')
        self.sandbox_workspace_exe_dir = getParamAsPath('GCAM.SandboxWorkspaceExeDir')

        self.sandbox_dir = getParamAsPath('GCAM.SandboxDir')

        self.sandbox_scenario_dir = sbx_scen_dir = makeDirPath(self.sandbox_dir, scenario)

        self.sandbox_exe_dir = makeDirPath(sbx_scen_dir, 'exe', create=create_dirs)
        self.sandbox_exe_path = pathjoin(self.sandbox_exe_dir, getParam('GCAM.Executable'))

        self.sandbox_output_dir = pathjoin(sbx_scen_dir, 'output')
        self.sandbox_xml_db = pathjoin(self.sandbox_output_dir, getParam('GCAM.DbFile'))
        self.sandbox_query_results_dir = pathjoin(sbx_scen_dir, QRESULTS_DIRNAME)
        self.sandbox_diffs_dir = pathjoin(sbx_scen_dir, DIFFS_DIRNAME)

        # In non-MCS Sandbox, the "local-xml" directory is at the same level as scenario dirs.
        # In the SimFileMapper, "local-xml" is under the sim directory (e.g., sims/s001).
        self.sandbox_local_xml = getParamAsPath('GCAM.SandboxLocalXml')

        self.sandbox_scenario_xml = makeDirPath(self.sandbox_local_xml, scenario, create=create_dirs)
        self.sandbox_dynamic_xml = pathjoin(self.sandbox_scenario_xml, 'dynamic')      # TBD: new subdir under local-xml

        self.sandbox_baseline_xml = (None if self.is_baseline
                                      else makeDirPath(self.sandbox_local_xml, self.baseline,
                                                       create=create_dirs))

        # In non-MCS Sandbox, config.xml is in '.../project/group/local-xml/scenario/config.xml'
        # In SimFileMapper, update_dependent_paths() relocates this to "sims/s{sim_id}/local-xml/config.xml"
        self.scenario_config_path = pathjoin(self.sandbox_scenario_xml, CONFIG_XML)

    def get_final_config(self):
        pmapper = self.parent_mapper
        parent_config_path = pmapper.config_path() if pmapper else getParam('GCAM.RefConfigFile')

        cfg_path = self.config_path()
        _logger.info("Copy %s\n      to %s", parent_config_path, cfg_path)
        shutil.copy(parent_config_path, cfg_path)
        os.chmod(cfg_path, 0o664)
        return cfg_path
