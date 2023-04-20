#
# Support for creation and navigation of GCAM runtime sandboxes.
#
# Copyright (c) 2016 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
#
import glob
import os

from .config import getParam, getParamAsBoolean, getParamAsPath, setParam, pathjoin, unixPath, mkdirs
from .constants import LOCAL_XML_NAME, CONFIG_XML
from .error import SetupException
from .file_utils import removeTreeSafely, removeFileOrTree, copyFileOrTree, symlinkOrCopyFile
from .log import getLogger

_logger = getLogger(__name__)


def makeDirPath(*elements, require=False, normpath=True, create=False):
    """
    Join the tuple of elements to create a path to a directory,
    optionally checking that it exists or creating intermediate
    directories as needed.

    :param elements: a tuple of pathname elements to join
    :param require: if True, raise an error if the path doesn't exist
    :param normpath: if True, normalize the path
    :param create: if True, create the path if it doesn't exist
    :return: the joined path
    :raises: pygcam.error.SetupException
    """
    non_empty = [e for e in elements if e]
    path = pathjoin(*non_empty, normpath=normpath)

    if (create or require) and not os.path.lexists(path):
        if create:
            _logger.debug(f"Creating directory '{path}'")
            mkdirs(path)
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


def copy_ref_workspace(ref_workspace, new_workspace,
                       force_create=False, files_to_link_param=None):
    """
    Copy/link the reference workspace to the given sandbox Workspace directory.

    :return: nothing
    """
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


    # Allows override from McsSandbox when calling super().__init__()
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

# TBD: incomplete
#   -
#   Maybe xmlSetup should be the only approach rather than supporting original setup subclasses.
#   (Though this is the method for users to add @callable methods called from scenarios.xml.)
#   This way we can assume scenario definition exists in xml format and create an API to get the
#   information about any scenario definition from xmlSetup.py.

