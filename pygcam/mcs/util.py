# Author: Richard Plevin
#
# Copyright (c) 2012-2023. The Regents of the University of California (Regents)
# and Richard Plevin. See the file COPYRIGHT.txt for details.

# TBD: eliminate redundancies with pygcam.utils

import os
from inspect import stack

from ..config import getParam, getParamAsInt, pathjoin, mkdirs
from ..constants import LOCAL_XML_NAME, APP_XML_NAME
from ..log import getLogger

from .error import BaseSpecError, PygcamMcsUserError, PygcamMcsSystemError

_logger = getLogger(__name__)

_activeYearStrs = None
_activeYearInts = None

PARAMETERS_XML = "parameters.xml"
RESULTS_XML    = "results.xml"
TRIAL_DATA_CSV = 'trialData.csv'

COMMENT_CHAR = '#'
YEAR_COL_PREFIX = 'y'

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

    directory = pathjoin(prefix, str(level1).zfill(log), str(level2).zfill(log), create=create)

    return directory

# TBD: rationalize this with McsSandbox.
#  Change to pass in Context? Or create McsSandbox from McsContext?
def getSimDir(simId, create=False):
    '''
    Return and optionally create the path to the top-level simulation
    directory for the given simulation number, based on the SimsDir
    parameter specified in the config file.
    '''
    simsDir = getParam('MCS.SandboxSimsDir')
    if not simsDir:
        raise PygcamMcsUserError("Missing required config parameter 'MCS.SandboxSimsDir'")

    # name is of format ".../s001/"
    simDir = pathjoin(simsDir, f's{simId:03d}', create=create)

    return simDir

def trialDataFile(simId):
    simDir = getSimDir(simId)
    return pathjoin(simDir, TRIAL_DATA_CSV)

def writeTrialDataFile(simId, df):
    '''
    Save the trial DataFrame in the file 'trialData.csv' in the simDir.
    '''
    dataFile = trialDataFile(simId)

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

    dataFile = trialDataFile(simId)
    df = pd.read_table(dataFile, sep=',', index_col='trialNum')
    return df

# TBD: test this
def newActiveYears(asInt=False):
    global _activeYearInts
    global _activeYearStrs

    # return cached values or compute and cache result
    if not _activeYearStrs:
        from ..project import Project, SimpleVariable

        proj_name = getParam('GCAM.ProjectName')
        Project.readProjectFile(proj_name)
        d = SimpleVariable.getDict()
        years = d['years']

        _activeYearInts = [int(y) for y in years]
        _activeYearStrs = [str(y) for y in years]

    return _activeYearInts if asInt else _activeYearStrs

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

    cmd = f"tail -n {count} '{filename}'"
    try:
        lines = check_output(cmd, shell=True).decode('utf-8')
        return lines

    except Exception as e:
        raise PygcamMcsSystemError(f'Shell command failed: "{cmd}" : {e}')


def computeLogPath(simId, scenario, logDir, trials):
    trialMin = min(trials)
    trialMax = max(trials)
    trialRange = trialMin if trialMin == trialMax else f"{trialMin}-{trialMax}"
    jobName  = f"{scenario}-s{simId}-{trialRange}"   # for displaying in job queue
    logFile  = f"{scenario}-{trialRange}.out"        # for writing diagnostic output
    logPath  = pathjoin(logDir, logFile)
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
            raise error(f'Wrong file extension. Should be "{fileExtension}"')

    with open(filename, 'r') as f:
        for lineNum, line in enumerate(f):
            error.lineNum = lineNum + 1
            line = line.split(COMMENT_CHAR)[0].strip()  # allow comments
            if len(line) == 0:
                continue
            if split:
                line = line.split()
            yield line

# TBD: Another version exists in pygcam.utils. Compare and reconcile these.
def loadModuleFromPath(modulePath):
    '''
    The load a module from a '.py' or '.pyc' file from a path that ends in the
    module name, i.e., from "foo/bar/Baz.py", the module name is 'Baz'.
    '''
    import sys
    from imp import load_source  # lazy import to speed startup

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

# TBD: Should be moved to pygcam.utils as well as a partner to the fn above.
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

    directory = pathjoin(prefix, str(level1).zfill(log), str(level2).zfill(log), create=create)
    return directory

