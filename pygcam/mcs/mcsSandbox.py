#
# Support for creation and navigation of GCAM runtime sandboxes.
#
# Copyright (c) 2016 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
#
import os
from ..config import getParam, getParamAsBoolean, mkdirs, pathjoin
from ..constants import LOCAL_XML_NAME, DYN_XML_NAME, McsMode
from ..error import SetupException
from ..file_utils import (pushd, removeTreeSafely, symlinkOrCopyFile,
                          removeFileOrTree, copyFileOrTree, symlink)
from ..log import getLogger
from ..sandbox import Sandbox, makeDirPath

# Creates a circular import.
#from .context import McsContext

from .error import PygcamMcsUserError

_logger = getLogger(__name__)

WORKSPACE_COPY_NAME = 'WorkspaceCopy'


def _workspaceLinkOrCopy(src, srcWorkspace, dstSandbox, copyFiles=False):
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


def _getFilesToCopyAndLink(linkParam):
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

#
# TBD: make this a method of McsSandbox
#
# Called only from setup_plugin.py and gensim_plugin.py
#
def copyRefWorkspace(newWorkspace, forceCreate=False, mcs=False):
    """
    Create a copy of a reference workspace by linking to or copying files from
    `refWorkspace`, which defaults to the value of config parameter
    GCAM.RunWorkspace. The copied workspace is the basis for creating sandboxes
    for a Monte Carlo simulation or a non-MCS project.

    :param newWorkspace: (str) the directory to create
    :param forceCreate: (bool) if True, delete and recreate the sandbox
    :param mcs: (bool) if True, perform setup appropriate for Monte Carlo trials.
    :return: none
    """
    version = getParam('GCAM.VersionNumber')
    _logger.info("Setting up GCAM workspace '%s' for GCAM %s", newWorkspace, version)

    refWorkspace = getParam('GCAM.RefWorkspace')
    if os.path.lexists(newWorkspace) and os.path.samefile(newWorkspace, refWorkspace):
        raise SetupException("run workspace is the same as reference workspace; no setup performed")

    # We write a semaphore file when creating Workspace to identify failures.
    # If we failed, we forceCreate on the next attempt. This prevents two users
    # from doing this at the same time, though it's probably overkill.
    # Updated 7/10/17: filelocking failed on Cray (NERSC) so was disabled for now.
    mkdirs(newWorkspace)
    semaphoreFile = pathjoin(newWorkspace, '.creation_semaphore')

    try:
        os.remove(semaphoreFile)
        forceCreate = True          # if we can remove it, last attempt failed
    except OSError as e:
        import errno
        if e.errno != errno.ENOENT: # ENOENT => no such file exists
            raise

    if mcs and getParamAsBoolean('GCAM.CopyAllFiles'):
        _logger.warn('GCAM.CopyAllFiles = True while running MCS. This will consume a lot of disk storage.')

    if forceCreate:
        _logger.info("Removing workspace '%s'", newWorkspace)
        removeTreeSafely(newWorkspace, ignore_errors=True)

    mkdirs(newWorkspace)
    open(semaphoreFile, 'w').close()    # create empty semaphore file

    # Spell out variable names rather than computing parameter names to
    # facilitate searching source files for parameter uses.
    paramName = 'MCS.WorkspaceFilesToLink' if mcs else 'GCAM.WorkspaceFilesToLink'

    filesToCopy, filesToLink = _getFilesToCopyAndLink(paramName)

    for filename in filesToCopy:
        _workspaceLinkOrCopy(filename, refWorkspace, newWorkspace, copyFiles=True)

    for filename in filesToLink:
        _workspaceLinkOrCopy(filename, refWorkspace, newWorkspace, copyFiles=False)

    for filename in [LOCAL_XML_NAME, DYN_XML_NAME]:
        dirname = pathjoin(newWorkspace, filename, create=True)

    # if successful, remove semaphore
    os.remove(semaphoreFile)