class Sandbox(object):
    def __init__(self, scenario, projectName=None, scenario_group=None,
                 parent=None, create_dirs=True, copy_workspace=False):
        """
        Create a Sandbox instance from the given arguments.

        :param scenario: (str) the name of a policy scenario
        :param projectName: (str) the name of the project, defaults to the value of
            config variable `GCAM.DefaultProject`
        :param scenario_group: (str) the name of a scenario group defined in scenarios.xml
        :param parent: (Sandbox) Sandbox parent scenario, generally a baseline in the same group
        :param create_dirs: (bool) whether to create some dirs
        :param copy_workspace: (bool) if True, copy the entire reference workspace without
            using symlinks. This may provide performance benefits on some cluster file systems.
        """
        from .xmlScenario import XMLScenario

        self.scenario = scenario
        self.parent = parent
        self.mcs_mode = getParam('MCS.Mode')
        self.project_name = projectName or getParam('GCAM.ProjectName')

        # Deprecated?
        # Ensure that GCAM.ScenarioGroup is set since system.cfg uses this in path construction
        # if scenario_group:
        #     setParam('GCAM.ScenarioGroup', scenario_group)

        self.scenarios_file = getParam('GCAM.ScenariosFile')
        self.scenario_group = scenario_group or ''

        scen_xml = XMLScenario.get_instance(self.scenarios_file)
        group_obj = scen_xml.getGroup(self.scenario_group)
        self.baseline = group_obj.baseline

        scen_obj = group_obj.getFinalScenario(scenario)
        self.is_baseline = scen_obj.isBaseline

        if not (self.parent or self.is_baseline):
            # TBD: Modify to support out-of-scenario-group parent after groupSource
            #      logic is moved to ScenarioGroup (see xmlScenario.py)
            # Create Sandbox (or McsSandbox) for baseline scenario so we can grab it's config.xml
            self.parent = self.__class__(self.baseline,
                                         projectName=projectName,
                                         scenario_group=scenario_group)

        # TBD
        # self.baseline_context = None if self.is_baseline else self.fromXmlSetup(scenario_group, baseline)

        # TBD: not yet implemented.
        self.copy_workspace = copy_workspace or getParamAsBoolean("GCAM.CopyWorkspace")

        self.ref_workspace = getParamAsPath('GCAM.RefWorkspace')
        self.ref_workspace_exe_dir = getParamAsPath("GCAM.RefExeDir")

        self.sandbox_workspace = getParamAsPath('GCAM.SandboxWorkspace')
        self.sandbox_workspace_exe_dir = getParamAsPath('GCAM.SandboxWorkspaceExeDir')

        # The following are set in self.update_dependent_paths()
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

        self.update_dependent_paths(getParamAsPath('GCAM.SandboxDir'), scenario,
                                    create_dirs=create_dirs)

        self.project_xml_src = getParamAsPath('GCAM.ProjectXmlsrc')
        self.project_scenario_xml_src = pathjoin(self.project_xml_src, scenario)

        # Directories accessed from configuration XML files (so we store relative-to-exe and
        # absolute paths. Note that gcam_path requires self.sandbox_exe_dir to be set first.
        self.scenario_gcam_xml_dir = self.gcam_path('../input/gcamdata/xml')

        parent = self.parent
        self.parent_scenario_path = self.gcam_path_from_abs(parent.sandbox_scenario_dir) if parent else None

    def update_dependent_paths(self, sandbox_dir, scenario, create_dirs=True):
        self.sandbox_dir = sandbox_dir
        self.sandbox_scenario_dir = makeDirPath(self.sandbox_dir, scenario)
        self.sandbox_exe_dir = makeDirPath(self.sandbox_scenario_dir, 'exe', create=create_dirs)
        self.sandbox_exe_path = pathjoin(self.sandbox_exe_dir, getParam('GCAM.Executable'))

        self.sandbox_output_dir = pathjoin(self.sandbox_scenario_dir, 'output')
        self.sandbox_xml_db = pathjoin(self.sandbox_output_dir, getParam('GCAM.DbFile'))

        self.sandbox_query_results_dir = pathjoin(self.sandbox_scenario_dir, 'queryResults')

        self.sandbox_diffs_dir = pathjoin(self.sandbox_scenario_dir, 'diffs')

        # The "local-xml" directory is always found at the same level as scenario dirs
        self.sandbox_local_xml = pathjoin(self.sandbox_scenario_dir, "..", LOCAL_XML_NAME, normpath=True)
        self.sandbox_scenario_xml = makeDirPath(self.sandbox_local_xml, scenario, create=create_dirs)

        self.sandbox_dynamic_xml = pathjoin(self.sandbox_scenario_xml, 'dynamic')      # TBD: new subdir under local-xml

        self.sandbox_baseline_xml = (None if self.is_baseline
                                      else makeDirPath(self.sandbox_local_xml, self.baseline,
                                                       create=create_dirs))

        # Store scenario config.xml in '.../project/group/local-xml/scenario/config.xml'
        self.scenario_config_path = pathjoin(self.sandbox_scenario_xml, CONFIG_XML)

    @classmethod
    def fromXmlSetup(cls, scenario_group, scenario):
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

    def config_path(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        return self.scenario_config_path

    def copy_ref_workspace(self, force_create=False, files_to_link_param=None):
        """
        Convenience method just calls global function with instance vars.

        :return: nothing
        """
        copy_ref_workspace(self.ref_workspace, self.sandbox_workspace,
                           force_create=force_create,
                           files_to_link_param=files_to_link_param)

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

    def create_dir_structure(self, force_create=False):
        """
        Create the directories required in the runtime structure for non-MCS GCAM runs.
        Optionally, this includes a local copy of the full reference workspace, to
        ensure isolation from changes to the reference workspace.

        :return: nothing
        """
        self.copy_ref_workspace(force_create=force_create)
        self.copy_sandbox_workspace()

        def create_subdirs(parent, *children):
            for child in children:
                pathjoin(parent, child, create=True)

        create_subdirs(self.sandbox_scenario_dir, 'output')
        create_subdirs(self.sandbox_exe_dir, 'restart', 'logs')

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

        self.create_dir_structure()

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


