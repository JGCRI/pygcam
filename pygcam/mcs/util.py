# @author: Richard Plevin
# @author: Sam Fendell
#
# Copyright (c) 2012-2015. The Regents of the University of California (Regents)
# and Richard Plevin. See the file COPYRIGHT.txt for details.

# TBD: eliminate redundancies with pygcam

from __future__ import with_statement, print_function

import os
import re
from inspect import stack, getargspec

from pygcam.config import setSection, getSection, getParam, getParamAsInt
from pygcam.log import getLogger
from pygcam.utils import mkdirs

from .error import BaseSpecError, PygcamMcsUserError, PygcamMcsSystemError
from .constants import COMMENT_CHAR

_logger = getLogger(__name__)

_activeYearStrs = None
_activeYearInts = None

def writeTrialDataFile(simId, df):
    '''
    Save the trial DataFrame in the file 'trialData.csv' in the simDir.
    '''
    simDir = getSimDir(simId)
    dataFile = os.path.join(simDir, 'trialData.csv')

    # If the file exists, rename it trialData.csv-.
    try:
        os.rename(dataFile, dataFile + '-')
    except:
        pass

    df.to_csv(dataFile, index_label='trialNum')


def readTrialDataFile(simId):
    """
    Load trial data (e.g., saved by writeTrialDataFile) and return a DataFrame
    """
    import pandas as pd

    simDir = getSimDir(simId)

    # If SALib version exists, use it; otherwise use legacy file
    dataFile = os.path.join(simDir, 'data.sa', 'inputs.csv')
    if not os.path.lexists(dataFile):
        dataFile = os.path.join(simDir, 'trialData.csv')

    df = pd.read_table(dataFile, sep=',', index_col='trialNum')
    return df
    # return df.as_matrix()

def activeYears(asInt=False):
    '''
    Convert a string identifying active years into a list of ints or strs. Values must
    be comma-separated integers or expressions of the form xxxx-yyyy or xxxx-yyyy:z. The
    two expressions indicate ranges of years, with a default timestep of 5 years. If
    given, the final value after the colon indicates an alternative timestep.
    '''
    global _activeYearInts
    global _activeYearStrs

    # return cached values or compute and cache result
    if not _activeYearStrs:
        import re

        def reducer(lst, item):
            m = re.match(r"^(\d{4})-(\d{4})(?::(\d+))?$", item)
            if m:
                start = int(m.group(1))
                end = int(m.group(2))
                step = int(m.group(3)) if m.lastindex == 3 else 5    # default 5 yr timestep
                rng = range(start, end + 1, step)
                lst.extend(rng)
            elif item.isdigit():
                lst.append(int(item))
            else:
                raise PygcamMcsUserError('Element in list of active years is not an integer: %s' % item)

            return lst

        yearStr = getParam('MCS.Years')
        items = yearStr.split(',')
        years = reduce(reducer, items, [])

        _activeYearInts = map(int, years)
        _activeYearStrs = map(str, years)

    return _activeYearInts if asInt else _activeYearStrs

def stripYearPrefix(s):
    '''
    If s is of the form y + 4 digits, remove the y and convert the rest to integer
    '''
    if len(s) == 5 and s[0] == 'y':
        try:
            return int(s[1:])
        except ValueError:
            pass
    return s

