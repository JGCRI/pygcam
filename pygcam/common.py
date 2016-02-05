'''
Created on: 2/12/15

@author: Rich Plevin (rich@plevin.com)

Common functions and data
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

def flatten(listOfLists):
    "Flatten one level of nesting"
    return list(chain.from_iterable(listOfLists))

def ensureXLSX(filename):
    '''Force an extension of ".xlsx" on a filename'''
    xlsx = '.xlsx'

    mainPart, extension = os.path.splitext(filename)
    if not extension:
        filename = mainPart + xlsx
    elif extension != xlsx:
        filename += xlsx

    return filename


def getTempFile(suffix, text=True, tmpDir=None):
    from tempfile import mkstemp

    tmpDir = tmpDir or getParam('GCAM.TempDir') or "/tmp"
    mkdirs(tmpDir)
    fd, tmpFile = mkstemp(suffix=suffix, dir=tmpDir, text=text)
    os.close(fd)    # we don't need this
    os.unlink(tmpFile)
    return tmpFile

def mkdirs(newdir):
    '''Try to create the full path and ignore error if it already exists'''
    from errno import EEXIST

    try:
        os.makedirs(newdir, 0777)
    except OSError, e:
        if e.errno != EEXIST:
            raise

def readRegionMap(filename):
    '''
    Read a region map file and return the contents as a dictionary with each
    key equal to a standard GCAM region and each value being the region to
    map the original to (which can be an existing GCAM region or a new name.)
    '''
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


#
# TBD: bundle some of these functions into a "GcamResults" class
#
def limitYears(df, years):
    'Return the DF, stripping years outside the given limits'
    first, last = map(int, years)
    yearCols  = map(int, filter(str.isdigit, df.columns))
    dropYears = map(str, filter(lambda y: y < first or y > last, yearCols))
    df.drop(dropYears, axis=1, inplace=True)


def dropExtraCols(df, inplace=True):
    columns = df.columns
    unnamed = 'Unnamed:'    # extra (empty) columns can sneak in; eliminate them
    dropCols = filter(lambda s: s[0:len(unnamed)] == unnamed, columns)

    unneeded  = set(['scenario', 'Notes', 'Date'])
    columnSet = set(columns)
    dropCols += columnSet & unneeded    # drop any columns in both sets

    resultDF = df.drop(dropCols, axis=1, inplace=inplace)
    return resultDF


def interpolateYears(df, startYear=0):
    '''
    Interpolate linearly between each pair of years in the GCAM output. The
    timestep is calculated from the numerical (string) column headings given
    in the dataframe, which are assumed to represent years in the timeseries.
    If startYear is given, begin interpolation at this year.
    '''
    yearCols = filter(str.isdigit, df.columns)
    years = map(int, yearCols)

    for i in range(0, len(years)-1):
        start = years[i]
        end   = years[i+1]
        timestep = end - start

        if timestep == 1:       # don't interpolate annual results (LUC emissions, forcing)
            continue

        startCol = df[str(start)]
        endCol   = df[str(end)]

        # compute vector of annual deltas for each row
        delta = (endCol - startCol)/timestep

        # interpolate the whole column -- but don't interpolate before the start year
        for j in range(1, timestep):
            nextYear = start + j
            df[str(nextYear)] = df[str(nextYear-1)] + (0 if nextYear < startYear else delta)

    yearCols = filter(str.isdigit, df.columns)  # get annualized year columns
    years = map(int, yearCols)       # sort as integers
    years.sort()
    yearCols = map(str, years)       # convert back to strings, now sorted

    nonYearCols = list(set(df.columns) - set(yearCols))
    result = df.reindex_axis(nonYearCols + yearCols, axis=1, copy=True)
    return result

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
    :param fuelname: the name of a fuel (currently must be one of {fame,bd,ethanol,etoh,biogasoline,bio-gasoline}.
    :return: energy density (MJ/gal)
    '''
    return FuelDensity[fuelname.lower()]
