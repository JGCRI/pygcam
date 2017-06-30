'''
.. The "gt" (gcamtool) commandline program

.. Copyright (c) 2017 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
from pygcam.config import getParam, getParamAsInt
from pygcam.utils import mkdirs
from .error import PygcamMcsUserError

def _getJobNum():
    import re

    batchSystem = getParam('MCS.BatchSystem')
    job_id_var = getParam("%s.%s" % (batchSystem, 'JOB_ID_VAR'))
    jobIdStr = os.getenv(job_id_var, '')

    result = re.search('\d+', jobIdStr)
    jobNum = int(result.group(0)) if result else os.getpid()
    return jobNum


def _dirFromNumber(n, prefix="", create=False):
    '''
    Compute a directory name using a 2-level directory structure that
    allows 1000 nodes at each level, accommodating up to 1 million files
    (0 to 999,999) in two levels.
    '''
    from numpy import log10     # lazy import

    maxnodes = getParamAsInt('MCS.MaxSimDirs') or 1000

    # Require a power of 10
    log = log10(maxnodes)
    if log != int(log):
        raise PygcamMcsUserError("MaxSimDirs must be a power of 10 (default value is 1000)")
    log = int(log)

    level1 = n / maxnodes
    level2 = n % maxnodes

    directory = os.path.join(prefix, str(level1).zfill(log), str(level2).zfill(log))
    if create:
        mkdirs(directory)

    return directory


# Deprecated
# def getLogDir(simId, create=False):
#     '''
#     :param simId: simulation id
#     :param create: if True, create the directory if needed
#     :return: the pathname of the log directory
#     '''
#     simDir = getSimDir(simId, create=create)
#     logDir = os.path.join(simDir, 'log')
#     if create:
#         mkdirs(logDir)
#
#     return logDir


def getSimDir(simId, create=False):
    '''
    Return and optionally create the path to the top-level simulation
    directory for the given simulation number, based on the SimsDir
    parameter specified in the config file.
    '''
    simsDir = getParam('MCS.RunSimsDir')
    if not simsDir:
        raise PygcamMcsUserError("Missing required config parameter 'RunSimsDir'")

    simDir = os.path.join(simsDir, 's%03d' % simId)  # name is of format ".../s001/"
    if create:
        mkdirs(simDir)

    return simDir


class Context(object):

    __slots__ = ['runId', 'simId', 'trialNum', 'expName', 'baseline',
                 'groupName', 'appName', 'jobNum']

    def __init__(self, runId=None, appName=None, simId=None, trialNum=None,
                 expName=None, baseline=None, groupName=None):
        self.runId     = runId
        self.simId     = simId
        self.trialNum  = trialNum
        self.expName   = expName        # TBD: change to scenario?
        self.baseline  = baseline
        self.groupName = groupName
        self.appName   = appName        # TBD: change to projectName
        self.jobNum    = _getJobNum()

    def __str__(self):
        return "<Context proj=%s exp=%s grp=%s sim=%s trial=%s run=%s job=%s>" % \
               (self.appName, self.expName, self.groupName,
                self.simId, self.trialNum, self.runId, self.jobNum)

    def setVars(self, appName=None, simId=None, trialNum=None, expName=None,
                baseline=None, groupName=None):
        '''
        Set elements of a context structure for all args that are not None.
        '''
        if appName:
            self.appName = appName

        if simId is not None:
            self.simId = int(simId)

        if trialNum is not None:
            self.trialNum = int(trialNum)

        if expName:
            self.expName = expName

        if baseline:
            self.baseline = baseline

        if groupName:
            self.groupName = groupName

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
        trialDir = _dirFromNumber(self.trialNum, prefix=simDir, create=create)
        return trialDir

    # TBD: change to getScenarioDir
    def getExpDir(self, create=False):
        '''
        Return and optionally create the path to the directory for a given experiment.
        '''
        trialDir = self.getTrialDir(create=False)
        expDir = os.path.join(trialDir, self.expName)
        if create:
            mkdirs(expDir)

        return expDir

    # def getLogDir(self, create=False):
    #     return getLogDir(self.simId, create=create)
