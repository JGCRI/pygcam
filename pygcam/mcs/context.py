'''
.. Copyright (c) 2017-2022 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
from ..config import getParam, getParamAsInt
from ..utils import mkdirs
from ..project import Project
from ..context import Context

from .error import PygcamMcsUserError

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


def dirFromNumber(n, prefix="", create=False):
    '''
    Compute a directory name using a 2-level directory structure that
    allows 1000 nodes at each level, accommodating up to 1 million files
    (0 to 999,999) in two levels.
    '''
    import math

    maxnodes = getParamAsInt('MCS.MaxSimDirs') or 1000

    # Require a power of 10
    log = math.log10(maxnodes)
    if log != int(log):
        raise PygcamMcsUserError("MaxSimDirs must be a power of 10 (default value is 1000)")
    log = int(log)

    level1 = n // maxnodes
    level2 = n % maxnodes

    directory = os.path.join(prefix, str(level1).zfill(log), str(level2).zfill(log))
    if create:
        mkdirs(directory)

    return directory


def getSimDir(simId, create=False):
    '''
    Return and optionally create the path to the top-level simulation
    directory for the given simulation number, based on the SimsDir
    parameter specified in the config file.
    '''
    simsDir = getParam('MCS.RunSimsDir')
    if not simsDir:
        raise PygcamMcsUserError("Missing required config parameter 'RunSimsDir'")

    simDir = os.path.join(simsDir, f's{simId:03d}')  # name is of format ".../s001/"
    if create:
        mkdirs(simDir)

    return simDir


class McsContext(Context):

    __slots__ = 'runId', 'simId', 'trialNum', 'status'      # in addition to those declared in Context class...

    instances = {}      # McsContext instances keyed by runId

    def __init__(self, projectName=None, scenario=None, baseline=None, groupName=None,
                 runId=None, simId=None, trialNum=None, status=None, store=True):

        super().__init__(projectName=projectName, scenario=scenario, baseline=baseline, groupName=groupName)

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

    def setVars(self, projectName=None, scenario=None, baseline=None, groupName=None,
                simId=None, trialNum=None, status=None):
        """
        Set instance vars of an McsContext for all args that are not None.
        """
        super().setVars(projectName=projectName, scenario=scenario, baseline=baseline, groupName=groupName)

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
        scenarioDir = os.path.join(trialDir, self.scenario)
        if create:
            mkdirs(scenarioDir)

        return scenarioDir

    def getQueryResultsDir(self):
        trialDir = self.getTrialDir()
        result = os.path.join(trialDir, self.scenario, 'queryResults')
        return result

    def getDiffsDir(self):
        trialDir = self.getTrialDir()
        result = os.path.join(trialDir, self.scenario, 'diffs')
        return result

    @property
    def groupDir(self):
        return self.groupName if self.useGroupDir else ''
