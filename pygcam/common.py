'''
.. Created on: 2/12/15
   Common functions and data

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import subprocess
import sys
from itertools import chain
from pygcam.config import getParam
from pygcam.error import PygcamException
from pygcam.log import getLogger

_logger = getLogger(__name__)

# Function to return current function name, or the caller, and so on up
# the stack, based on value of n.
getFuncName = lambda n=0: sys._getframe(n + 1).f_code.co_name

def getBooleanXML(value):
    false = ["false", "0"]
    true  = ["true", "1"]

    val = str(value).strip()
    if val not in true + false:
        raise PygcamException("Can't convert '%s' to boolean; must be in {false,no,0,true,yes,1} (case sensitive)." % value)

    return (val in true)

def coercible(value, type):
    """
    Attempt to coerce a value to `type` and raise an error on failure.

    :param value: any value coercible to `type`
    :return: (`type`) the coerced value
    :raises: PygcamException
    """
    try:
        value = type(value)
    except ValueError as e:
        raise PygcamException("%s: %r is not coercible to %s" % (getFuncName(1), value, type.__name__))

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
    exitStatus = subprocess.call(command, shell=shell)
    if exitStatus <> 0:
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

def getYearCols(years, timestep=5):
    """
    Generate a list of names of year columns in GCAM result files from a
    string indicating a year range.
    :param years: a string of the form "2020-2050"
    :param timestep: the number of years between timesteps
    :return: the names of the corresponding columns
    """
    try:
        yearRange = map(int, years.split('-'))
        if not len(yearRange) == 2:
            raise Exception
    except:
        raise Exception('Years must be specified as two years separated by a hyphen, as in "2020-2050"')

    cols = map(str, range(yearRange[0], yearRange[1]+1, timestep))
    return cols

# Consolidate with fn in query.py


def saveToFile(txt, dirname, filename):
    mkdirs(dirname)
    pathname = os.path.join(dirname, filename)
    _logger.debug("    Generating file:", pathname)
    with open(pathname, 'w') as f:
        f.write(txt)

def getTempFile(suffix, text=True, tmpDir=None):
    """
    Construct the name of a temporary file.

    :param suffix: the extension to give the temporary file
    :param text: True if this will be a text file
    :param tmpDir: the directory in which to create the (defaults to
      the value of configuration file variable 'GCAM.TempDir', or '/tmp'
      if the variable is not found.
    :return: the name of the temporary file
    """
    from tempfile import mkstemp

    tmpDir = tmpDir or getParam('GCAM.TempDir') or "/tmp"

    mkdirs(tmpDir)
    fd, tmpFile = mkstemp(suffix=suffix, dir=tmpDir, text=text)
    os.close(fd)    # we don't need this
    os.unlink(tmpFile)
    return tmpFile

def getBatchDir(baseline, resultsDir, fromMCS=False):
    leafDir = 'queryResults' if fromMCS else 'batch-{baseline}'.format(baseline=baseline)
    pathname = os.path.join(resultsDir, baseline, leafDir)
    # '{resultsDir}/{baseline}/{leafDir}'.format(resultsDir=resultsDir, baseline=baseline, leafDir=leafDir)
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
    except OSError, e:
        if e.errno != EEXIST:
            raise

def loadModuleFromPath(modulePath):
    '''
    The load a module from a '.py' or '.pyc' file from a path that ends in the
    module name, i.e., from "foo/bar/Baz.py", the module name is 'Baz'.
    '''
    from imp import load_source, load_compiled  # lazy import to speed startup

    # Extract the module name from the module path
    base       = os.path.basename(modulePath)
    moduleName = base.split('.')[0]

    #logger.info('loading module %s' % base)

    # Load the compiled code if it's a '.pyc', otherwise load the source code
    module = None
    try:
        if base.endswith('.py'):
            module = load_source(moduleName, modulePath)
        elif base.endswith('.pyc'):
            module = load_compiled(moduleName, modulePath)
        else:
            raise Exception('Unknown module type (%s): file must must be .py or .pyc' % modulePath)

    except Exception, e:
        errorString = "Can't load module %s from path %s: %s" % (moduleName, modulePath, e)
        #logger.error(errorString)
        raise PygcamException(errorString)

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

    raise Exception("Module '%s' has no object named '%s'" % (modulePath, objName))

# def importFrom(modname, objname):
#     """
#     Import `modname` and return reference to ``modname.objname``
#     """
#     from importlib import import_module
#
#     module = import_module(modname, package=None)
#     return getattr(module, objname)
#
# def importFromDotSpec(spec):
#     '''
#     Import object x from arbitrary dotted sequence of packages, e.g.,
#     "a.b.c.x" by splitting this into "a.b.c" and "x" and calling importFrom.
#     '''
#     modname, objname = spec.rsplit('.', 1)
#
#     try:
#         return importFrom(modname, objname)
#
#     except ImportError:
#         raise PygcamException("Can't import '%s' from '%s'" % (objname, modname))


FT_DIESEL_MJ_PER_GAL   = 130.4
FAME_MJ_PER_GAL        = 126.0
ETOH_MJ_PER_GAL        = 81.3
BIOGASOLINE_MJ_PER_GAL = 122.3     # from GREET1_2011

FuelDensity = {
    'fame'          : FAME_MJ_PER_GAL,
    'bd'            : FAME_MJ_PER_GAL,
    'biodiesel'     : FAME_MJ_PER_GAL,          # GCAM name

    'ethanol'            : ETOH_MJ_PER_GAL,
    'etoh'               : ETOH_MJ_PER_GAL,
    'corn ethanol'       : ETOH_MJ_PER_GAL,     # GCAM name
    'cellulosic ethanol' : ETOH_MJ_PER_GAL,     # GCAM name
    'sugar cane ethanol' : ETOH_MJ_PER_GAL,     # GCAM name

    'ft'            : FT_DIESEL_MJ_PER_GAL,
    'FT biofuels'   : FT_DIESEL_MJ_PER_GAL,     # GCAM name

    'biogasoline'   : BIOGASOLINE_MJ_PER_GAL,
    'bio-gasoline'  : BIOGASOLINE_MJ_PER_GAL
}

def fuelDensityMjPerGal(fuelname):
    '''
    Return the fuel energy density of the named fuel.

    :param fuelname: the name of a fuel, which must be one of:
      ``{fame, bd, biodiesel, ethanol, etoh, corn ethanol, cellulosic ethanol, sugar cane ethanol, ft, FT biofuels, biogasoline, bio-gasoline}``.
    :return: energy density (MJ/gal)
    '''
    return FuelDensity[fuelname.lower()]


if __name__ == '__main__':

    # TBD: move to unittest
    if False:
        print ensureExtension('/a/b/c/foo', '.baz')
        print ensureExtension('/a/b/c/foo.bar', 'baz')

        l = getRegionList()
        print "(%d) %s" % (len(l), l)
        print
        l = getRegionList('/Users/rjp/bitbucket/gcam-core')
        print "(%d) %s" % (len(l), l)
