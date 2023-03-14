'''
.. Copyright (c) 2017-2022 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from .util import getSimDir, dirFromNumber
from ..config import pathjoin, getParam
from ..project import Project

# def _getJobNum():
#     import re
#
#     batchSystem = getParam('MCS.BatchSystem')
#     job_id_var = getParam("%s.%s" % (batchSystem, 'JOB_ID_VAR'))
#     jobIdStr = os.getenv(job_id_var, '')
#
#     result = re.search('\d+', jobIdStr)
#     jobNum = int(result.group(0)) if result else os.getpid()
#     return jobNum

class McsContext(object):
    __slots__ = ('scenario', 'baseline', 'groupName', 'projectName', 'useGroupDir',
                 'runId', 'simId', 'trialNum', 'status')

    instances = {}      # McsContext instances keyed by runId

    def __init__(self, projectName=None, scenario=None, baseline=None, groupName=None,
                 runId=None, simId=None, trialNum=None, status=None, store=True):

        projectName = projectName or getParam('GCAM.ProjectName')
        self.projectName = projectName
        self.scenario = scenario
        self.baseline = baseline

        project = Project.readProjectFile(projectName)
        self.groupName = groupName or project.scenarioSetup.defaultGroup
        self.useGroupDir = project.scenarioGroup.useGroupDir
        self.groupDir = self.groupName if self.useGroupDir else ''

        self.runId = runId
        self.simId = simId
        self.trialNum = trialNum
        self.status = status

        if store and runId:
            self.saveRunInfo()

    def saveRunInfo(self):
        McsContext.instances[self.runId] = self
        return self

    @classmethod
    def getRunInfo(cls, runId):
        return cls.instances.get(runId, None)

    def __str__(self):
        idTail = str(id(self))[-6:] # show last 6 digits only; enough to distinguish objs
        return f"<McsClass id={idTail} scn={self.scenario} grp={self.groupName} use={self.useGroupDir} sim={self.simId} trl={self.trialNum} run={self.runId} sta={self.status}>"

    # TBD: not sure we should be setting anything but status here
    def setVars(self, projectName=None, scenario=None, baseline=None, groupName=None,
                simId=None, trialNum=None, status=None):
        """
        Set instance vars of an McsContext for all args that are not None.
        """
        if projectName:
            self.projectName = projectName

        if scenario:
            self.scenario = scenario

        if baseline:
            self.baseline = baseline

        if groupName:
            self.groupName = groupName

        if simId is not None:
            self.simId = int(simId)

        if trialNum is not None:
            self.trialNum = int(trialNum)

        if status:
            self.status = status

    def getSimDir(self, create=False):
        '''
        Return and optionally create the path to the directory for a given sim.
        '''
        return getSimDir(self.simId, create=create)

    def getTrialDir(self, create=False):
        '''
        Return and optionally create the path to the directory for a given trial.
        '''
        simDir = getSimDir(self.simId, create=False)
        trialDir = dirFromNumber(self.trialNum, prefix=simDir, create=create)
        return trialDir

    def getScenarioDir(self, create=False):
        '''
        Return and optionally create the path to the directory for a given experiment.
        '''
        trialDir = self.getTrialDir(create=False)
        scenarioDir = pathjoin(trialDir, self.scenario, create=create)

        return scenarioDir

    def getQueryResultsDir(self):
        scenarioDir = self.getScenarioDir()
        result = pathjoin(scenarioDir, 'queryResults')
        return result

    def getDiffsDir(self):
        scenarioDir = self.getScenarioDir()
        result = pathjoin(scenarioDir, 'diffs')
        return result

