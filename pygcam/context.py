from .config import getParam, pathjoin
from .file_utils import mkdirs
from .project import Project

class Context(object):
    __slots__ = 'scenario', 'baseline', 'groupName', 'projectName', 'useGroupDir'

    def __init__(self, projectName=None, scenario=None, baseline=None, groupName=None):
        self.scenario = scenario
        self.baseline = baseline

        self.projectName = projectName = projectName or getParam('GCAM.ProjectName')

        project = Project.readProjectFile(projectName)
        self.groupName = groupName or project.scenarioSetup.defaultGroup
        self.useGroupDir = project.scenarioGroup.useGroupDir

    def __str__(self):
        idTail = str(id(self))[-6:] # show last 6 digits only; enough to distinguish objs
        return f"<Context id={idTail} scn={self.scenario} grp={self.groupName} use={self.useGroupDir}>"

    @property
    def groupDir(self):
        return self.groupName if self.useGroupDir else ''

    def setVars(self, projectName=None, scenario=None, baseline=None, groupName=None):
        '''
        Set elements of a context structure for all args that are not None.
        '''
        if projectName:
            self.projectName = projectName

        if scenario:
            self.scenario = scenario

        if baseline:
            self.baseline = baseline

        if groupName:
            self.groupName = groupName

    # TBD: Should this be consolidated here or in Sandbox?
    #      Perhaps Sandbox.__init__() should take a Context instance?
    def getScenarioDir(self, create=False):
        '''
        Return and optionally create the path to the directory for a given experiment.
        '''
        sandbox_root = getParam('GCAM.SandboxRoot')
        scenarioDir = pathjoin(sandbox_root, self.groupDir, self.scenario)
        if create:
            mkdirs(scenarioDir)

        return scenarioDir

    def getQueryResultsDir(self):
        scenarioDir = self.getScenarioDir()
        result = pathjoin(scenarioDir, 'queryResults')
        return result

    def getDiffsDir(self):
        scenarioDir = self.getScenarioDir()
        result = pathjoin(scenarioDir, 'diffs')
        return result

