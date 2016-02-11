'''
.. Created on: 2/12/15
   Common functions and data

.. codeauthor:: Rich Plevin <rich@plevin.com>

'''

# Copyright (c) 2015, Richard Plevin.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
from itertools import chain
import subprocess
from .config import getParam

class ToolException(Exception):
    pass

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
    Run a shell command and optionally raise ToolException error.

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
            raise ToolException("\n*** Command failed: %s\n*** Command exited with status %s\n" % (command, exitStatus))

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
        raise ToolException("*** Reading file '%s' failed: %s\n" % (filename, e))

    return df

# For testing, workspace = '/Users/rjp/bitbucket/gcam-core'

def readRegionList(workspace):
    """
    Read the region names from the gcam-data-system input in the `workspace`.

    :param workspace: the path a Main_User_Workspace that has the file
      `input/gcam-data-system/_common/mappings/GCAM_region_names.csv`

    :return: a list of strings representing the defined regions
    """
    relpath = 'input/gcam-data-system/_common/mappings/GCAM_region_names.csv'
    path = os.path.join(workspace, relpath)

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
