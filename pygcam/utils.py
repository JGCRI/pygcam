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
import semver
import subprocess
import sys

from .config import getParam, getParamAsBoolean, pathjoin, unixPath
from .error import PygcamException, FileFormatError
from .file_utils import deleteFile
from .log import getLogger
from .version import VERSION

_logger = getLogger(__name__)

pygcam_version = semver.parse_version_info(VERSION)

def random_sleep(low_secs, high_secs):
    """
    Sleep a random number of seconds between low_secs and high_secs

    :param low_secs: (float) the minimum number of seconds to sleep
    :param high_secs: (float) the maximum number of seconds to sleep
    :return: none
    """
    from random import uniform
    from time import sleep

    sleep(uniform(low_secs, high_secs))

#
# Custom argparse "action" to parse comma-delimited strings to lists
# TBD: Use this in all relevant cmd-line cases
#
class ParseCommaList(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed with " % option_strings)

        super().__init__(option_strings, dest, **kwargs)

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
    otherwise use the built-in list of 32 regions. If config variable
    "GCAM.RegionDiscovery" is True (the default) then the reference configuration
    file is consulted L file is read to see whether the tag "socioeconomics"
    or "socio_usa" is defined, and the XML file indicated there is parsed to
    extract region names. If "GCAM.RegionDiscovery" is False, the built-in list
    of 32 regions is used.

    :param workspace: (str) The workspace to use as the base for interpreting
      relative pathnames in the reference configuration file. If ``workspace``
      is ``None``, the value of config variable "GCAM.RefWorkspace" is used.
    :param states: (str) One of {'together', 'only', 'none'}. Default is 'together'.
      Defines which regions to return: "together" means combine states and global
      regions (but drop USA from list of states); "only" means return only the
      states; "none" means return only the global regions (no states).
    :return: a list of strings with the names of the defined regions
    """
    from .csvCache import readCachedCsv

    global _RegionList, _StateList

    if states not in StateOptions:
        raise PygcamException(f'Called getRegionList with unrecognized value ({states}) for "state" argument. Must be one of {StateOptions}.')

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

    workspace = workspace or getParam('GCAM.RefWorkspace')

    if getParamAsBoolean('GCAM.RegionDiscovery'):   # True by default, but can be disabled by setting to False
        configFile = getParam('GCAM.RefConfigFile')
        if not os.path.lexists(configFile):
            _logger.error(f"GCAM reference config file '{configFile}' not found.")
            return

        parser = ET.XMLParser(remove_blank_text=True)
        tree   = ET.parse(configFile, parser)

        def _xmlpath(tag):
            elt = tree.find(f'//ScenarioComponents/Value[@name="{tag}"]')
            return None if elt is None else pathjoin(workspace, 'exe', elt.text, abspath=True)

        xml_USA    = _xmlpath('socio_usa')
        xml_global = _xmlpath('socioeconomics')

        if xml_global and os.path.lexists(xml_global):
            tree = ET.parse(xml_global, parser)
            _RegionList = tree.xpath('//region/@name')
        else:
            _logger.error(f"GCAM input file '{xml_global}' not found.")
            return

        if xml_USA:
            if not os.path.lexists(xml_USA):
                _logger.error(f"GCAM input file '{xml_USA}' not found.")
                return

            tree = ET.parse(xml_USA, parser)
            _StateList = tree.xpath('//region/@name')
            _StateList = sorted(set(_StateList) - {'USA'})  # don't include "USA" in list of states

    else: # Deprecated (probably) -- see note above.
        relpath = 'input/gcamdata/inst/extdata/common/GCAM_region_names.csv'
        skiprows = 6

        path = pathjoin(workspace, relpath) if workspace else None

        if path and os.path.lexists(path):
            _logger.debug("Reading region names from %s", path)
            df = readCachedCsv(path, skiprows=skiprows)
            _RegionList = list(df.region)

        else:
            from .constants import GCAM_32_REGIONS

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
    from queue import Queue
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
        raise FileFormatError(f'Unknown parameter {e} in project XML template string: {s}')


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

    :param command: (str or list of str) the command to run, with arguments.
    :param shell: if True, run `command` in a shell, otherwise run it directly.
    :param raiseError: if True, raise `PygcamException` on command failure.

    :return: exit status of executed command
    :raises: PygcamException
    """
    _logger.info(command)
    exitStatus = subprocess.call(command, shell=shell)
    if exitStatus != 0:
        if raiseError:
            raise PygcamException(f"\n*** Command failed: '{command}'\n*** Exit status {exitStatus}\n")

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
            raise Exception # trigger the "except" clause below
    except:
        raise PygcamException(f'Years must be specified as two years separated by a hyphen, as in "2020-2050", got "{years}"')

    cols = [str(y) for y in range(yearRange[0], yearRange[1]+1, timestep)]
    return cols

# TBD: use Sandbox instead
def getExeDir(workspace, chdir=False):
    # expanduser => handle leading tilde in pathname
    exeDir = pathjoin(workspace, 'exe', expanduser=True, abspath=True)

    if chdir:
        _logger.info("cd %s", exeDir)
        os.chdir(exeDir)

    return exeDir

# TBD: use Sandbox instead
def getBatchDir(scenario, resultsDir):
    """
    Get the name of the directory holding batch query results..

    :param scenario: (str) the name of a scenario
    :param resultsDir: (str) the directory in which the batch
        results directory should be created
    :return: (str) the pathname to the batch results directory
    """
    from .constants import QRESULTS_DIRNAME
    pathname = pathjoin(resultsDir, scenario, QRESULTS_DIRNAME)
    return pathname

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
    # imp is deprecated in Python3; use importlib instead
    from imp import load_source  # lazy import to speed startup

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


# Deprecated?
# def readScenarioName(configFile):
#     """
#     Read the file `configFile` and extract the scenario name.
#
#     :param configFile: (str) the path to a GCAM configuration file
#     :return: (str) the name of the scenario defined in `configFile`
#     """
#     parser = ET.XMLParser(remove_blank_text=True)
#     tree   = ET.parse(configFile, parser)
#     scenarioName = tree.find('//Strings/Value[@name="scenarioName"]')
#     return scenarioName.text
