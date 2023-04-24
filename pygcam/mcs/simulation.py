import os
from ..config import (getParam, getParamAsPath, setParam, pathjoin)
from ..constants import (LOCAL_XML_NAME, APP_XML_NAME, PARAMETERS_XML,
                         RESULTS_XML, CONFIG_XML)
from ..log import getLogger
from ..xmlScenario import XMLScenario

from .context import McsContext

_logger = getLogger(__name__)

TRIAL_DATA_CSV = 'trial_data.csv'
ARGS_SAVE_FILE = 'gensim-args.txt'

class Simulation(object):
    def __init__(self, project_name=None, group=None, sim_id=1, run_root=None,
                 trial_count=None, trial_str=None, param_file=None, context : McsContext=None):
        self.context = context
        self.sim_id = sim_id
        self.trial_count = trial_count
        self.trial_str = trial_str
        self.project_name = project_name or getParam('GCAM.ProjectName')
        self.scenario_group = group or '' # getParam('GCAM.ScenarioGroup')
        self.scenarios_file = getParamAsPath('GCAM.ScenariosFile')
        self.run_root = run_root or getParamAsPath('MCS.SandboxRoot')
        self.param_file = param_file or getParamAsPath('MCS.ProjectParametersFile')
        self.sandbox_workspace_input_dir = getParamAsPath('MCS.SandboxWorkspaceInputDir')
        self.group_subdir = ''

        self.project_results_file = getParamAsPath('MCS.ProjectResultsFile')

        scen_xml = XMLScenario.get_instance(self.scenarios_file)
        group_obj = scen_xml.getGroup(self.scenario_group)

        # set config params so other config-based path construction works
        if param_file:
            setParam('MCS.ProjectParametersFile', param_file)

        self.project_parameters_file = getParamAsPath('MCS.ProjectParametersFile')

        if project_name:
            # N.B. GCAM.DefaultProject is set in tool.py from global +P/--project arg
            setParam('GCAM.ProjectName', project_name)

        if group and group_obj.useGroupDir:
            # setParam('GCAM.ScenarioSubdir', group)   # this is set in project.py
            self.group_subdir = group

        if run_root:
            setParam('MCS.SandboxRoot', run_root)

        self.ref_workspace = getParamAsPath('GCAM.RefWorkspace')
        self.sandbox_workspace = getParamAsPath('MCS.SandboxWorkspace')

        # Deprecated?
        # self.workspace_local_xml = pathjoin(self.sandbox_workspace, LOCAL_XML_NAME)

        # MCS.SandboxDir = %(MCS.SandboxRoot)s/%(GCAM.ProjectName)s/%(GCAM.ProjectSubdir)s/%(GCAM.ScenarioGroup)s
        self.sandbox_dir = getParamAsPath('MCS.SandboxDir')

        sandbox_sims_dir = getParamAsPath('MCS.SandboxSimsDir')
        self.sim_dir = sim_dir = pathjoin(sandbox_sims_dir, f's{self.sim_id:03d}', create=True)

        self.trial_data_file = pathjoin(sim_dir, TRIAL_DATA_CSV)
        self.args_save_file  = pathjoin(sim_dir, ARGS_SAVE_FILE)
        self.sim_local_xml   = pathjoin(sim_dir, LOCAL_XML_NAME, create=True)
        self.sim_app_xml     = pathjoin(sim_dir, APP_XML_NAME, create=True)

        # These files will be copied from the project directory to the sim's app-xml
        # directory for reference.
        self.app_xml_param_file   = pathjoin(self.sim_app_xml, PARAMETERS_XML)
        self.app_xml_results_file = pathjoin(self.sim_app_xml, RESULTS_XML)

        self.ref_gcamdata_dir = getParam('GCAM.RefGcamData')    # used if running data system

    @classmethod
    def from_context(cls, ctx : McsContext):
        sim = cls(project_name=ctx.projectName, group=ctx.groupName, sim_id=ctx.simId, context=ctx)
        return sim

    def set_context(self, ctx : McsContext):
        self.context = ctx

    # TBD: may not need trial_num arg
    def trial_dir(self, context=None, trial_num=None, create=False) -> str:
        """
        Get the trial directory for the given trial number (from ``context``).

        :param context: (McsContext) information describing this trial
        :param trial_num: (int) optional trial number to use instead of ``context``.
        :param create: (bool) whether to create directories
        :return: (str) the pathname of the trial directory
        """
        from .util import dirFromNumber

        if trial_num is None:
            ctx = context or self.context
            trial_num = ctx.trialNum

        trial_dir = dirFromNumber(trial_num, prefix=self.sim_dir, create=create)
        return trial_dir

    def trial_scenario_dir(self, context, scenario=None, create=False):
        dir = self.trial_dir(context=context, create=create)
        path = pathjoin(dir, self.group_subdir, scenario or context.scenario)
        return path

    def trial_scenario_exe_dir(self, context, create=False):
        dir = self.trial_scenario_dir(context, create=create)
        path = pathjoin(dir, 'exe')
        return path

    # TBD: if we need a second local-xml under the trial rather than just the
    #  one under the sim. Though, we might just create baseline and policy
    #  folders under trial-xml and avoid some confusion.
    def trial_local_xml(self, context=None, create=False):
        """
        Requires self.context to be set before calling this without passing a ``context``.
        """
        context = context or self.context
        trial_dir = self.trial_dir(context=context, create=create)
        local_xml = pathjoin(trial_dir, LOCAL_XML_NAME, create=create)
        return local_xml

    def sim_local_xml_scenario(self, scenario, create=False):
        path = pathjoin(self.sim_local_xml, scenario, create=create)
        return path

    def scenario_config_file(self, scenario):
        """
        Returns the path to sim's copy of the config.xml file for the given scenario.
        If ``context`` is None, self.context is used.
        """
        dir = self.sim_local_xml_scenario(scenario, create=True)
        configFile = pathjoin(dir, CONFIG_XML)
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
