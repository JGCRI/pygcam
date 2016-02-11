'''
.. Created on: 2/12/15
   Common functions and data

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
from itertools import chain
import subprocess
from pygcam.config import getParam
from pygcam.error import PygcamException

GCAM_32_REGIONS = [
    'Africa_Eastern',
    'Africa_Northern',
    'Africa_Southern',
    'Africa_Western',
    'Argentina',
    'Australia_NZ',
    'Brazil',
    'Canada',
    'Central America and Caribbean',
    'Central Asia',
    'China',
    'Colombia',
    'EU-12',
    'EU-15',
    'Europe_Eastern',
    'Europe_Non_EU',
    'European Free Trade Association',
    'India',
    'Indonesia',
    'Japan',
    'Mexico',
    'Middle East',
    'Pakistan',
    'Russia',
    'South Africa',
    'South America_Northern',
    'South America_Southern',
    'South Asia',
    'South Korea',
    'Southeast Asia',
    'Taiwan',
    'USA'
]

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

def ensureXLSX(filename):
    """
    Force a filename to have the '.xlsx' extension, removing any other extension
    if present.

    :param filename: filename
    :return: filename with '.xlsx' extention
    """
    xlsx = '.xlsx'

    mainPart, extension = os.path.splitext(filename)
    if not extension:
        filename = mainPart + xlsx
    elif extension != xlsx:
        filename += xlsx

    return filename

def readCsv(filename, skiprows=1):
    """
    Read a .csv file and return a DataFrame with the file contents.
    :param filename: the path to a .csv file
    :param skiprows: the number of rows to skip before reading the data
    :return: a DataFrame with the file contents
    """
    import pandas as pd     # lazy import avoids long startup if readCsv is not needed

    try:
        df = pd.read_table(filename, sep=',', skiprows=skiprows, index_col=None)

    except Exception, e:
        raise PygcamException("*** Reading file '%s' failed: %s\n" % (filename, e))

    return df

# For testing, workspace = '/Users/rjp/bitbucket/gcam-core'

def getRegionList(workspace=None):
    """
    Get a list of the defined region names.

    :param workspace: the path to a ``Main_User_Workspace`` directory that
      has the file
      ``input/gcam-data-system/_common/mappings/GCAM_region_names.csv``,
      or ``None``, in which case the value of config variable
      ``GCAM.SourceWorkspace`` (if defined) is used. If `workspace` is
      empty or ``None``, and the config variable ``GCAM.SourceWorkspace`` is
      empty (the default value), the built-in default 32-region list is returned.
    :return: a list of strings with the names of the defined regions
    """
    relpath = 'input/gcam-data-system/_common/mappings/GCAM_region_names.csv'

    workspace = workspace or getParam('GCAM.SourceWorkspace')
    if not workspace:
        return GCAM_32_REGIONS

    path = os.path.join(workspace, relpath)

    print "Reading", path
    df = readCsv(path, skiprows=3)  # this is a gcam-data-system input file (different format)
    regions = list(df.region)
    return regions

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

def mkdirs(newdir):
    """
    Try to create the full path `newdir` and ignore the error if it already exists.

    :param newdir: the directory to create (along with any needed parent directories)
    :return: nothing
    """
    from errno import EEXIST

    try:
        os.makedirs(newdir, 0777)
    except OSError, e:
        if e.errno != EEXIST:
            raise

def readRegionMap(filename):
    """
    Read a region map file and return the contents as a dictionary with each
    key equal to a standard GCAM region and each value being the region to
    map the original to (which can be an existing GCAM region or a new name.)

    :param filename: the name of a file containing region mappings
    :return: a dictionary holding the mappings read from `filename`
    """
    import re
    mapping = {}
    pattern = re.compile('\t+')

    print "Reading region map '%s'" % filename
    with open(filename) as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if line[0] == '#':
            continue

        tokens = pattern.split(line)
        #print "Line: '%s', tokens: %s" % (line, tokens)
        assert len(tokens) == 2, "Badly formatted line in region map '%s': %s" % (filename, line)

        mapping[tokens[0]] = tokens[1]

    return mapping


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

    :param fuelname: the name of a fuel (currently must be from the set m{fame, bd, biodiesel, ethanol, etoh,
      'corn ethanol', 'cellulosic ethanol', 'sugar cane ethanol', ft, 'FT biofuels', biogasoline, bio-gasoline}.
    :return: energy density (MJ/gal)
    '''
    return FuelDensity[fuelname.lower()]


if __name__ == '__main__':
    l = getRegionList()
    print "(%d) %s" % (len(l), l)
    print
    l = getRegionList('/Users/rjp/bitbucket/gcam-core')
    print "(%d) %s" % (len(l), l)
