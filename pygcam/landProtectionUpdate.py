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
    """
    Return the landtype and basin name, ignoring the protected field
    """
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
    for (reg, prot_tups) in prot_dict.items():
        reg_dict = node_dict[reg]
        land_basin_pairs = _landtype_basin_pairs(reg_dict)

        for (landtype, basin, prot_frac) in prot_tups:
            for (l, b) in land_basin_pairs:
                basin = basin or b              # if basin is not specified, apply to all basins in the region
                if landtype == l and basin == b:
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

    for reg, protReg in scenario.protRegDict.items():
        for prot in protReg.protections:
            fraction = prot.fraction
            basin = prot.basin
            prot_dict[reg] = [(landtype, basin, fraction) for landtype in prot.landClasses]

    _protect_land(tree, prot_dict)
