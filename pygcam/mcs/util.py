# @author: Richard Plevin
# @author: Sam Fendell
#
# Copyright (c) 2012-2015. The Regents of the University of California (Regents)
# and Richard Plevin. See the file COPYRIGHT.txt for details.

# TBD: eliminate redundancies with pygcam

from __future__ import with_statement, print_function

import os
from inspect import stack, getargspec

from pygcam.config import getParam, getParamAsInt
from pygcam.log import getLogger
from pygcam.utils import mkdirs, createTrialString, chunkify

from .constants import COMMENT_CHAR
from .context import getSimDir
from .error import BaseSpecError, PygcamMcsUserError, PygcamMcsSystemError

_logger = getLogger(__name__)

_activeYearStrs = None
_activeYearInts = None

YEAR_COL_PREFIX = 'y'

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

def createOutputDir(outputDir):
    from ..utils import removeFileOrTree
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
        from functools import reduce

        def reducer(lst, item):
            m = re.match(r"^(\d{4})-(\d{4})(?::(\d+))?$", item)
            if m:
                start = int(m.group(1))
                end = int(m.group(2))
                step = int(m.group(3)) if m.lastindex == 3 else 5    # default 5 yr timestep
                rng = list(range(start, end + 1, step))
                lst.extend(rng)
            elif item.isdigit():
                lst.append(int(item))
            else:
                raise PygcamMcsUserError('Element in list of active years is not an integer: %s' % item)

            return lst

        yearStr = getParam('MCS.Years')
        items = yearStr.split(',')
        years = reduce(reducer, items, [])

        _activeYearInts = [int(y) for y in years]
        _activeYearStrs = [str(y) for y in years]

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
        lines = check_output(cmd, shell=True).decode('utf-8')

    except Exception as e:
        msg = "Failed run 'tail' on file '%s': %s" % (filename, e)
        raise PygcamMcsSystemError(msg)
    finally:
        if pipe:
            pipe.close()

    return lines

def computeLogPath(simId, scenario, logDir, trials):
    trialMin = min(trials)
    trialMax = max(trials)
    trialRange = trialMin if trialMin == trialMax else "%d-%d" % (trialMin, trialMax)
    jobName  = "%s-s%d-%s" % (scenario, simId, trialRange)   # for displaying in job queue
    logFile  = "%s-%s.out" % (scenario, trialRange)          # for writing diagnostic output
    logPath  = os.path.join(logDir, logFile)
    return logPath, logFile, jobName

def sign(number):
    return (number > 0) - (number < 0)      # cmp() removed in py3

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
    try:
        module = load_source(moduleName, modulePath)
        return module

    except Exception as e:
        errorString = "Can't load module %s from path %s: %s" % (moduleName, modulePath, e)
        _logger.error(errorString)
        raise PygcamMcsUserError(errorString)


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

    level1 = n // maxnodes
    level2 = n % maxnodes

    directory = os.path.join(prefix, str(level1).zfill(log), str(level2).zfill(log))
    if create:
        mkdirs(directory)

    return directory

def findParamData(paramList, name):
    '''
    Convenience method mostly used in testing.
    Finds a param from a given list of Parameter instances with given name.
    '''
    items = [x for x in paramList if x.name == name]
    return items[0].data

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
            r = list(range(r[0], r[1] + 1))
        elif len(r) != 1:
            raise ValueError('Malformed trial string.')
        res = res.union(set(r))
    return list(res)


def saveDict(d, filename):
    with open(filename, 'w') as f:
        for key, value in d.items():
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

def getSimXmlFile(simId, filename):
    """
    Returns the path to a file in the sim's XML dir, e.g., {simDir}/app-xml/foo.xml
    """
    simDir = getSimDir(simId)
    xmlDir = os.path.join(simDir, SimAppXmlDirName)
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

def getRunQueryDir():
    """
    Returns the path to sim's copy of the scenarios.xml file.
    """
    workspace = getParam('MCS.RunWorkspace')

    path = os.path.join(workspace, QueryDirName)
    return path