def createOutputDir(outputDir):
    from ..file_utils import removeFileOrTree
    from ..temp_file import getTempDir

    removeFileOrTree(outputDir, raiseError=False)
    tempOutputDir = getParam('MCS.TempOutputDir')

    if tempOutputDir:
        # We create this on /scratch which is purged automatically.
        newDir = getTempDir(suffix='', tmpDir=tempOutputDir, delete=False)
        mkdirs(newDir)
        _logger.debug("Creating '%s' link to %s" % (outputDir, newDir))
        symlink(newDir, outputDir)

    else:
        mkdirs(outputDir)


def sandbox_for_mode(scenario, **kwargs):
    mcs_mode = getParam('MCS.Mode')

    cls = McsSandbox if mcs_mode else Sandbox
    return cls(scenario, **kwargs)


# TBD: should this be created from, or combined with McsContext?
class McsSandbox(Sandbox):
    """
    A subclass of Sandbox that handles the slightly different structure required for
    Monte Carlo simulations. This is used by the gensim and runsim sub-commands.
    """
    def __init__(self, scenario, projectName=None, scenarioGroup=None,
                 parent=None, createDirs=True):
        """
        Create an McsSandbox instance from the given arguments.

        :param scenario: (str) the name of a policy scenario
        :param projectName: (str)
        :param scenarioGroup: (str) the name of a scenario group defined in scenarios.xml
        :param parent: (str)
        :param createDirs: (bool) whether to create some dirs
        """
        super().__init__(scenario, projectName=projectName, scenarioGroup=scenarioGroup,
                         parent=parent, createDirs=createDirs)

        # self.sim_id = sim_id
        self.mcs_sandbox_dir = getParam('MCS.SandboxDir') # default is {MCS.RunRoot}/{GCAM.ProjectName}

        self.sim_root = makeDirPath(self.mcs_sandbox_dir, scenarioGroup, self.scenario)

        self.db_dir = getParam('MCS.SandboxDbDir')

        # {McsRoot}/{ProjectName}/WorkspaceCopy
        self.workspace_copy_dir = pathjoin(self.mcs_root, WORKSPACE_COPY_NAME)

        # Override superclass setting, which is for non-MCS runs
        self.copy_workspace = getParamAsBoolean("MCS.CopyWorkspace")

        self.trial_xml_file = None


    # Use of McsContext creates a circular import
    # @classmethod
    # def sandbox_from_context(cls, context: McsContext):
    #     # TBD
    #     pass

    # TBD: rationalize these two methods
    @classmethod
    def get_sim_dir(cls, simId, create=False):
        '''
        Return and optionally create the path to the top-level simulation
        directory for the given simulation number, based on the SimsDir
        parameter specified in the config file.
        '''
        simsDir = getParam('MCS.SandboxSimsDir')
        if not simsDir:
            raise PygcamMcsUserError("Missing required config parameter 'MCS.SandboxSimsDir'")

        # name is of format ".../s001/"
        simDir = pathjoin(simsDir, f's{simId:03d}', create=create)

        return simDir

    def sim_dir(self, sim_id):
        path = pathjoin(self.sim_root, 'sims', f"s{sim_id:03d}")
        return path

    # Probably does not call super()
    def create_dir_structure(self):
        # TBD:
        #   Create optional local workspace: {McsRoot}/{ProjectName}/WorkspaceCopy. The
        #   implication here is that sims/s001, sims/s002, etc. all share the reference
        #   workspace. Need to allow an MCS subdir under {McsRoot}/{ProjectName} so one
        #   project can have multiple simulations using different versions of GCAM, i.e.,
        #   {McsRoot}/{ProjectName}/{optionalSimSubdir}/WorkspaceCopy
        #   -
        #   Create {McsRoot}/{ProjectName}/{optionalSimSubdir}/db and initialize the DB.
        #
        sim_id = 1  # TBD: where to get this?
        mkdirs(self.sim_dir(sim_id))

        mkdirs(self.db_dir)
        # TBD: initialize the database

        if self.copy_workspace:
            mkdirs(self.workspace_copy_dir)
            # TBD: copy ref workspace to self.workspace_copy_dir


    def create_sandbox(self, forceCreate=False):
        """
        Set up a run-time sandbox in which to run GCAM. This involves copying
        from or linking to files and directories in `workspace`, which defaults
        to the value of config parameter GCAM.SandboxWorkspace.

        Differs from non-MCS sandbox in terms of directory structure. Trial sandboxes are in
        {McsRoot}/{ProjectName}/{optionalSimSubdir}/sims/sNNN/xxx/yyy/{scenario}

        :param forceCreate: (bool) if True, delete and recreate the sandbox
        :return: nothing
        """
        from .util import dirFromNumber # TBD: subclass should live in mcs directory once fleshed out

        # N.B. does not call super().__init__() -- just overrides it

        trial_num = 0 # TBD: where to get this?
        scenario_dir = dirFromNumber(trial_num, prefix=self.sim_dir, create=True)

        sandbox = 'compute this'

        mcs_mode = getParam('MCS.Mode')

        # TBD: take this from Sandbox or McsSandbox, which should set these values in __init__()
        srcWorkspace = self.ref_workspace if mcs_mode == McsMode.GENSIM else getParam("GCAM.SandboxWorkspace")

        if os.path.lexists(sandbox) and os.path.samefile(sandbox, srcWorkspace):
            raise SetupException("The run sandbox is the same as the run workspace; no setup performed")

        # MCS "gensim" sub-command creates a shared workspace; for non-MCS we do it here if needed
        if not mcs_mode:
            copyRefWorkspace(srcWorkspace, forceCreate=forceCreate)

        if mcs_mode and getParamAsBoolean('GCAM.CopyAllFiles'):
            # Not prohibited; just a disk-hogging, suboptimal choice
            _logger.warn('GCAM.CopyAllFiles = True while running MCS')

        _logger.info("Setting up sandbox '%s'", sandbox)

        if forceCreate or mcs_mode == McsMode.TRIAL:
            # avoid deleting the current directory
            with pushd('..'):
                removeTreeSafely(sandbox, ignore_errors=True)
                mkdirs(sandbox)

        # also makes sandbox and sandbox/exe
        logPath = pathjoin(sandbox, 'exe', 'logs', create=True)

        restartDir = pathjoin(sandbox, 'exe', 'restart', create=True)

        filesToCopy, filesToLink = _getFilesToCopyAndLink('GCAM.SandboxFilesToLink')

        for filename in filesToCopy:
            _workspaceLinkOrCopy(filename, srcWorkspace, sandbox, copyFiles=True)

        for filename in filesToLink:
            _workspaceLinkOrCopy(filename, srcWorkspace, sandbox, copyFiles=False)

        outputDir = pathjoin(sandbox, 'output')

        if mcs_mode:  # i.e., mcs_mode is 'trial' or 'gensim'
            # link {sandbox}/dyn-xml to ../dyn-xml
            dynXmlDir = pathjoin('..', DYN_XML_NAME)

            dynXmlAbsPath = pathjoin(os.path.dirname(sandbox), DYN_XML_NAME, create=True)
            createOutputDir(outputDir)  # deals with link and tmp dir...
        else:
            # link {sandbox}/dyn-xml to {refWorkspace}/dyn-xml
            dynXmlDir = pathjoin(srcWorkspace, DYN_XML_NAME)

            # Create a local output dir
            mkdirs(outputDir)

        def _remakeSymLink(source, linkname):
            removeFileOrTree(linkname)
            symlinkOrCopyFile(source, linkname)

        dynXmlLink = pathjoin(sandbox, DYN_XML_NAME)
        _remakeSymLink(dynXmlDir, dynXmlLink)

        # static xml files are always linked to reference workspace
        localXmlDir = pathjoin(srcWorkspace, LOCAL_XML_NAME)
        localXmlLink = pathjoin(sandbox, LOCAL_XML_NAME)
        _remakeSymLink(localXmlDir, localXmlLink)
