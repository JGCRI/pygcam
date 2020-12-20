'''
.. Created on: 2/12/15
   Common functions and data

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import argparse
import io
import os
from lxml import etree as ET
import pkgutil
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager

from .config import getParam, getParamAsBoolean, pathjoin, unixPath, parse_version_info
from .error import PygcamException, FileFormatError
from .log import getLogger

_logger = getLogger(__name__)

#
# Custom argparse "action" to parse comma-delimited strings to lists
# TBD: Use this where relevant
#
class ParseCommaList(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed with " % option_strings)

        super(ParseCommaList, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.split(','))

def splitAndStrip(s, delim):
    items = [item.strip() for item in s.split(delim)]
    return items

def validate_years(years):
    pair = years.split('-')
    if len(pair) != 2:
        return None

    (first, last) = pair
    if not (first.isdigit() and last.isdigit()):
        return None

    first = int(first)
    last  = int(last)

    if not (first < last):
        return None

    return [i for i in range(first, last+1, 5)]

def is_abspath(pathname):
    """
    Return True if pathname is an absolute pathname, else False.
    """
    return bool(re.match(r"^([/\\])|([a-zA-Z]:)", pathname))

def get_path(pathname, defaultDir):
    """
    Return pathname if it's an absolute pathname, otherwise return
    the path composed of pathname relative to the given defaultDir.
    """
    return pathname if is_abspath(pathname) else pathjoin(defaultDir, pathname)

# For gcam 5, read the map of river basins to countries (and other info)
def readBasinMap():
    from .query import readCsv

    stream = resourceStream('etc/gcam-v5/basin_to_country_mapping.csv')
    df = readCsv(stream, skiprows=2)
    return df

# For gcam 5, produce a map of basins for each (ISO) country name
def basinsByISO():
    df = readBasinMap()
    ISOs = df['ISO'].unique()
    result = {}
    for iso in ISOs:
        rows = df.query("ISO == '{}'".format(iso))
        result[iso] = list(rows['GLU_name'])

    return result

# Cache results of determining regions
_RegionList = None
_StateList  = None
_RegWorkspace = None

# Options for the states keyword to getRegionsList
StateOptions = ('withGlobal',   # return states and global regions
                'withUSA',      # return states and USA region only
                'only',         # return states only, excluding global regions
                'none')         # return only global regions

def getRegionList(workspace=None, states='withGlobal'):
    """
    Set the list of the defined region names from the data system, if possible,
    otherwise use the built-in list of 32 regions.

    :param workspace: (str) the path to a ``Main_User_Workspace`` directory that
      has the file
      ``input/gcamdata/inst/extdata/common/GCAM_region_names.csv``,
      or ``None``, in which case the value of config variable
      ``GCAM.SourceWorkspace`` (if defined) is used. If `workspace` is
      empty or ``None``, and the config variable ``GCAM.SourceWorkspace`` is
      empty (the default value), the built-in default 32-region list is returned.
    :param states: (str) One of {'together', 'only', 'none'}. Default is 'together'.
    :return: a list of strings with the names of the defined regions
    """
    from .constants import GCAM_32_REGIONS
    from .csvCache import readCachedCsv
    from semver import VersionInfo

    global _RegionList, _StateList

    if states not in StateOptions:
        raise PygcamException('Called getRegionList with unrecognized value ({}) for "state" argument. Must be one of {}.'.format(states, StateOptions))

    # Decache if called with different workspace
    if _RegWorkspace and workspace != _RegWorkspace:
        _RegionList = _StateList = None

    if _RegionList and states == 'none':
        return _RegionList

    if _StateList and states == 'only':
        return _StateList

    if _RegionList and _StateList and states == 'withGlobal':
        return _RegionList + _StateList

    if _StateList and states == 'withUSA':
        return _StateList + ['USA']

    version = parse_version_info()

    # Deprecated (probably). Need to test that the subsequent code handles all require cases
    if version > VersionInfo(5, 0, 0):
        # input/gcamdata/inst/extdata/common/GCAM_region_names.csv
        relpath = pathjoin('input', 'gcamdata', 'inst', 'extdata', 'common', 'GCAM_region_names.csv')
        skiprows = 6
    else:
        relpath = pathjoin('input', 'gcam-data-system', '_common', 'mappings', 'GCAM_region_names.csv')
        skiprows = 3

    workspace = workspace or getParam('GCAM.RefWorkspace')

    if getParamAsBoolean('GCAM.RegionDiscovery'):   # True by default, but can be disabled by setting to False
        configFile = getParam('GCAM.RefConfigFile')
        if not os.path.lexists(configFile):
            _logger.error("GCAM reference config file '{}' not found.".format(configFile))
            return

        parser = ET.XMLParser(remove_blank_text=True)
        tree   = ET.parse(configFile, parser)

        def _xmlpath(tag):
            elt = tree.find('//ScenarioComponents/Value[@name="{}"]'.format(tag))
            return None if elt is None else pathjoin(workspace, 'exe', elt.text, abspath=True)

        xml_USA    = _xmlpath('socio_usa')
        xml_global = _xmlpath('socioeconomics')

        if xml_global and os.path.lexists(xml_global):
            tree = ET.parse(xml_global, parser)
            _RegionList = tree.xpath('//region/@name')
        else:
            _logger.error("GCAM input file '{}' not found.".format(xml_global))
            return

        if xml_USA:
            if not os.path.lexists(xml_USA):
                _logger.error("GCAM input file '{}' not found.".format(xml_USA))
                return

            tree = ET.parse(xml_USA, parser)
            _StateList = tree.xpath('//region/@name')
            _StateList = sorted(set(_StateList) - {'USA'})  # don't include "USA" in list of states

    else: # Deprecated (probably) -- see note above.
        path = pathjoin(workspace, relpath) if workspace else None

        if path and os.path.lexists(path):
            _logger.debug("Reading region names from %s", path)
            df = readCachedCsv(path, skiprows=skiprows)
            _RegionList = list(df.region)

        else:
            _logger.info("Path %s not found; Using built-in region names", path)
            _RegionList = GCAM_32_REGIONS

    _StateList = _StateList or []

    if states == 'withGlobal':
        regions = _RegionList + _StateList
    elif states == 'only':
        regions = _StateList
    elif states == 'withUSA':
        regions = _StateList + ['USA']
    elif states == 'none':
        regions = _RegionList

    _logger.debug("getRegionList returning: %s", regions)
    return regions

def queueForStream(stream):
    """
    Create a thread to read from a non-socket file descriptor and
    its contents to a socket so non-blocking read via select() works
    on Windows. (Since Windows doesn't support select on pipes.)

    :param stream: (file object) the input to read from,
       presumably a pipe from a subprocess
    :return: (int) a file descriptor for the socket to read from.
    """
    from six.moves.queue import Queue
    from threading import Thread

    def enqueue(stream, queue):
        fd = stream.fileno()
        data = None
        while data != b'':
            data = os.read(fd, 1024)
            queue.put(data)
        stream.close()

    q = Queue()
    t = Thread(target=enqueue, args=(stream, q))
    t.daemon = True # thread dies with the program
    t.start()

    return q

# Used only in CI plugins
def digitColumns(df, asInt=False):
    '''
    Get a list of columns with integer names (as strings, e.g., "2007") in df.
    If asInt is True return as a list of integers, otherwise as strings.
    '''
    digitCols = filter(str.isdigit, df.columns)
    return [int(x) for x in digitCols] if asInt else list(digitCols)

# Function to return current function name, or the caller, and so on up
# the stack, based on value of n.
getFuncName = lambda n=0: sys._getframe(n + 1).f_code.co_name

pat = re.compile('(\{[^\}]+\})')

# used only in project.py
def simpleFormat(s, varDict):
    """
    Simple version of str.format that does not treat '.' as
    an attribute reference.

    :param s: (str) string with args in curly braces
    :param varDict: (dict) dictionary of var names and values
    :return: (str) formatted string
    """
    def lookup(m):
        match = m.group(0)
        key = match[1:-1]   # strip off curly braces
        return str(varDict[key])

    try:
        result = re.sub(pat, lookup, s)
        return result
    except KeyError as e:
        raise FileFormatError('Unknown parameter %s in project XML template string' % e)

@contextmanager
def pushd(directory):
    """
    Context manager that changes to the given directory and then
    returns to the original directory. Usage is ``with pushd('/foo/bar'): ...``

    :param directory: (str) a directory to chdir to temporarily
    :return: none
    """
    owd = os.getcwd()
    try:
        os.chdir(directory)
        yield directory
    finally:
        os.chdir(owd)

def getResource(relpath):
    """
    Extract a resource (e.g., file) from the given relative path in
    the pygcam package.

    :param relpath: (str) a path relative to the pygcam package
    :return: the file contents
    """
    contents = pkgutil.get_data('pygcam', relpath)
    return contents.decode('utf-8')

def resourceStream(relpath):
    """
    Return a stream on the resource found on the given path relative
    to the pygcam package.

    :param relpath: (str) a path relative to the pygcam package
    :return: (file-like stream) a file-like buffer opened on the desired resource.
    """
    text = getResource(relpath)
    return io.BytesIO(text)

def copyResource(relpath, dest, overwrite=True):
    """
    Copy a resource from the 'pygcam' package to the given destination.

    :param relpath: (str) a path relative to the pygcam package
    :param dest: (str) the pathname of the file to create by copying the resource.
    :param overwrite: (bool) if False, raise an error if the destination
      file already exists.
    :return: none
    """
    if not overwrite and os.path.lexists(dest):
        raise FileFormatError(dest)

    text = getResource(relpath)
    with open(dest, 'w') as f:
        f.write(text)

# used only in gcamtool modules
def getBooleanXML(value):
    """
    Get a value from an XML file and convert it into a boolean True or False.

    :param value: any value (it's first converted to a string)
    :return: True if the value is in ['true', 'yes', '1'], False if the value
             is in ['false', 'no', '0']. An exception is raised if any other
             value is passed.
    :raises: PygcamException
    """
    false = ["false", "no", "0"]
    true  = ["true", "yes", "1"]

    val = str(value).strip()
    if val not in true + false:
        raise PygcamException("Can't convert '%s' to boolean; must be in {false,no,0,true,yes,1} (case sensitive)." % value)

    return (val in true)

_XMLDBPropertiesTemplate = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<!-- WARNING: this file is automatically generated. Manual edits will be overwritten. -->
<properties>
	<entry key="in-memory">{inMemory}</entry>
	<entry key="filter-script">{filterFile}</entry>
	<entry key="batch-logfile">{batchLog}</entry>
	<entry key="batch-queries">{batchFile}</entry>
</properties>
"""

def writeXmldbDriverProperties(outputDir='.', inMemory=True, filterFile='', batchFile='', batchLog=''):
    """
    Write a XMLDBDriver.properties file using the values passed in the arguments.

    :param outputDir: (str) where to write the file
    :param inMemory: (bool) if True, the ``in-memory`` attribute is set to True
    :param filterFile: (str) a file that filters GCAM query output to limit what's
       written to the database
    :param batchFile: (str) the path to an XML batch query file
    :param batchLog: (str) the path to a log file into which to direct
       batch query messages (queries can be pretty verbose...)
    :return: none
    """
    path = pathjoin(outputDir, 'XMLDBDriver.properties')
    memFlag = 'true' if inMemory else 'false'
    content = _XMLDBPropertiesTemplate.format(inMemory=memFlag, filterFile=filterFile,
                                              batchFile=batchFile, batchLog=batchLog)

    deleteFile(path) # avoid writing through symlinks to ref workspace
    with open(path, 'w') as f:
        f.write(content)

def deleteFile(filename):
    """
    Delete the given `filename`, but ignore errors, like "rm -f"

    :param filename: (str) the file to remove
    :return: none
    """
    try:
        os.remove(filename)
    except:
        pass    # ignore errors, like "rm -f"

# used only in gcamtool modules
def symlinkOrCopyFile(src, dst):
    """
    Symlink a file unless GCAM.CopyAllFiles is True, in which case, copy the file.

    :param src: (str) filename of original file
    :param dst: (dst) filename of copy
    :return: none
    """
    if getParamAsBoolean('GCAM.CopyAllFiles'):
        copyFileOrTree(src, dst)
    else:
        os.symlink(src, dst)

def copyFileOrTree(src, dst):
    """
    Copy src to dst, where the two can both be files or directories.
    If `src` and `dst` are directories, `dst` must not exist yet.

    :param src: (str) path to a source file or directory
    :param dst: (str) path to a destination file or directory.
    :return: none
    """
    if getParamAsBoolean('GCAM.CopyAllFiles') and src[0] == '.':   # convert relative paths
        src = pathjoin(os.path.dirname(dst), src, normpath=True)

    if os.path.islink(src):
        src = os.readlink(src)

    if os.path.isdir(src):
        removeTreeSafely(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)

# used only in gcamtool modules
# TBD: rename to removeTree
def removeTreeSafely(path, ignore_errors=True):
    if not os.path.lexists(path):
        return

    refWorkspace = os.path.realpath(getParam('GCAM.RefWorkspace'))
    thisPath = os.path.realpath(path)
    if os.path.commonprefix((refWorkspace, thisPath)) == refWorkspace:
        raise PygcamException("Refusing to delete %s, which is part of the reference workspace" % path)

    _logger.debug("shutil.rmtree('%s')", thisPath)
    shutil.rmtree(thisPath, ignore_errors=ignore_errors)

def removeFileOrTree(path, raiseError=True):
    """
    Remove a file or an entire directory tree. Handles removal of symlinks
    on Windows, as these are treated differently in that system.

    :param path: (str) the pathname of a file or directory.
    :param raiseError: (bool) if True, re-raise any error that occurs
       during the file operations, else errors are ignored.
    :return: none
    """
    from .windows import removeSymlink

    if not os.path.lexists(path):
        return

    try:
        if os.path.islink(path):
            # Windows treats links to files and dirs differently.
            # NB: if not on Windows, just calls os.remove()
            removeSymlink(path)
        else:
            if os.path.isdir(path):
                removeTreeSafely(path)
            else:
                os.remove(path)
    except Exception as e:
        if raiseError:
            raise

def systemOpenFile(path):
    """
    Ask the operating system to open a file at the given pathname.

    :param path: (str) the pathname of a file to open
    :return: none
    """
    import platform
    from subprocess import call

    if platform.system() == 'Windows':
        call(['start', os.path.abspath(path)], shell=True)
    else:
        # "-g" => don't bring app to the foreground
        call(['open', '-g', path], shell=False)

def coercible(value, type, raiseError=True):
    """
    Attempt to coerce a value to `type` and raise an error on failure.

    :param value: any value coercible to `type`
    :param type: any Python type
    :return: (`type`) the coerced value, if it's coercible, otherwise
       None if raiseError is False
    :raises PygcamException: if not coercible and raiseError is True
    """
    try:
        value = type(value)
    except (TypeError, ValueError) as e:
        if raiseError:
            raise PygcamException("%s: %r is not coercible to %s" % (getFuncName(1), value, type.__name__))
        else:
            return None

    return value



def shellCommand(command, shell=True, raiseError=True):
    """
    Run a shell command and optionally raise PygcamException error.

    :param command: the command to run, with arguments. This can be expressed
      either as a string or as a list of strings.
    :param shell: if True, run `command` in a shell, otherwise run it directly.
    :param raiseError: if True, raise `ToolError` on command failure.
    :return: exit status of executed command
    :raises: ToolError
    """
    _logger.info(command)
    exitStatus = subprocess.call(command, shell=shell)
    if exitStatus != 0:
        if raiseError:
            raise PygcamException("\n*** Command failed: %s\n*** Command exited with status %s\n" % (command, exitStatus))

    return exitStatus

def flatten(listOfLists):
    """
    Flatten one level of nesting given a list of lists. That is, convert
    [[1, 2, 3], [4, 5, 6]] to [1, 2, 3, 4, 5, 6].

    :param listOfLists: a list of lists, obviously
    :return: the flattened list
    """
    from itertools import chain

    return list(chain.from_iterable(listOfLists))

def ensureExtension(filename, ext):
    """
    Force a filename to have the given extension, `ext`, adding it to
    any other extension, if present. That is, if `filename` is ``foo.bar``,
    and `ext` is ``baz``, the result will be ``foo.bar.baz``.
    If `ext` doesn't start with a ".", one is added.

    :param filename: filename
    :param ext: the desired filename extension
    :return: filename with extension `ext`
    """
    mainPart, extension = os.path.splitext(filename)
    ext = ext if ext[0] == '.' else '.' + ext

    if not extension:
        filename = mainPart + ext
    elif extension != ext:
        filename += ext

    return filename

def ensureCSV(file):
    """
    Ensure that the file has a '.csv' extension by replacing or adding
    the extension, as required.

    :param file: (str) a filename
    :return: (str) the filename with a '.csv' extension.
    """
    return ensureExtension(file, '.csv')

def getYearCols(years, timestep=5):
    """
    Generate a list of names of year columns in GCAM result files from a
    string indicating a year range.

    :param years: (str) a string of the form "2020-2050"
    :param timestep: (int) the number of years between timesteps
    :return: (list of strings) the names of the corresponding columns
    """
    try:
        yearRange = [int(x) for x in years.split('-')]
        if not len(yearRange) == 2:
            raise Exception
    except:
        raise Exception('Years must be specified as two years separated by a hyphen, as in "2020-2050"')

    cols = [str(y) for y in range(yearRange[0], yearRange[1]+1, timestep)]
    return cols

def saveToFile(txt, dirname='', filename=''):
    """
    Save the given text to a file in the given directory.

    :param txt: (str) the text to save
    :param dirname: (str) path to a directory
    :param filename: (str) the name of the file to create

    :return: none
    """
    if dirname:
        mkdirs(dirname)

    pathname = pathjoin(dirname, filename)

    _logger.debug("Writing %s", pathname)
    with open(pathname, 'w') as f:
        f.write(txt)

QueryResultsDir = 'queryResults'

def getBatchDir(scenario, resultsDir):
    """
    Get the name of the directory holding batch query results..

    :param scenario: (str) the name of a scenario
    :param resultsDir: (str) the directory in which the batch
        results directory should be created
    :return: (str) the pathname to the batch results directory
    """
    pathname = pathjoin(resultsDir, scenario, QueryResultsDir)
    return pathname


def mkdirs(newdir, mode=0o770):
    """
    Try to create the full path `newdir` and ignore the error if it already exists.

    :param newdir: the directory to create (along with any needed parent directories)
    :return: nothing
    """
    from errno import EEXIST

    try:
        os.makedirs(newdir, mode)
    except OSError as e:
        if e.errno != EEXIST:
            raise

def getExeDir(workspace, chdir=False):
    # handle ~ in pathname
    exeDir = pathjoin(workspace, 'exe', expanduser=True, abspath=True)

    if chdir:
        _logger.info("cd %s", exeDir)
        os.chdir(exeDir)

    return exeDir

def loadModuleFromPath(modulePath, raiseOnError=True):
    """
    Load a module from a '.py' or '.pyc' file from a path that ends in the
    module name, i.e., from "foo/bar/Baz.py", the module name is 'Baz'.

    :param modulePath: (str) the pathname of a python module (.py or .pyc)
    :param raiseOnError: (bool) if True, raise an error if the module cannot
       be loaded
    :return: (module) a reference to the loaded module, if loaded, else None.
    :raises: PygcamException
    """
    from imp import load_source, load_compiled  # lazy import to speed startup

    # Extract the module name from the module path
    modulePath = unixPath(modulePath)
    base       = os.path.basename(modulePath)
    moduleName = base.split('.')[0]

    _logger.debug('loading module %s' % modulePath)

    # Load the compiled code if it's a '.pyc', otherwise load the source code
    module = None
    try:
        module = load_source(moduleName, modulePath)
    except Exception as e:
        errorString = "Can't load module %s from path %s: %s" % (moduleName, modulePath, e)
        if raiseOnError:
            raise PygcamException(errorString)

        _logger.error(errorString)

    return module


def importFrom(modname, objname, asTuple=False):
    """
    Import `modname` and return reference to `objname` within the module.

    :param modname: (str) the name of a Python module
    :param objname: (str) the name of an object in module `modname`
    :param asTuple: (bool) if True a tuple is returned, otherwise just the object
    :return: (object or (module, object)) depending on `asTuple`
    """
    from importlib import import_module

    module = import_module(modname, package=None)
    obj    = getattr(module, objname)
    return ((module, obj) if asTuple else obj)


def importFromDotSpec(spec):
    """
    Import an object from an arbitrary dotted sequence of packages, e.g.,
    "a.b.c.x" by splitting this into "a.b.c" and "x" and calling importFrom().

    :param spec: (str) a specification of the form package.module.object
    :return: none
    :raises PygcamException: if the import fails
    """
    modname, objname = spec.rsplit('.', 1)

    try:
        return importFrom(modname, objname)

    except ImportError:
        raise PygcamException("Can't import '%s' from '%s'" % (objname, modname))

# Deprecated?
def readScenarioName(configFile):
    """
    Read the file `configFile` and extract the scenario name.

    :param configFile: (str) the path to a GCAM configuration file
    :return: (str) the name of the scenario defined in `configFile`
    """
    parser = ET.XMLParser(remove_blank_text=True)
    tree   = ET.parse(configFile, parser)
    scenarioName = tree.find('//Strings/Value[@name="scenarioName"]')
    return scenarioName.text

def printSeries(series, label, header='', asStr=False):
    """
    Print a `series` of values, with a give `label`.

    :param series: (convertible to pandas Series) the values
    :param label: (str) a label to print for the data
    :return: none
    """
    import pandas as pd

    if type(series) == pd.DataFrame:
        df = series
        df = df.T
    else:
        df = pd.DataFrame(pd.Series(series))  # DF is more convenient for printing

    df.columns = [label]

    oldPrecision = pd.get_option('precision')
    pd.set_option('precision', 5)
    s = "%s\n%s" % (header, df.T)
    pd.set_option('precision', oldPrecision)

    if asStr:
        return s
    else:
        print(s)


TRIAL_STRING_DELIMITER = ','

# Unused
def parseTrialString(string):
    """
    Converts a comma-separated list of ranges into a list of numbers.
    Ex. 1,3,4-6,2 becomes [1,3,4,5,6,2]. Duplicates are deleted. This
    function is the inverse of :func:`createTrialString`.

    :param string: (str) comma-separate list of ints or int ranges indicated
      by two ints separated by a hyphen.
    :return: (list) a list of ints
    """
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

    lst = sorted(set(lst))
    ranges = []
    for _, g in groupby(enumerate(lst), lambda pair: pair[0] - pair[1]):
        group = [str(x[1]) for x in g]
        if group[0] == group[-1]:
            ranges.append(group[0])
        else:
            ranges.append(group[0] + '-' + group[-1])
    return TRIAL_STRING_DELIMITER.join(ranges)

def chunkify(lst, chunks):
    """
    Iterator to turn a list into the number of lists given by chunks.
    In the case that len(lst) % chunksize != 0, all chunks are made as
    close to the same size as possible.

    :param lst: (list) a list of values
    :param chunks: (int) the number of chunks to create
    :return: iterator that returns one chunk at a time
    """
    l = len(lst)
    numWithExtraEntry = l % chunks  # this many chunks have one extra entry
    chunkSize = (l - numWithExtraEntry) // chunks + 1
    switch = numWithExtraEntry * chunkSize

    i = 0
    while i < l:
        if i == switch:
            chunkSize -= 1
        yield lst[i:i + chunkSize]
        i += chunkSize
