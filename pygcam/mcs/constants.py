'''
Created on Dec 19, 2012


@author: Richard Plevin
@author: Sam Fendell

Copyright (c) 2012-2015. The Regents of the University of California (Regents)
and Richard Plevin. See the file COPYRIGHT.txt for details.
'''

# Status codes for invoked programs
RUNNER_SUCCESS = 0
RUNNER_FAILURE = -1

# DistGenerate
DEFAULT_BINS     = 30
DEFAULT_TRUNCATE = 3
COUNT_TITLE      = 'count'

DISCRETE_ENTRY_SEPARATOR = ':'
DICT_SEPARATOR = '='
DISTRO_SUFFIX  = 'distro'

# SymbolicSet, Distro:
DICT_REGEX = '^[^%s]+%s[^%s]+$' % (DICT_SEPARATOR, DICT_SEPARATOR, DICT_SEPARATOR)

# Multiple users
COMMENT_CHAR = '#'
PARAM_SUFFIX = 'param'


# Default region map for GCAM 4.
# TBD: Take this from pygcam.
RegionMap = {
    'Multiple': -1,
    'global': 0,
    'USA': 1,
    'Africa_Eastern': 2,
    'Africa_Northern': 3,
    'Africa_Southern': 4,
    'Africa_Western': 5,
    'Australia_NZ': 6,
    'Brazil': 7,
    'Canada': 8,
    'Central America and Caribbean': 9,
    'Central Asia': 10,
    'China': 11,
    'EU-12': 12,
    'EU-15': 13,
    'Europe_Eastern': 14,
    'Europe_Non_EU': 15,
    'European Free Trade Association': 16,
    'India': 17,
    'Indonesia': 18,
    'Japan': 19,
    'Mexico': 20,
    'Middle East': 21,
    'Pakistan': 22,
    'Russia': 23,
    'South Africa': 24,
    'South America_Northern': 25,
    'South America_Southern': 26,
    'South Asia': 27,
    'South Korea': 28,
    'Southeast Asia': 29,
    'Taiwan': 30,
    'Argentina': 31,
    'Colombia': 32
}
