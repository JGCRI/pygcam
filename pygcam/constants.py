'''
.. Copyright (c) 2016-2020 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
#
# Constants shared across modules. Note: use utils.getRegionList() rather than the
# hard-coded 32 regions to insulate against failures with different aggregations.
#

# TBD: move to gcamtool package
LOCAL_XML_NAME = 'local-xml'
DYN_XML_NAME   = 'dyn-xml'
XML_SRC_NAME   = 'xmlsrc'

# These are the "standard" unmanaged classes. 'OtherArableLand' can also be protected.
UnmanagedLandClasses = ['UnmanagedPasture', 'UnmanagedForest', 'Shrubland', 'Grassland']

# TBD: keep in pygcam package
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

