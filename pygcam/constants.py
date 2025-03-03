'''
.. Copyright (c) 2016-2020 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
#
# Constants shared across modules. Note: use utils.getRegionList() rather than the
# hard-coded 32 regions to insulate against failures with different aggregations.
#
LOCAL_XML_NAME = 'local-xml'
DYN_XML_NAME   = 'dyn-xml'
APP_XML_NAME   = 'app-xml'
TRIAL_XML_NAME = 'trial-xml'
XML_SRC_NAME   = 'xmlsrc'
PARAMETERS_XML = "parameters.xml"
RESULTS_XML    = "results.xml"

# Common directory and filenames
CONFIG_XML = "config.xml"
SCENARIOS_XML = "scenarios.xml"
PROJECT_XML = "project.xml"
QUERY_DIRNAME  = "queries"
QRESULTS_DIRNAME = 'queryResults'
DIFFS_DIRNAME = 'diffs'
OUTPUT_DIRNAME = 'output'

CO2_PER_C = 3.666666667     # the exact value used in PNNL scripts

# Column names in land query files. Used to split compound GLU names
# into constituent parts (e.g., in diff.py and query.py)
LAND_LEAF = 'LandLeaf'
LAND_ALLOC = 'land_allocation'
LAND_USE = 'land_use'
BASIN = 'basin'
IRR_LEVEL = 'irr_level'
IRR_TYPE = 'irr_type'
SOIL_TYPE = 'soil_type'

from enum import Enum

class McsMode(Enum):
    TRIAL = 'trial'
    GENSIM = 'gensim'

    @classmethod
    def values(cls):
        return [x.value for x in cls.__members__.values()]

    def __eq__(self, value):
        return self.value == value

# These are the "standard" unmanaged classes. 'OtherArableLand' can also be protected.
UnmanagedLandClasses = ['UnmanagedPasture', 'UnmanagedForest', 'Shrubland', 'Grassland']

DEFAULT_TIMESTEP = 5    # 5 years

NUM_AEZS = 18

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

# 50 states + DC
GCAM_USA_STATES = [
    'AK', 'AL', 'AR', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE', 'FL',
    'GA', 'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY', 'LA', 'MA',
    'MD', 'ME', 'MI', 'MN', 'MO', 'MS', 'MT', 'NC', 'ND', 'NE',
    'NH', 'NJ', 'NM', 'NV', 'NY', 'OH', 'OK', 'OR', 'PA', 'RI',
    'SC', 'SD', 'TN', 'TX', 'UT', 'VA', 'VT', 'WA', 'WI', 'WV',
    'WY'
]


class FileVersions(Enum):
    FINAL    = -4   # => LOCAL_XML for non-MCS; TRIAL_XML for MCS
    PARENT   = -3   # parent's FINAL
    CURRENT  = -2   # return the "most local" existing version of the file
    NEXT     = -1   # the next "more local" version of the file
    REFERENCE = 0   # the Workspace version
    BASELINE  = 1   # the local-xml version for baseline scenario
    LOCAL_XML = 2   # the local-xml version for current scenario
    TRIAL_XML = 3   # the trial-xml version for current scenario
