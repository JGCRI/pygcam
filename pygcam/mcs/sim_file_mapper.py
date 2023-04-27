#
# Support for creation and navigation of GCAM runtime sandboxes.
#
# Copyright (c) 2016 Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.
#
import os
from typing import Union

from ..config import getParam, getParamAsBoolean, getParamAsPath, setParam, mkdirs, pathjoin
from ..constants import (McsMode, LOCAL_XML_NAME, APP_XML_NAME, PARAMETERS_XML,
                         RESULTS_XML, CONFIG_XML)
from ..error import SetupException
from ..file_utils import pushd, removeTreeSafely, removeFileOrTree, symlink
from ..log import getLogger
from ..file_mapper import (AbstractFileMapper, FileMapper, getFilesToCopyAndLink,
                           workspaceLinkOrCopy, makeDirPath)
from ..tool import GcamTool
from ..xmlScenario import XMLScenario

from .context import McsContext

_logger = getLogger(__name__)

TRIAL_DATA_CSV = 'trial_data.csv'
ARGS_SAVE_FILE = 'gensim-args.txt'

class SimFileMapper(AbstractFileMapper):
    """
    A subclass of AbstractFileMapper that handles the slightly different structure required for
    Monte Carlo simulations. This is used by the gensim and runsim sub-commands.
    """
    def __init__(self, context=None, scenario=None, project_name=None,
                 scenario_group=None, sim_id=1, trial_count=None, trial_str=None,
                 param_file=None, parent=None, create_dirs=True):
        """
        Create an SimFileMapper instance from the given arguments.

        :param context: (McsContext) optional context object
        :param scenario: (str) the name of a scenario
        :param project_name: (str) the name of the project (and section of cfg file to use).
            Defaults to value of config parameter "GCAM.ProjectName".
        :param scenario_group: (str) the name of a scenario group defined in scenarios.xml
        :param sim_id: (int) the numerical ID of the simulation. Default is 1.
        :param trial_count: (int) the number of trials for this simulation
        :param trial_str: (str) representing the range trials for this simulation, e.g.,
            "0-999" or "1-6,7,9,100-599" and so on.
        :param param_file: (str) the pathname of an alternate parameters.xml file to use.
            Default is the value of config parameter "MCS.ProjectParametersFile"
        :param parent: (str) name of parent scenario, i.e., from which we inherit a config
            file as a starting point. Usually the baseline for a non-baseline scenario.
        :param create_dirs: (bool) whether to create some dirs
        """

        # Allow specific cmdline options to override context
        self.context = context
        project_name = (project_name or (context and context.projectName) or
                        getParam('GCAM.ProjectName') or None)
        scenario_group = scenario_group or (context and context.groupName) or None
        parent = parent or (context and context.baseline) or None
        scenario = scenario or (context and context.scenario) or None

        super().__init__(scenario, project_name=project_name, scenario_group=scenario_group,
                         parent=parent, create_dirs=False)

        self.sim_id = sim_id
        self.trial_count = trial_count
        self.trial_str = trial_str
        self.trial_xml_file = None          # Deprecated? Needed by xmlScenario

        self.db_dir = getParamAsPath('MCS.SandboxDbDir')
        self.project_parameters_file = getParamAsPath('MCS.ProjectParametersFile')
        self.project_results_file = getParamAsPath('MCS.ProjectResultsFile')
        self.run_root = getParamAsPath('MCS.SandboxRoot')
        self.sandbox_dir = getParamAsPath('MCS.SandboxDir')
        self.sandbox_workspace = getParamAsPath('MCS.SandboxWorkspace')
        self.sandbox_workspace_input_dir = getParamAsPath('MCS.SandboxWorkspaceInputDir')
        self.sim_root = sim_root = getParamAsPath('MCS.SandboxSimsDir')
        self.sim_dir = sim_dir = pathjoin(sim_root, f's{self.sim_id:03d}', create=True)

        self.trial_data_file = pathjoin(sim_dir, TRIAL_DATA_CSV)
        self.args_save_file  = pathjoin(sim_dir, ARGS_SAVE_FILE)
        self.sim_app_xml     = pathjoin(sim_dir, APP_XML_NAME, create=True)

        # TBD: still needed? This is a pretty confusing way to transmit info
        # Set some config parameter values so super().__init__ does the right thing
        setParam('GCAM.SandboxDir', getParamAsPath('MCS.SandboxDir'))
        setParam('GCAM.SandboxWorkspace', getParamAsPath('MCS.SandboxWorkspace'))

        # These files will be copied from the project directory to the sim's app-xml
        # directory for reference.
        self.app_xml_param_file   = pathjoin(self.sim_app_xml, PARAMETERS_XML)
        self.app_xml_results_file = pathjoin(self.sim_app_xml, RESULTS_XML)

        # In non-MCS Sandbox, the "local-xml" directory is at the same level as scenario dirs.
        # In the SimFileMapper, "local-xml" is under the sim directory (e.g., sims/s001/local-xml).
        self.sim_local_xml = pathjoin(sim_dir, LOCAL_XML_NAME, create=True)
        self.sandbox_local_xml = self.sim_local_xml # so generic methods work properly

        self.sandbox_baseline_xml = (None if self.is_baseline
                                      else makeDirPath(self.sandbox_local_xml, self.baseline,
                                                       create=create_dirs))
        if scenario:
            # When used by gensim, no scenario is identified
            self.sandbox_scenario_xml = makeDirPath(self.sandbox_local_xml, scenario, create=create_dirs)
            self.sandbox_dynamic_xml = pathjoin(self.sandbox_scenario_xml, 'dynamic')      # TBD: new subdir under local-xml
            self.scenario_config_path = pathjoin(self.sim_local_xml, scenario, CONFIG_XML)

            # Directories accessed from configuration XML files (so we store relative-to-exe and
            # absolute paths. Note that gcam_path requires self.sandbox_exe_dir to be set first.
            self.scenario_gcam_xml_dir = self.gcam_path('../input/gcamdata/xml')
        else:
            self.sandbox_scenario_xml = self.sandbox_dynamic_xml = None
            self.scenario_config_path = self.scenario_gcam_xml_dir = None

        # Reset dependent pathnames stored by FileMapper superclass
        trial_dir = self.trial_dir(create=True)

        # TBD: from update dependent paths
        if trial_dir:
            # trial_dir is None when running gensim since no trial_num is defined
            self.sandbox_scenario_dir = sbx_scen_dir = makeDirPath(trial_dir, scenario)
            self.sandbox_exe_dir = makeDirPath(sbx_scen_dir, 'exe', create=create_dirs)
            self.sandbox_exe_path = pathjoin(self.sandbox_exe_dir, getParam('GCAM.Executable'))

            self.sandbox_query_results_dir = pathjoin(sbx_scen_dir, 'queryResults')
            self.sandbox_diffs_dir = pathjoin(sbx_scen_dir, 'diffs')
            self.sandbox_output_dir = pathjoin(sbx_scen_dir, 'output')
            self.sandbox_xml_db = pathjoin(self.sandbox_output_dir, getParam('GCAM.DbFile'))

    # TBD: might not be useful since ivars are not reset to match context.
    #   Used only in one place and use is questionable.
    def set_context(self, ctx : McsContext):
        self.context = ctx

    def trial_scenario_dir(self, scenario=None, create=False):
        dir = self.trial_dir(context=self.context, create=create)
        path = pathjoin(dir, self.group_subdir, scenario or self.context.scenario)
        return path

    def trial_dir(self, context=None, create=False) -> str:
        """
        Get the trial directory for the given trial number (from ``context``).
        Can be called (e.g., by gensim) with no trial number, so trial dir
        cannot be computed.

        :param context: (McsContext) information describing this trial
        :param create: (bool) whether to create directories
        :return: (str) the pathname of the trial directory
        """
        from .util import dirFromNumber

        ctx = context or self.context
        if not ctx:
            return None

        trial_dir = dirFromNumber(ctx.trialNum, prefix=self.sim_dir, create=create)
        return trial_dir

    def get_sim_local_xml(self):
        return self.sim_local_xml

    def sim_local_xml_scenario(self, scenario, create=False):
        path = pathjoin(self.sim_local_xml, scenario, create=create)
        return path

    def get_scenarios_file(self):
        return self.scenarios_file  # TBD self.scenarios_file

    def scenario_config_file(self, scenario):
        """
        Returns the path to sim's copy of the config.xml file for the given scenario.
        """
        dir = self.sim_local_xml_scenario(scenario, create=True)
        configFile = pathjoin(dir, CONFIG_XML)
        return configFile

    def get_param_file(self):
        return self.project_parameters_file

    def get_scenario_group(self):
        return self.scenario_group  # TBD self.scenario_group

    def get_app_xml_param_file(self):
        return self.app_xml_param_file

    def get_app_xml_results_file(self):
        return self.app_xml_results_file

    def get_log_file(self):
        path = pathjoin(self.logs_dir, 'pygcam.log')
        return path

    def copy_ref_workspace(self, force_create=False, files_to_link_param=None):
        if getParamAsBoolean('GCAM.CopyAllFiles'):
            _logger.warn('GCAM.CopyAllFiles = True while running MCS. This will consume a lot of disk storage.')

        super().copy_ref_workspace(force_create=force_create, files_to_link_param='MCS.WorkspaceFilesToLink')

    def copy_app_xml_files(self):
        from ..file_utils import filecopy

        filecopy(self.project_results_file, self.get_app_xml_results_file())
        filecopy(self.project_parameters_file, self.get_app_xml_param_file())

    def create_sim(self, desc=''):
        """
        Add a simulation to the database. If ``self.sim_id`` is None, a new
        simulation and sim_id are created. If ``self.sim_id`` is not None,
        a simulation with that id is created, replacing any existing one
        with that id.

        :param desc: (str) Optional description of the simulation.
        :return: (int) simulation id.
        """
        from .database import getDatabase

        db = getDatabase()
        new_sim_id = db.createSim(self.trial_count, desc, simId=self.sim_id)
        return new_sim_id

    def create_database(self):
        '''
        Copies reference workspace to the MCS sandbox's workspace and, if ``trials``
        is non-zero, ensures database initialization.
        '''
        from .database import getDatabase
        from .XMLResultFile import XMLResultFile
        from ..utils import getResource

        db = getDatabase()  # ensures database initialization before adding output
        XMLResultFile.addOutputs()

        # Load SQL script to create convenient views
        text = getResource('mcs/etc/views.sql')
        db.executeScript(text=text)

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
        mkdirs(self.sim_dir)
        mkdirs(self.db_dir)

        # if self.copy_workspace:
        #     mkdirs(self.workspace_copy_dir)
            # TBD: copy ref workspace to self.workspace_copy_dir

    def create_output_dir(self, output_dir):
        removeFileOrTree(output_dir, raiseError=False)
        temp_output_dir = getParam('MCS.TempOutputDir')

        if temp_output_dir:
            from ..temp_file import getTempDir

            # We create this on /scratch which is purged automatically.
            new_dir = getTempDir(suffix='', tmpDir=temp_output_dir, delete=False)
            mkdirs(new_dir)
            _logger.debug("Creating '%s' link to %s", output_dir, new_dir)
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
        sandbox_scenario_dir = self.sandbox_scenario_dir

        mcs_mode = getParam('MCS.Mode')

        # TBD: take this from FileMapper, which should set these values in __init__()
        srcWorkspace = self.ref_workspace if mcs_mode == McsMode.GENSIM else getParam("GCAM.SandboxWorkspace")

        if os.path.lexists(sandbox_dir) and os.path.samefile(sandbox_dir, srcWorkspace):
            raise SetupException("The run sandbox is the same as the run workspace; no setup performed")

        # Deprecated. This doesn't run in non-MCS mode
        # MCS "gensim" sub-command creates a shared workspace; for non-MCS we do it here if needed
        # if not mcs_mode:
        #     self.copy_ref_workspace(srcWorkspace, force_create=force_create)

        if mcs_mode and getParamAsBoolean('GCAM.CopyAllFiles'):
            # Not prohibited; just a disk-hogging, suboptimal choice
            _logger.warn('GCAM.CopyAllFiles = True while running MCS')

        _logger.info("Setting up sandbox '%s'", sandbox_dir)

        if force_create or mcs_mode == McsMode.TRIAL:
            sandbox_scenario_xml = self.sandbox_scenario_xml

            # Delete the scenario directory under the sim-level local-xml directory
            # (.../sims/s001/local-xml/{scenario}) so the config file is recreated.
            sim_local_xml_scenario = self.sim_local_xml_scenario(self.scenario)

            # avoid deleting the current directory
            with pushd(os.path.dirname(sandbox_dir)):
                removeTreeSafely(sim_local_xml_scenario, ignore_errors=True)
                mkdirs(sim_local_xml_scenario)

                removeTreeSafely(sandbox_scenario_dir, ignore_errors=True)
                removeTreeSafely(sandbox_scenario_xml, ignore_errors=True)
                mkdirs(sandbox_scenario_xml)

                # TBD: mapper.create_dir_structure() creates these and "output" directory
                # also makes sandbox and sandbox/exe (needed for pushd to return to 'exe'
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

    def readTrialDataFile(self):
        """
        Load trial data (e.g., saved by writeTrialDataFile) and return a DataFrame
        """
        import pandas as pd

        df = pd.read_table(self.trial_data_file, sep=',', index_col='trialNum')
        return df

    def writeTrialDataFile(self, df):
        '''
        Save the trial DataFrame in the file 'trialData.csv' in the simDir.
        '''
        import pandas as pd

        data_file = self.trial_data_file

        # If the file exists, rename it trialData.csv-.
        try:
            os.rename(data_file, data_file + '-')
        except:
            pass

        df.to_csv(data_file, index_label='trialNum')

def mapper_for_mode(scenario, **kwargs) -> Union[AbstractFileMapper]:
    mcs_mode = getParam('MCS.Mode')

    if mcs_mode:
        tool = GcamTool.getInstance()
        mapper = tool.get_mapper() or SimFileMapper(scenario=scenario, **kwargs)
    else:
        mapper = FileMapper(scenario, **kwargs)

    return mapper