#
# TBD: the whole "context" approach may be obsolete with ipp master/worker setup
#
class Context(object):
    def __init__(self, simId, trialNum, expName, appName,
                 baseline=None, groupName=None, jobNum=None):
        self.simId     = simId
        self.trialNum  = trialNum
        self.expName   = expName
        self.baseline  = baseline
        self.groupName = groupName
        self.jobNum    = jobNum
        self.appName   = appName


    def __str__(self):
        return "proj=%s exp=%s grp=%s sim=%s trial=%s job=%s" % \
               (self.appName, self.expName, self.groupName, self.simId, self.trialNum, self.jobNum)

    def setEnvironment(self):
        '''
        Update the environment vars to represent the context
        '''
        os.environ['MCS_APP']      = self.appName or ''
        os.environ['MCS_SIMID']    = str(self.simId) if self.simId is not None else ''
        os.environ['MCS_TRIALNUM'] = str(self.trialNum) if self.trialNum is not None else ''
        os.environ['MCS_EXPNAME']  = self.expName or ''
        os.environ['MCS_BASELINE'] = self.baseline or ''
        os.environ['MCS_GROUP']    = self.groupName or ''

    def setVars(self, appName=None, simId=None, trialNum=None, expName=None,
                baseline=None, groupName=None, jobNum=None):
        '''
        Set elements of a context structure, updating the environment as well.
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

        if jobNum:
            self.jobNum = jobNum

        self.setEnvironment()


def getContext():
    '''
    Get the "context" from environment variables.
    '''
    appName = os.getenv('MCS_APP') or getSection()
    setSection(appName)

    trialNum = os.getenv('MCS_TRIALNUM')
    if trialNum:
        trialNum = int(trialNum)

    simId = os.getenv('MCS_SIMID')
    if simId:
        simId = int(simId)

    expName  = os.getenv('MCS_EXPNAME')
    baseline = os.getenv('MCS_BASELINE')

    jobNum  = getJobNum()

    groupName = os.getenv('MCS_GROUP')

    return Context(simId, trialNum, expName, appName,
                   baseline=baseline, groupName=groupName, jobNum=jobNum)


def setContext(context, appName=None, simId=None, trialNum=None,
               expName=None, baseline=None, jobNum=None):
    '''
    Set elements of a context structure, updating the environment as well.
    '''
    if appName:
        context.appName = appName
        os.environ['MCS_APP'] = appName

    if simId is not None:
        context.simId = int(simId)
        os.environ['MCS_SIMID'] = str(simId)

    if trialNum is not None:
        context.trialNum = int(trialNum)
        os.environ['MCS_TRIALNUM'] = str(trialNum)

    if expName:
        context.expName = expName
        os.environ['MCS_EXPNAME'] = expName

    if baseline:
        context.baseline = baseline
        os.environ['MCS_BASELINE'] = baseline

    if jobNum:
        context.jobNum = jobNum


def getJobNum():
    batchSystem = getParam('MCS.BatchSystem')
    job_id_var  = getParam("%s.%s" % (batchSystem, 'JOB_ID_VAR'))
    jobIdStr  = os.getenv(job_id_var, '')

    result = re.search('\d+', jobIdStr)
    jobNum = int(result.group(0)) if result else os.getpid()
    return jobNum

def jobTmpDir():
    '''
    Generate the name of a temporary directory based on the value of $MCS_TMP (if set,
    or '/tmp' if not) and the job ID from the environment.
    '''
    tmpDir = getParam('GCAM.TempDir')
    dirName = "mcs.%s.tmp" % getJobNum()
    dirPath = os.path.join(tmpDir, dirName)
    return dirPath

def tail(filename, count):
    '''
    Return the last `count` lines from a text file by running the
    tail command as a subprocess. (Faster than native Python...)

    :param filename: a filename
    :param count: number of lines to read from end of file
    :return: a list of the lines read
    '''
    from subprocess import check_output
    pipe = None

    try:
        cmd = 'tail -n %d %s' % (count, filename)
        lines = check_output(cmd, shell=True)

    except Exception as e:
        msg = "Failed run 'tail' on file '%s': %s" % (filename, e)
        raise PygcamMcsSystemError(msg)
    finally:
        if pipe:
            pipe.close()

    return lines

LogLinesToSave = 100
QuarterGigabyte = 1024 * 1024 * 128

# TBD: still needed?
def truncateBigFile(filename, maxSize=QuarterGigabyte, linesToSave=LogLinesToSave, delete=True, raiseError=True):
    '''
    If the named file is greater than maxSize (default 128 MB), read the last
    `count` lines (default 100) from the file, write the saved lines in a
    file with new extension of .truncated.out, and if `delete` is non-False,
    delete the original file.
    '''
    try:
        fileSize = os.path.getsize(filename)
        if fileSize <= maxSize:
            return
    except Exception as e:
        msg = "Failed to get size of file '%s': %s" % (filename, e)
        if raiseError:
            raise PygcamMcsSystemError(msg)
        else:
            return

    text = tail(filename, linesToSave)

    base, ext = os.path.splitext(filename)
    newName = base + '.truncated' + ext

    with open(newName, "w") as f:
        f.write(text)

    if delete:
        os.unlink(filename)

def computeLogPath(simId, expName, logDir, trials):
    trialMin = min(trials)
    trialMax = max(trials)
    trialRange = trialMin if trialMin == trialMax else "%d-%d" % (trialMin, trialMax)
    jobName  = "%s-s%d-%s" % (expName, simId, trialRange)   # for displaying in job queue
    logFile  = "%s-%s.out" % (expName, trialRange)          # for writing diagnostic output
    logPath  = os.path.join(logDir, logFile)
    return logPath, logFile, jobName

def sign(number):
    return cmp(number, 0)

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def checkSuffix(path, suffix):
    return os.path.splitext(path)[1][1:] == suffix

def fileReader(filename, error=BaseSpecError, fileExtension=None, split=True):
    '''
    Generator for reading a file line by line.

    error is an exception class that subclasses BaseSpecError. lineNum is changed
    automatically as the generator reads the file to ensure that any error thrown
    has the correct line number printed.

    fileExtension is the expected extension of the file. If the
    extension doesn't match, an exception is thrown.

    split is a boolean indicating whether the line should be tokenized or not.

    Returns either a list of tokens in a line (if split is True) or a single string.
    '''
    error.filename = filename.replace('\\', '/')

    if fileExtension:
        if not checkSuffix(filename, fileExtension):
            raise error('Wrong file extension. Should be "%s"' % fileExtension)

    with open(filename, 'r') as f:
        for lineNum, line in enumerate(f):
            error.lineNum = lineNum + 1
            line = line.split(COMMENT_CHAR)[0].strip()  # allow comments
            if len(line) == 0:
                continue
            if split:
                line = line.split()
            yield line

def getOptionalArgs(func):
    '''
    Inspects a function to find the names of optional arguments.
    Used in distrogen to generate distrogens from a single function.

    func is a function object.
    Returns a tuple of strings of the optional argument names.
    '''
    args, _, _, defaults = getargspec(func)
    args = args[-len(defaults):]
    return args

def loadModuleFromPath(modulePath):
    '''
    The load a module from a '.py' or '.pyc' file from a path that ends in the
    module name, i.e., from "foo/bar/Baz.py", the module name is 'Baz'.
    '''
    import sys
    from imp import load_source, load_compiled  # lazy import to speed startup

    # Extract the module name from the module path
    base       = os.path.basename(modulePath)
    moduleName = base.split('.')[0]

    try:
        # see if it's already loaded
        module = sys.modules[moduleName]
        _logger.debug('Module %s found in sys.modules: %s' % (moduleName, module))
        return module

    except KeyError:
        pass

    _logger.info('loading module %s' % base)

    # Load the compiled code if it's a '.pyc', otherwise load the source code
    module = None
    try:
        module = load_source(moduleName, modulePath)

    except Exception as e:
        errorString = "Can't load module %s from path %s: %s" % (moduleName, modulePath, e)
        _logger.error(errorString)
        raise PygcamMcsUserError(errorString)

    return module

def loadObjectFromPath(objName, modulePath, required=True):
    '''
    Load a module and return a reference to a named object in that module.
    If 'required' and the object is not found, an error is raised, otherwise,
    None is returned if the object is not found.
    '''
    module = loadModuleFromPath(modulePath)
    obj    = getattr(module, objName, None)

    if obj or not required:
        return obj

    raise PygcamMcsUserError("Module '%s' has no object named '%s'" % (modulePath, objName))

#
# File and directory utilities for navigating the run-time structure
#
def rmlink(path):
    if os.path.lexists(path) and os.path.islink(path):
        os.remove(path)

def symlink(src, dst):
    rmlink(dst)
    _logger.debug('ln -s %s %s', src, dst)
    try:
        os.symlink(src, dst)
    except Exception:
        print("Can't symlink %s to %s" % (src, dst))
        raise

def rename(direc, src, dest):
    old = os.path.join(direc, src)
    new = os.path.join(direc, dest)
    os.rename(old, new)

def filecopy(src, dst, removeDst=True):
    'Copy src file to dst, optionally removing dst first to avoid writing through symlinks'
    from shutil import copy2        # equivalent to "cp -p"

    _logger.debug("copyfile(%s,%s,%s)" % (src, dst, removeDst))
    if removeDst and os.path.islink(dst):
        os.remove(dst)

    copy2(src, dst)

def copyfiles(files, dstdir, removeDst=True):
    '''
    :param files: a list of files to copy
    :param dstdir: the directory to copy to
    :param removeDst: if True-like, remove destination file before copying
    :return: nothing
    '''
    mkdirs(dstdir)
    for f in files:
        filecopy(f, dstdir, removeDst=removeDst)

def dirFromNumber(n, prefix="", create=False):
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


def getLogDir(simId, create=False):
    '''
    :param simId: simulation id
    :param create: if True, create the directory if needed
    :return: the pathname of the log directory
    '''
    simDir = getSimDir(simId, create=create)
    logDir = os.path.join(simDir, 'log')
    if create:
        mkdirs(logDir)

    return logDir

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

def getTrialDir(simId, trialNum, create=False):
    '''
    Return and optionally create the path to the directory for a specific
    simulation id and trial id.
    '''
    simDir = getSimDir(simId, create=False)
    trialDir = dirFromNumber(trialNum, prefix=simDir, create=create)
    return trialDir

def getExpDir(simId, trialNum, expName, create=False):
    trialDir = getTrialDir(simId, trialNum, create=create)
    expDir = os.path.join(trialDir, expName)
    if create:
        mkdirs(expDir)

    return expDir

def getExpDirFromContext(context=None, create=False):
    '''
    Return and optionally create the path to the directory for a specific experiment.
    '''
    if context is None:
        context = getContext()

    return getExpDir(context.simId, context.trialNum, context.expName, create=create)

def getCurExpDir():
    '''
    Gets the current experiment directory based on current context.
    '''
    return getExpDirFromContext(getContext())

def getCurTrialDir():
    '''
    Gets the current trial dir based on current context.
    '''
    context = getContext()
    return getTrialDir(context.simId, context.trialNum)


def randomSleep(minSleep, maxSleep):
    '''
    Sleep for a random number of seconds between minSleep and maxSleep.
    '''
    import random
    import time

    delay = minSleep + random.random() * (maxSleep - minSleep)
    _logger.debug('randomSleep: sleeping %.1f seconds', delay)
    time.sleep(delay)

# Support for saving and loading runtime arguments passed from the "queue"
# command to the program running on the compute node.
_RUNTIME_ARGS_FILENAME = 'args.json'

def saveRuntimeArgs(args, context=None):
    import json     # lazy import

    expDir = getExpDirFromContext(context=context, create=True)
    args['expName'] = context.expName
    pathname = os.path.join(expDir, _RUNTIME_ARGS_FILENAME)
    with open(pathname, 'w') as fp:
        json.dump(args, fp, indent=4)
        fp.write("\n")

def loadRuntimeArgs(dirname=None, context=None, asNamespace=False):
    '''
    Load arguments from args.json file, but retry to allow for transient
    timeout errors resulting from many jobs starting at once.
    '''
    import json     # lazy import

    if not dirname:
        dirname = getExpDirFromContext(context=context)

    pathname = os.path.join(dirname, _RUNTIME_ARGS_FILENAME)

    minSleep = 1
    maxSleep = 1 # 3
    maxTries = 1 # 3

    args = None
    for i in range(maxTries):
        try:
            with open(pathname, 'r') as fp:
                args = json.load(fp)
            break

        except IOError as e:
            _logger.error("loadRuntimeArgs: %s", e)
            randomSleep(minSleep, maxSleep)

    if i == maxTries:
        raise PygcamMcsSystemError("Failed to read '%s' after %d tries" % (pathname, maxTries))

    if args and asNamespace:
        from argparse import Namespace
        return Namespace(**args)

    return args


def findParamData(paramList, name):
    '''
    Convenience method mostly used in testing.
    Finds a param from a given list of Parameter instances with given name.
    '''
    return filter(lambda x: x.name == name, paramList)[0].data

TRIAL_STRING_DELIMITER = ','

def parseTrialString(string):
    '''
    Converts a comma-separated list of ranges into a list of numbers.
    Ex. 1,3,4-6,2 becomes [1,3,4,5,6,2]. Duplicates are deleted.
    '''
    rangeStrs = string.split(TRIAL_STRING_DELIMITER)
    res = set()
    for rangeStr in rangeStrs:
        r = [int(x) for x in rangeStr.strip().split('-')]
        if len(r) == 2:
            r = range(r[0], r[1] + 1)
        elif len(r) != 1:
            raise ValueError('Malformed trial string.')
        res = res.union(set(r))
    return list(res)

def createTrialString(lst):
    '''
    Assemble a list of numbers into a compact list using hyphens to identify ranges.
    This reverses the operation of parseTrialString
    '''
    from itertools import groupby   # lazy import
    from operator  import itemgetter

    lst = sorted(set(lst))
    ranges = []
    for _, g in groupby(enumerate(lst), lambda (i, x): i - x):
        group = map(lambda x: str(itemgetter(1)(x)), g)
        if group[0] == group[-1]:
            ranges.append(group[0])
        else:
            ranges.append(group[0] + '-' + group[-1])
    return TRIAL_STRING_DELIMITER.join(ranges)

def chunkify(lst, chunks):
    '''
    Generator to turn a list into the number of lists given by chunks.
    In the case that len(lst) % chunksize != 0, all chunks are made as
    close to the same size as possible.
    '''
    l = len(lst)
    numWithExtraEntry = l % chunks  # this many chunks have one extra entry
    chunkSize = (l - numWithExtraEntry) / chunks + 1
    switch = numWithExtraEntry * chunkSize

    i = 0
    while i < l:
        if i == switch:
            chunkSize -= 1
        yield lst[i:i + chunkSize]
        i += chunkSize

def saveDict(d, filename):
    with open(filename, 'w') as f:
        for key, value in d.iteritems():
            f.write('%s=%s\n' % (key, value))

def fullClassname(obj):
    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__
    return module + '.' + obj.__class__.__name__

def isdebugging():
  for frame in stack():
    if frame[1].endswith("pydevd.py"):
      return True
  return False

# Basenames of common files and dirs
ConfigFileName    = "config.xml"
ScenarioFileName  = "scenarios.xml"
ParameterFileName = "parameters.xml"
ResultFileName    = "results.xml"
QueryDirName      = "queries"

SimAppXmlDirName   = "app-xml"
SimLocalXmlDirName = "local-xml"

def getSimXmlDir(simId):
    """
    Returns the top-level simulation-specific App xml dir, e.g., {simDir}/app-xml
    """
    simDir = getSimDir(simId)
    path = os.path.join(simDir, SimAppXmlDirName)
    return path

def getSimXmlFile(simId, filename):
    """
    Returns the path to a file in the sim's XML dir, e.g., {simDir}/app-xml/foo.xml
    """
    xmlDir = getSimXmlDir(simId)
    path = os.path.join(xmlDir, filename)
    return path

def getSimParameterFile(simId):
    """
    Returns the path to sim's copy of the parameters.xml file.
    """
    return getSimXmlFile(simId, ParameterFileName)

def getSimScenarioFile(simId):
    """
    Returns the path to sim's copy of the scenarios.xml file.
    """
    return getSimXmlFile(simId, ScenarioFileName)

def getSimResultFile(simId):
    """
    Returns the path to sim's copy of the results.xml file.
    """
    return getSimXmlFile(simId, ResultFileName)

def getSimLocalXmlDir(simId):
    """
    Returns the path to sim's local-xml dir.
    """
    simDir = getSimDir(simId)
    path = os.path.join(simDir, SimLocalXmlDirName)
    return path

def getSimScenarioDir(simId, scenarioName):
    subdir = getParam('MCS.ScenarioSubdir')

    localXmlDir = getSimLocalXmlDir(simId)
    scenDir = os.path.join(localXmlDir, subdir, scenarioName)
    return scenDir

def getSimConfigFile(simId, scenarioName):
    """
    Returns the path to sim's copy of the config.xml file for the given scenario.
    """
    scenDir = getSimScenarioDir(simId, scenarioName)
    configFile = os.path.join(scenDir, ConfigFileName)
    return configFile

def getRunQueryDir():
    """
    Returns the path to sim's copy of the scenarios.xml file.
    """
    workspace = getParam('MCS.RunWorkspace')

    path = os.path.join(workspace, QueryDirName)
    return path

# if __name__ == "__main__":
#     filename = '/Users/rjp/tmp/final-energy-by-fuel-Reference.csv'
#
#     truncateBigFile(filename, 100000, linesToSave=10, delete=False)
#     truncateBigFile(filename, 10000,  linesToSave=50, delete=True)
