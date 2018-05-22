from lxml import etree as ET

from .error import FileFormatError
from .landProtection import Scenario
from .log import getLogger

_logger = getLogger(__name__)

PROTECTED = 'Protected'

def pp(elt):
    print(ET.tostring(elt, pretty_print=True))

def eltname(elt):
    return elt.get('name')


def _parse_land_basin(name):
    if name.startswith(PROTECTED):
        protected = PROTECTED
        name = name[len(PROTECTED):]
    else:
        protected = ''

    pos = name.rfind('_')
    landtype = name[:pos]
    basin = name[pos + 1:]
    return (landtype, basin, protected)


def _compose_land_basin(landtype, basin, protection):
    return "{}{}_{}".format(protection, landtype, basin)

def _set_land_values(land_leaf, vals):
    """
    Update allocation and landAllocation nodes with the values
    computed for each year.
    """
    nodes = land_leaf.xpath('.//allocation|.//landAllocation')
    for node in nodes:
        year = node.get('year')
        node.text = str(vals[year])

def _get_allocation(reg_dict, landtype, basin, protected=''):
    import pandas as pd

    land_key = protected + landtype + '_' + basin
    land_leaf = reg_dict[land_key]
    nodes = land_leaf.xpath('.//allocation[@year<1975]|.//landAllocation')
    [(node.get('year'), float(node.text)) for node in nodes]
    values = [(node.get('year'), float(node.text)) for node in nodes]
    ind, val = zip(*values)
    s = pd.Series(val, index=ind)
    return s

def _get_total_area(reg_dict, landtype, basin):
    unprot = _get_allocation(reg_dict, landtype, basin, protected='')
    prot   = _get_allocation(reg_dict, landtype, basin, protected=PROTECTED)
    return prot + unprot

def _landtype_basin_pairs(reg_dict):
    """Return the landtype and basin name, ignoring the protected field"""
    pairs = [_parse_land_basin(key)[0:2] for key in reg_dict.keys() if key.startswith(PROTECTED)]
    return pairs

def _get_land_leafs(tree, region):
    return tree.xpath('//region[@name="{}"]//UnmanagedLandLeaf'.format(region))

def _cache_land_nodes(tree, regions):
    d = {}
    for reg in regions:
        nodes = _get_land_leafs(tree, reg)
        d[reg] = {eltname(node) : node for node in nodes}
    return d

def _update_protection(reg_dict, landtype, basin, prot_vals, unprot_vals):
    def _upd(protected, vals):
        leaf_name = _compose_land_basin(landtype, basin, protected)
        land_leaf = reg_dict[leaf_name]
        _set_land_values(land_leaf, vals)

    _upd(PROTECTED, prot_vals)
    _upd('', unprot_vals)

def _protect_land(tree, prot_dict):
    node_dict = _cache_land_nodes(tree, prot_dict.keys())
    for (reg, prot_pairs) in prot_dict.iteritems():
        reg_dict = node_dict[reg]
        land_basin_pairs = _landtype_basin_pairs(reg_dict)

        for (landtype, prot_frac) in prot_pairs:
            for (ltype, basin) in land_basin_pairs:
                if landtype == ltype:
                    # print("Processing {}, {}, {}".format(reg, landtype, basin))
                    total = _get_total_area(reg_dict, landtype, basin)
                    prot_vals   = total * prot_frac
                    unprot_vals = total - prot_vals
                    _update_protection(reg_dict, landtype, basin, prot_vals, unprot_vals)

#
# Modified from landProtection.py method of same name
#
def protectLandTree(tree, scenarioName):
    """
    Apply the protection scenario `scenarioName` to the parsed XML file `tree`.
    This interface is provided so WriteFuncs (which are passed an open XMLInputFile)
    can apply protection scenarios.

    :param tree: (lxml ElementTree) a tree for a parsed XML input file.
    :param scenarioName: (str) the name of the scenario to apply
    :return: none
    """
    _logger.info("Applying protection scenario %s", scenarioName)

    scenario = Scenario.getScenario(scenarioName)
    if not scenario:
        raise FileFormatError("Scenario '%s' was not found" % scenarioName)

    prot_dict = {}

    for reg, protReg in scenario.protRegDict.iteritems():
        for prot in protReg.protections:
            fraction = prot.fraction
            prot_dict[reg] = [(landtype, fraction) for landtype in prot.landClasses]

    _protect_land(tree, prot_dict)



# def save_unmgd_land_allocation(outfile):
#     """
#     Save a CSV file with reference allocations to all the unmanaged land categories:
#     'Shrubland', 'Grassland', 'UnmanagedPasture', and 'UnmanagedForest'. The original
#     CSV file has GLU (geographical land unit) and region ID keys that we map to their
#     string values for use in XML files.
#     """
#     import pandas as pd
#
#     data_sys_dir = pathjoin(getParam('GCAM.RefWorkspace'), 'input', 'gcam-data-system')
#
#     def _readcsv(path, skiprows=0):
#         filename = data_sys_dir + path
#         df = pd.read_csv(filename, skiprows=skiprows)
#         return df
#
#     df = _readcsv('/aglu-data/level1/L125.LC_bm2_R_LT_Yh_GLU.csv', skiprows=5)
#
#     regionMap = _readcsv('/_common/mappings/GCAM_region_names_32reg.csv', skiprows=3)
#     regionMap.columns = ['ID', 'region']
#     regionMap.set_index('ID', inplace=True)
#     region = regionMap.region
#
#     basinMapFull = _readcsv('/water-data/mappings/basin_to_country_mapping.csv', skiprows=2)
#     basinSlice = basinMapFull[['GLU_code', 'GLU_name']]
#     basinSlice.set_index('GLU_code', inplace=True)
#     basinMap = basinSlice.GLU_name
#
#     years = range(1700,1951, 50) + [1975, 1990, 2005, 2010]
#     xyears = ["X{}".format(year) for year in years]
#     cols = ['GCAM_region_ID', 'Land_Type', 'GLU'] + xyears
#     result = df.query("Land_Type in {}".format(UnmanagedLandClasses))
#     unmgd = result[cols].copy()
#
#     unmgd['region'] = unmgd['GCAM_region_ID'].map(region)
#     unmgd['basin']  = unmgd['GLU'].map(basinMap)
#     unmgd.drop(['GCAM_region_ID', 'GLU'], axis=1, inplace=True)
#
#     unmgd.columns = [col[1:] if col[0] == 'X' else col for col in unmgd.columns]
#     unmgd.rename(index=str, columns={'Land_Type': 'landtype'}, inplace=True)
#
#     unmgd.set_index(['region', 'landtype', 'basin'], inplace=True)
#     unmgd.to_csv(outfile)
#
# def load_unmgd_land_allocation(pathname):
#     """
#     Load the land allocation CSV file saved by `save_unmgd_land_allocation`.
#     """
#     import pandas as pd
#     df = pd.read_csv(pathname, index_col=['region', 'landtype', 'basin'])
#     return df
