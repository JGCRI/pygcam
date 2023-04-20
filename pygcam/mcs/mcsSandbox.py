#
# Support for creation and navigation of GCAM runtime sandboxes.
#
# Copyright (c) 2016 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
#
import os
from typing import Union

from ..config import getParam, getParamAsBoolean, getParamAsPath, setParam, mkdirs, pathjoin
from ..constants import McsMode
from ..error import SetupException
from ..file_utils import pushd, removeTreeSafely, removeFileOrTree, symlink
from ..log import getLogger
from ..sandbox import Sandbox, getFilesToCopyAndLink, workspaceLinkOrCopy
from ..tool import GcamTool

_logger = getLogger(__name__)


# TBD: should this be created from, or combined with McsContext?
class McsSandbox(Sandbox):
    """
    A subclass of Sandbox that handles the slightly different structure required for
    Monte Carlo simulations. This is used by the gensim and runsim sub-commands.
    """
    def __init__(self, scenario, projectName=None, scenario_group=None,
                 sim=None, parent=None, create_dirs=True):
        """
        Create an McsSandbox instance from the given arguments.

        :param scenario: (str) the name of a scenario
        :param projectName: (str)
        :param scenario_group: (str) the name of a scenario group defined in scenarios.xml
        :param sim: (Simulation) a simulation instance
        :param parent: (str) name of parent scenario, i.e., from which we inherit a config
            file as a starting point. Usually the baseline for a non-baseline scenario.
        :param create_dirs: (bool) whether to create some dirs
        """
        # TBD: pass as keyword args to __init__?
        # Set some config parameter values so super().__init__ does the right thing
        setParam('GCAM.SandboxDir', getParamAsPath('MCS.SandboxDir'))
        setParam('GCAM.SandboxWorkspace', getParamAsPath('MCS.SandboxWorkspace'))

        copy_workspace = getParamAsBoolean('MCS.CopyWorkspace')

        super().__init__(scenario, projectName=projectName, scenario_group=scenario_group,
                         parent=parent, create_dirs=False, copy_workspace=copy_workspace)

        # self.sim_id = sim_id
        self.sim_root = getParamAsPath('MCS.SandboxSimsDir')
        self.db_dir = getParamAsPath('MCS.SandboxDbDir')

        self.sim = sim or GcamTool.getInstance().get_sim()
        self.trial_xml_file = None

        # Reset dependent pathnames stored by Sandbox superclass
        trial_dir = sim.trial_dir(create=True)
        self.update_dependent_paths(trial_dir, scenario, create_dirs=create_dirs)

    def copy_ref_workspace(self, src_workspace, force_create=False):
        if getParamAsBoolean('GCAM.CopyAllFiles'):
            _logger.warn('GCAM.CopyAllFiles = True while running MCS. This will consume a lot of disk storage.')

        super().__init__(force_create=force_create, files_to_link_param='MCS.WorkspaceFilesToLink')


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
        mkdirs(self.sim.sim_dir)

        mkdirs(self.db_dir)
        # TBD: initialize the database

        if self.copy_workspace:
            mkdirs(self.workspace_copy_dir)
            # TBD: copy ref workspace to self.workspace_copy_dir

    def create_output_dir(self, output_dir):
        removeFileOrTree(output_dir, raiseError=False)
        temp_output_dir = getParam('MCS.TempOutputDir')

        if temp_output_dir:
            from ..temp_file import getTempDir

            # We create this on /scratch which is purged automatically.
            new_dir = getTempDir(suffix='', tmpDir=temp_output_dir, delete=False)
            mkdirs(new_dir)
            _logger.debug("Creating '%s' link to %s" % (output_dir, new_dir))
            symlink(new_dir, output_dir)

        else:
            mkdirs(output_dir)

    # TBD: needs a lot of work!
    def create_sandbox(self, force_create=False):
        """
        Set up a run-time sandbox in which to run GCAM. This involves copying
        from or linking to files and directories in `workspace`, which defaults
        to the value of config parameter GCAM.SandboxWorkspace.

        Differs from non-MCS sandbox in terms of directory structure. Trial sandboxes are in
        {McsRoot}/{ProjectName}/{optionalSimSubdir}/sims/sNNN/xxx/yyy/{scenario}

        :param force_create: (bool) if True, delete and recreate the sandbox
        :return: nothing
        """

        # N.B. does not call super().__init__() -- just overrides it?

        sandbox_dir = self.sandbox_dir

        mcs_mode = getParam('MCS.Mode')

        # TBD: take this from Sandbox or McsSandbox, which should set these values in __init__()
        srcWorkspace = self.ref_workspace if mcs_mode == McsMode.GENSIM else getParam("GCAM.SandboxWorkspace")

        if os.path.lexists(sandbox_dir) and os.path.samefile(sandbox_dir, srcWorkspace):
            raise SetupException("The run sandbox is the same as the run workspace; no setup performed")

        # MCS "gensim" sub-command creates a shared workspace; for non-MCS we do it here if needed
        if not mcs_mode:
            self.copy_ref_workspace(srcWorkspace, force_create=force_create)

        if mcs_mode and getParamAsBoolean('GCAM.CopyAllFiles'):
            # Not prohibited; just a disk-hogging, suboptimal choice
            _logger.warn('GCAM.CopyAllFiles = True while running MCS')

        _logger.info("Setting up sandbox '%s'", sandbox_dir)

        if force_create or mcs_mode == McsMode.TRIAL:
            # avoid deleting the current directory
            with pushd('..'):
                removeTreeSafely(sandbox_dir, ignore_errors=True)
                mkdirs(sandbox_dir)

        # also makes sandbox and sandbox/exe
        sandbox_scenario_dir = self.sandbox_scenario_dir
        self.logs_dir = pathjoin(sandbox_scenario_dir, 'exe', 'logs', create=True)
        pathjoin(sandbox_scenario_dir, 'exe', 'restart', create=True)

        filesToCopy, filesToLink = getFilesToCopyAndLink('GCAM.SandboxFilesToLink')

        for filename in filesToCopy:
            workspaceLinkOrCopy(filename, srcWorkspace, sandbox_scenario_dir, copyFiles=True)

        for filename in filesToLink:
            workspaceLinkOrCopy(filename, srcWorkspace, sandbox_scenario_dir, copyFiles=False)

        output_dir = pathjoin(sandbox_scenario_dir, 'output')

        if mcs_mode:  # i.e., mcs_mode is 'trial' or 'gensim'
            # link {sandbox}/dyn-xml to ../dyn-xml
            # dynXmlDir = pathjoin('..', DYN_XML_NAME)

            # Deprecated?
            #  dynXmlAbsPath = pathjoin(os.path.dirname(sandbox_dir), DYN_XML_NAME, create=True)

            self.create_output_dir(output_dir)  # deals with link and tmp dir...
        else:
            # link {sandbox}/dyn-xml to {refWorkspace}/dyn-xml
            # dynXmlDir = pathjoin(srcWorkspace, DYN_XML_NAME)

            # Create a local output dir
            mkdirs(output_dir)

        # def _remakeSymLink(source, linkname):
        #     removeFileOrTree(linkname)
        #     symlinkOrCopyFile(source, linkname)
        #
        # dynXmlLink = pathjoin(sandbox_dir, DYN_XML_NAME)
        # _remakeSymLink(dynXmlDir, dynXmlLink)
        #
        # # static xml files are always linked to reference workspace
        # localXmlDir = pathjoin(srcWorkspace, LOCAL_XML_NAME)
        # localXmlLink = pathjoin(sandbox_dir, LOCAL_XML_NAME)
        # _remakeSymLink(localXmlDir, localXmlLink)


def sandbox_for_mode(scenario, **kwargs) -> Union[Sandbox, McsSandbox]:
    mcs_mode = getParam('MCS.Mode')

    if mcs_mode:
        tool = GcamTool.getInstance()
        sim = tool.get_sim()
        sbx = McsSandbox(scenario, sim=sim, **kwargs)
    else:
        sbx = Sandbox(scenario, **kwargs)

    return sbx