TRIAL_STRING_DELIMITER = ','

def parseTrialString(string):
    '''
    Converts a comma-separated list of ranges into a list of numbers.
    Ex. 1,3,4-6,2 becomes [1,3,4,5,6,2]. Duplicates are deleted.
    See also createTrialString() below.
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

def createTrialString(lst):
    '''
    Assemble a list of numbers into a compact list using hyphens to identify
    ranges. This reverses the operation of parseTrialString()
    '''
    from itertools import groupby
    from operator  import itemgetter

    lst = sorted(set(lst))
    ranges = []

    def _group(i, x):
        return i - x

    for _, g in groupby(enumerate(lst), lambda tup: _group(*tup)):
        # group = map(lambda x: str(itemgetter(1)(x)), g)
        group = [str(itemgetter(1)(x)) for x in g]
        if group[0] == group[-1]:
            ranges.append(group[0])
        else:
            ranges.append(group[0] + '-' + group[-1])
    return TRIAL_STRING_DELIMITER.join(ranges)

def saveDict(d, filename):
    with open(filename, 'w') as f:
        for key, value in d.items():
            f.write('%s=%s\n' % (key, value))

def isdebugging():
  for frame in stack():
    if frame[1].endswith("pydevd.py"):
      return True
  return False

# TBD: the following should be subsumed by McsSandbox

def getSimXmlFile(simId, filename):
    """
    Returns the path to a file in the sim's XML dir, e.g., {simDir}/app-xml/foo.xml
    """
    simDir = getSimDir(simId)
    path = pathjoin(simDir, APP_XML_NAME, filename)
    return path

def getSimParameterFile(simId):
    """
    Returns the path to sim's copy of the parameters.xml file.
    """
    return getSimXmlFile(simId, PARAMETERS_XML)

# TBD: unused
# def getSimScenarioFile(simId):
#     """
#     Returns the path to sim's copy of the scenarios.xml file.
#     """
#     return getSimXmlFile(simId, SCENARIOS_XML)

def getSimResultFile(simId):
    """
    Returns the path to sim's copy of the results.xml file.
    """
    return getSimXmlFile(simId, RESULTS_XML)

def getSimLocalXmlDir(simId):
    """
    Returns the path to sim's local-xml dir.
    """
    simDir = getSimDir(simId)
    path = pathjoin(simDir, LOCAL_XML_NAME)
    return path

def parseMcsDir(path, trialNum_only=False):
    """
    Parse a path to a trial and scenario's "exe" directory to extract
    the trial number and scenario name. If the pathname doesn't end in
    "exe", assume it's the parent (scenario) directory.

    :param path: (str) pathname of an "exe" directory for a trial and scenario
    :return: (tuple) (simId, trialNum, scenario) unless ``trialNum_only`` is True,
        in which case only the trial number is returned.
    """
    from pathlib import Path
    parts = Path(path).absolute().parts

    if parts[-1] == 'exe':
        # e.g., "/whatever/mcs/series_61/sims/s001/001/023/base/exe"
        sim, trial1, trial2, scenario = parts[-5:-1]
    else:
        # e.g., "/whatever/mcs/series_61/sims/s001/001/023/base"
        sim, trial1, trial2 = parts[-4:-1]

    trialNum = int(trial1 + trial2)
    if trialNum_only:
        return trialNum

    simId = int(sim[1:])
    return (simId, trialNum, scenario)

def hardlink_directory_contents(src_dir, dst_dir):
    """
    Recursively hard link all files in the source directory ``src_dir`` in the
    destination directory ``dst_dir``. Subdirectories are created in the same
    relative location in ``dst_dir``, and all files are linked.

    :param src_dir: (str or pathlib.Path) the directory to create links to
    :param dst_dir: (str or pathlib.Path) the directory in which to create links
    :return: none
    """
    mkdirs(dst_dir)

    src_dir_len = len(src_dir)

    for item in os.scandir(src_dir):
        rel_path = item.path[src_dir_len:]
        dst_abs_path = dst_dir + rel_path

        if item.is_dir():
            hardlink_directory_contents(item.path, dst_abs_path)
        else:
            os.link(item.path, dst_abs_path, follow_symlinks=True)
