'''
.. Created on: 2/12/15
   Common functions and data

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import sys
import re
import subprocess
import shutil
from itertools import chain
from tempfile import mkstemp, mkdtemp
from .config import getParam
from .error import PygcamException, FileFormatError
from .log import getLogger, getLogLevel

_logger = getLogger(__name__)

# Function to return current function name, or the caller, and so on up
# the stack, based on value of n.
getFuncName = lambda n=0: sys._getframe(n + 1).f_code.co_name

pat = re.compile('(\{[^\}]+\})')

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
        raise FileFormatError('Unknown parameter %s in project XML template' % e)

def getBooleanXML(value):
    """
    Get a value from an XML file and convert it into a boolean True or False.

    :param value: any value (it's first converted to a string)
    :return: True of the value is in ['true', '1'], False if the value
             is in ['false', '0']. An exception is raised if any other
             value is passed.
    :raises: PygcamException
    """
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

def unixPath(path, rmFinalSlash=False):
    """
    Convert a path to use Unix-style slashes, optionally
    removing the final slash, if present.

    :param path: (str) a pathname
    :param rmFinalSlash: (bool) True if a final slash should
           be removed, if present.
    :return: (str) the modified pathname
    """
    path = path.replace('\\', '/')
    if rmFinalSlash and path[-1] == '/':
        path = path[0:-1]

    return path

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

    :param years: (str) a string of the form "2020-2050"
    :param timestep: (int) the number of years between timesteps
    :return: (list of strings) the names of the corresponding columns
    """
    try:
        yearRange = map(int, years.split('-'))
        if not len(yearRange) == 2:
            raise Exception
    except:
        raise Exception('Years must be specified as two years separated by a hyphen, as in "2020-2050"')

    cols = map(str, range(yearRange[0], yearRange[1]+1, timestep))
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

    pathname = os.path.join(dirname, filename)

    _logger.debug("Generating file: %s", pathname)
    with open(pathname, 'w') as f:
        f.write(txt)

def getBatchDir(scenario, resultsDir, fromMCS=False):
    """
    Get the name of the directory holding batch query results. This differs
    when running in pygcam's "gt" or when running in GCAM-MCS.

    :param scenario: (str) the name of a scenario
    :param resultsDir: (str) the directory in which the batch results directory
           should be created
    :param fromMCS: (bool) True if being called from GCAM-MCS
    :return: (str) the pathname to the batch results directory
    """
    leafDir = 'queryResults' if fromMCS else 'batch-{scenario}'.format(scenario=scenario)
    pathname = os.path.join(resultsDir, scenario, leafDir)
    # '{resultsDir}/{scenario}/{leafDir}'.format(resultsDir=resultsDir, scenario=scenario, leafDir=leafDir)
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
    base       = os.path.basename(modulePath)
    moduleName = base.split('.')[0]

    _logger.debug('loading module %s' % base)

    # Load the compiled code if it's a '.pyc', otherwise load the source code
    module = None
    try:
        # TBD: this test isn't necessary since load_source loads a .pyc instead if found
        if base.endswith('.py'):
            module = load_source(moduleName, modulePath)
        elif base.endswith('.pyc'):
            module = load_compiled(moduleName, modulePath)
        else:
            raise Exception('Unknown module type (%s): file must must be .py or .pyc' % modulePath)

    except Exception, e:
        errorString = "Can't load module %s from path %s: %s" % (moduleName, modulePath, e)
        if raiseOnError:
            #logger.error(errorString)
            raise PygcamException(errorString)

        _logger.error(errorString)

    return module

def loadObjectFromPath(objName, modulePath, required=True):
    """
    Load a module and return a reference to a named object in that module.
    If 'required' and the object is not found, an error is raised, otherwise,
    None is returned if the object is not found.

    :param objName: (str) the name of an object to find in the `modulePath`
    :param modulePath: (str) the path to a python module to load
    :param required: (bool) if True and the object cannot be loaded, raise
      an error.
    :return: a reference to the loaded object, if loaded. If not loaded and
       `required` is False, return None.
    :raises: PygcamException
    """
    module = loadModuleFromPath(modulePath)
    obj    = getattr(module, objName, None)

    if obj or not required:
        return obj

    raise PygcamException("Module '%s' has no object named '%s'" % (modulePath, objName))

def importFrom(modname, objname, asTuple=False):
    """
    Import `modname` and return reference to ``modname.objname``
    """
    from importlib import import_module

    module = import_module(modname, package=None)
    obj    = getattr(module, objname)
    return module, obj if asTuple else obj

def importFromDotSpec(spec):
    '''
    Import object x from arbitrary dotted sequence of packages, e.g.,
    "a.b.c.x" by splitting this into "a.b.c" and "x" and calling importFrom.
    '''
    modname, objname = spec.rsplit('.', 1)

    try:
        return importFrom(modname, objname)

    except ImportError:
        raise PygcamException("Can't import '%s' from '%s'" % (objname, modname))

# TBD: move to common once debugged; use it in project.py as well.
class XMLFile(object):
    """
    Represents an XML file, which is parsed by lxml.etree and stored internally.

    :param xmlFile: pathname of the XML file
    :param schemaFile: optional XMLSchema file (or stream) to use for validation
    :param raiseError: if True, raise an error if validation fails
    :param rootClass: optional root class, which is instantiated for the parsed
      tree and stored internally
    :raises: FileFormatError
    """
    def __init__(self, xmlFile, schemaFile=None, raiseError=True, rootClass=None):
        from lxml import etree as ET

        parser = ET.XMLParser(remove_blank_text=True)
        self.tree = ET.parse(xmlFile, parser)

        if not schemaFile:
            return

        schemaDoc = ET.parse(schemaFile)
        schema = ET.XMLSchema(schemaDoc)

        if raiseError:
            try:
                schema.assertValid(self.tree)
            except ET.DocumentInvalid as e:
                raise FileFormatError("Validation of '%s'\n  using schema '%s' failed:\n  %s" % (xmlFile, schemaFile, e))
        else:
            return schema.validate(self.tree)

        self.root = rootClass(self.tree) if rootClass else None

    def getRoot(self):
        return self.root


def printSeries(series, label):
    """
    Print a `series` of values, with a give `label`.

    :param series: (convertible to pandas Series) the values
    :param label: (str) a label to print for the data
    :return: none
    """
    if getLogLevel() == 'DEBUG':
        import pandas as pd

        df = pd.DataFrame(pd.Series(series))  # DF is more convenient for printing
        df.columns = [label]
        pd.set_option('precision', 5)
        print df.T

def getTempFile(suffix='', tmpDir=None, text=True, delete=True):
    """
    Convenience function for common use pattern, which is to get
    the name of a temp file that needs to be deleted on app exit.

    :param suffix: (str) an extension to give the temporary file
    :param tmpDir: (str) the directory in which to create the file.
      (Defaults to the value of configuration file variable 'GCAM.TempDir',
      or '/tmp' if the variable is not found.
    :param text: True if this will be a text file
    :param delete: (bool) if False, don't delete the file on cleanup.
       (This is useful for debugging.)
    :return: (str) pathname of a new temporary file
    """
    obj = TempFile(suffix=suffix, text=text, tmpDir=tmpDir, delete=delete)
    return obj.path

def getTempDir(suffix='', tmpDir=None, delete=True):
    """
    Convenience function for common use pattern, which is to get the
    name of a temporary directory that needs to be deleted on app exit.

    :param suffix: (str) an extension to give the temporary file
    :param tmpDir: (str) the directory in which to create the new temporary
        directory (Defaults to the value of configuration file variable
        'GCAM.TempDir', or '/tmp' if the variable is not found.
    :param delete: (bool) if False, don't delete the file on cleanup.
       (This is useful for debugging.)
    :return: (str) pathname of a new temporary directory
    """
    obj = TempFile(suffix=suffix, tmpDir=tmpDir, delete=delete, createDir=True)
    return obj.path


class TempFile(object):
    """
    Class to create and track temporary files in one place
    so they can be deleted before an application exits.
    """
    Instances = {}

    def __init__(self, path=None, suffix='', tmpDir=None, delete=True,
                 openFile=False, text=True, createDir=False):
        """
        Construct the name of a temporary file.

        :param path: (str) a path to register for deletion. If given, all other
            args are ignored.
        :param suffix: (str) an extension to give the temporary file
        :param tmpDir: (str) the directory in which to create the (defaults to
            the value of configuration file variable 'GCAM.TempDir', or '/tmp'
            if the variable is not found.
        :param delete: (bool) whether deleteFile() should delete the file when
            called
        :param openFile: (bool) whether to leave the new file open (ignored if
            createDir is True)
        :param text: (bool) Set to False if this will not be a text file
        :param createDir: (bool) if True, a temporary directory will be created
            rather than a temporary file.
        :return: none
        """
        self.suffix = suffix
        self.delete = delete
        self.fd = None

        if path:
            # If we're called with a path, it's just to register a file for deletion.
            # We ignore all other parameters.
            self.path = path
        else:
            tmpDir = tmpDir or getParam('GCAM.TempDir') or "/tmp"
            mkdirs(tmpDir)

            if createDir:
                self.path = mkdtemp(suffix=suffix, dir=tmpDir)      # TODO: test this
            else:
                fd, tmpFile = mkstemp(suffix=suffix, dir=tmpDir, text=text)

                self.path = tmpFile
                if openFile:
                    self.fd = fd
                else:
                    # the caller is just after a pathname, so close it here
                    os.close(fd)
                    os.unlink(tmpFile)

        # save this instance by the unique path
        self.Instances[self.path] = self

    def deleteFile(self):
        """
        Remove the file for a TempFile instance if self.delete is True. In either
        case, delete the instance from the class instance dict.

        :return: none
        :raises: PygcamException if the path is not related to a TempFile instance.
        """
        path = self.path

        try:
            del self.Instances[path]
        except KeyError:
            raise PygcamException('No TempFile instance with name "%s"' % path)

        deleting = 'Deleting' if self.delete else 'Not deleting'
        _logger.debug("%s TempFile file '%s'", deleting, path)

        if self.delete:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.unlink(path)
            except Exception as e:
                _logger.debug('Failed to delete "%s": %s', path, e)

    @classmethod
    def deleteAll(cls):
        for obj in cls.Instances.values():
            obj.deleteFile()

    @classmethod
    def remove(cls, filename, raiseError=True):
        """
        Remove a temporary file and delete the TempFile instance from the dict.

        :param filename: (str) the name of a temp file created by this class
        :param raiseError (bool) if True, raise an exception if the filename is
          not a known TempFile.
        :return: none
        :raises: PygcamException if the path is not related to a TempFile instance.
        """
        try:
            obj = cls.Instances[filename]
            obj.deleteFile()
        except KeyError:
            if raiseError:
                raise PygcamException('No TempFile instance with name "%s"' % filename)

if __name__ == '__main__':
    pass
