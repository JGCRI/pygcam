import os
from ..config import (getParam, getParamAsPath, setParam, pathjoin)
from ..constants import LOCAL_XML_NAME, APP_XML_NAME, PARAMETERS_XML, RESULTS_XML
from ..log import getLogger
from ..xmlScenario import XMLScenario

from .context import McsContext
from .error import PygcamMcsUserError

_logger = getLogger(__name__)

TRIAL_DATA_CSV = 'trial_data.csv'
ARGS_SAVE_FILE = 'gensim-args.txt'

class Simulation(object):
    def __init__(self, project_name=None, group=None, sim_id=1, run_root=None,
                 trial_count=None, trial_str=None, param_file=None):
        self.sim_id = sim_id
        self.trial_count = trial_count
        self.trial_str = trial_str
        self.project_name = project_name or getParam('GCAM.ProjectName')
        self.scenario_group = group or getParam('GCAM.ScenarioGroup')
        self.scenarios_file = getParamAsPath('GCAM.ScenariosFile')
        self.run_root = run_root or getParamAsPath('MCS.SandboxRoot')
        self.param_file = param_file or getParamAsPath('MCS.ProjectParametersFile')
        self.sandbox_workspace_input_dir = getParamAsPath('MCS.SandboxWorkspaceInputDir')

        self.project_results_file = getParamAsPath('MCS.ProjectResultsFile')

        scen_xml = XMLScenario.get_instance(self.scenarios_file)
        group_obj = scen_xml.getGroup(self.scenario_group)

        # set config params so other config-based path construction works
        if param_file:
            setParam('MCS.ProjectParametersFile', param_file)

        if project_name:
            # N.B. GCAM.DefaultProject is set in tool.py from global +P/--project arg
            setParam('GCAM.ProjectName', project_name)

        if group and group_obj.useGroupDir:
            setParam('GCAM.ScenarioGroup', group)

        if run_root:
            setParam('MCS.SandboxRoot', run_root)

        self.ref_workspace = getParamAsPath('GCAM.RefWorkspace')
        self.sandbox_workspace = getParamAsPath('MCS.SandboxWorkspace')

        # Deprecated?
        # self.workspace_local_xml = pathjoin(self.sandbox_workspace, LOCAL_XML_NAME)

        # MCS.SandboxDir = %(MCS.SandboxRoot)s/%(GCAM.ProjectName)s/%(GCAM.ProjectSubdir)s/%(GCAM.ScenarioGroup)s
        self.sandbox_dir = getParamAsPath('MCS.SandboxDir')

        sandbox_sims_dir = getParamAsPath('MCS.SandboxSimsDir')
        if not sandbox_sims_dir:
            raise PygcamMcsUserError("Missing required config parameter 'MCS.SandboxSimsDir'")

        self.sim_dir = sim_dir = pathjoin(sandbox_sims_dir, f's{self.sim_id:03d}', create=True)

        self.trial_data_file = pathjoin(sim_dir, TRIAL_DATA_CSV)
        self.args_save_file  = pathjoin(sim_dir, ARGS_SAVE_FILE)
        # self.sim_input_dir   = pathjoin(sim_dir, 'input')                       # TBD: should be inside scenario dir
        self.sim_local_xml   = pathjoin(sim_dir, LOCAL_XML_NAME, create=True)
        self.sim_app_xml     = pathjoin(sim_dir, APP_XML_NAME, create=True)

        # These files will be copied from the project directory to the sim's app-xml
        # directory for reference.
        self.app_xml_param_file   = pathjoin(self.sim_app_xml, PARAMETERS_XML)
        self.app_xml_results_file = pathjoin(self.sim_app_xml, RESULTS_XML)

        self.ref_gcamdata_dir = getParam('GCAM.RefGcamData')    # used if running data system

    @classmethod
    def from_context(cls, ctx : McsContext):
        sim = cls(project_name=ctx.projectName, group=ctx.groupName, sim_id=ctx.simId)
        return sim

    # TBD: if we need a second local-xml under the trial rather than just the
    #  one under the sim. Though, we might just create baseline and policy
    #  folders under trial-xml and avoid some confusion.
    def trial_local_xml(self, context):
        pass

    def scenario_local_xml(self, context):
        path = pathjoin(self.sim_local_xml, context.scenario)
        return path

    def scenario_config_file(self, context):
        """
        Returns the path to sim's copy of the config.xml file for the given scenario.
        """
        from ..constants import CONFIG_XML

        scen_dir = self.scenario_local_xml(context)
        configFile = pathjoin(scen_dir, CONFIG_XML)
        return configFile

    def create_database(self):
        '''
        Copies reference workspace to the MCS sandbox's workspace and, if ``trials``
        is non-zero, ensures database initialization.
        '''
        from .Database import getDatabase
        from .XMLResultFile import XMLResultFile
        from ..utils import getResource

        db = getDatabase()  # ensures database initialization before adding output
        XMLResultFile.addOutputs()

        # Load SQL script to create convenient views
        text = getResource('mcs/etc/views.sql')
        db.executeScript(text=text)

    def create_sim(self, desc=''):
        """
        Add a simulation to the database. If ``self.sim_id`` is None, a new
        simulation and sim_id are created. If ``self.sim_id`` is not None,
        a simulation with that id is created, replacing any existing one
        with that id.

        :param desc: (str) Optional description of the simulation.
        :return: (int) simulation id.
        """
        from .Database import getDatabase

        db = getDatabase()
        new_sim_id = db.createSim(self.trial_count, desc, simId=self.sim_id)
        return new_sim_id

    def writeTrialDataFile(self, df):
        '''
        Save the trial DataFrame in the file 'trialData.csv' in the simDir.
        '''
        data_file = self.trial_data_file

        # If the file exists, rename it trialData.csv-.
        try:
            os.rename(data_file, data_file + '-')
        except:
            pass

        df.to_csv(data_file, index_label='trialNum')

    def readTrialDataFile(self):
        """
        Load trial data (e.g., saved by writeTrialDataFile) and return a DataFrame
        """
        import pandas as pd

        df = pd.read_table(self.trial_data_file, sep=',', index_col='trialNum')
        return df
