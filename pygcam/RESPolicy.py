#
# Goal is eventually to translate a file like ../etc/exampleRES.xml into standard GCAM XML.
#
from copy import deepcopy
import pandas as pd
from lxml import etree as ET
from lxml.etree import Element, SubElement

# We deal only with one historical year (2010) and all future years
LAST_HISTORICAL = 2010
END_YEAR = 2100
TIMESTEP = 5
GCAM_YEARS = [year for year in range(LAST_HISTORICAL, END_YEAR+1, TIMESTEP)]

SMALL_NUMBER = 1E-6

# Oddly, we must re-parse the XML to get the formatting right.
def write_xml(tree, filename):
    from io import StringIO

    parser = ET.XMLParser(remove_blank_text=True)
    xml = ET.tostring(tree.getroot())
    file_obj = StringIO(xml.decode('utf-8'))
    tree = ET.parse(file_obj, parser)

    tree.write(filename, pretty_print=True, xml_declaration=True)

# Surface level (tag and attribute) comparison of elements
def match_element(elt1, elt2):
    if elt1.tag != elt2.tag:
        return False

    attr1 = elt1.attrib
    attr2 = elt2.attrib

    if len(attr1) != len(attr2):
        return False

    try:
        for key, value in attr1.items():
            if value != attr2[key]:
                return False
    except KeyError:
        return False

    return True

def merge_element(parent, new_elt):
    """
    Add an element if none of parent's children has the same tag and attributes
    as element. If a match is found, add element's children to those of the
    matching element.
    """
    for sibling in parent:
        if match_element(new_elt, sibling):
            merge_elements(sibling, new_elt.getchildren())
            return

    # if it wasn't merged, append it to parent
    parent.append(deepcopy(new_elt))

def merge_elements(parent, elt_list):
    """
    For each element in elt_list, add the append to parent if none of parent's children has the
    same tag and attributes as element. If a match is found, merge element's children with those
    of the matching element, recursively.
    """
    for elt in elt_list:
        merge_element(parent, elt)

def ElementWithText(tag, text, **kwargs):
    elt = Element(tag, **kwargs)
    elt.text = str(text)
    return elt

def SubElementWithText(parent, tag, text, **kwargs):
    elt = ElementWithText(tag, text, **kwargs)
    parent.append(elt)
    return elt

#
# Policy setup
#
def create_policy_region(region, commodity, market, consumer_elts, producer_elts,
                         minPrice=None,  startYear=2015):
    policy_template =  """
    <policy-portfolio-standard name="{commodity}">
      <market>{market}</market>
      <policyType>RES</policyType>
      <constraint fillout="1" year="{startYear}">0</constraint>
    </policy-portfolio-standard>"""

    policy_elt = ET.XML(policy_template.format(commodity=commodity, market=market,
                                               minPrice=minPrice, startYear=startYear))

    if minPrice is not None:
        SubElementWithText(policy_elt, 'min-price', minPrice, year=str(startYear))

    # Disable markets for the RECs prior to start year
    for year in GCAM_YEARS:
        if year < startYear:
            SubElementWithText(policy_elt, 'fixedTax', 0, year=str(year))
        else:
            break

    region_elt = Element('region', name=region)
    region_elt.append(policy_elt)
    region_elt.extend(consumer_elts)
    merge_elements(region_elt, producer_elts)

    return region_elt

#
# REC demand
#

def create_demand_period(year, commodity, coefficient, priceUnitConv=0):
    template = '''
<period year="{year}">
  <minicam-energy-input name="{commodity}">
    <coefficient>{coefficient}</coefficient>
    <price-unit-conversion>{priceUnitConv}</price-unit-conversion>
  </minicam-energy-input>
</period>'''

    xml = template.format(year=year, commodity=commodity,
                          coefficient=coefficient, priceUnitConv=priceUnitConv)
    elt = ET.XML(xml)
    return elt

def create_elt(tag, name, child_list):
    elt = Element(tag, name=name)
    elt.extend(deepcopy(child_list))    # since we reuse redundant elements
    return elt

def create_tech(tech, period_list, stub=True):
    tag = 'stub-technology' if stub else 'technology'
    return create_elt(tag, tech, period_list)

def create_subsector(subsector, tech_list):
    return create_elt('subsector', subsector, tech_list)

def create_sector(sector, subsector_list, pass_through=False):
    tag = 'pass-through-sector' if pass_through else 'supplysector'
    return create_elt(tag, sector, subsector_list)

#
# REC supply
#

def create_supply_period(year, commodity, outputRatio, pMultiplier):
    template = '''
<period year="{year}">
  <res-secondary-output name="{commodity}">
    <output-ratio>{outputRatio}</output-ratio>
    <pMultiplier>{pMultiplier}</pMultiplier>
  </res-secondary-output>
</period>'''

    xml = template.format(year=year, commodity=commodity,
                          outputRatio=outputRatio, pMultiplier=pMultiplier)
    elt = ET.XML(xml)
    return elt

def   create_supply_sectors(df, commodity, targets, outputRatio=1, pMultiplier=1):
    sector_list = []

    for sector in df.sector.unique():
        sub_df = df[df.sector == sector]

        sub_list = []
        for subsector in sub_df.subsector.unique():
            tech_df = sub_df[sub_df.subsector == subsector]
            tech_list = []
            for tech in tech_df.technology.unique():
                period_list = []
                for year, coefficient in targets:
                    period = create_supply_period(year, commodity,
                                                  outputRatio=outputRatio if coefficient else SMALL_NUMBER,
                                                  pMultiplier=pMultiplier)
                    period_list.append(period)

                tech_list.append(create_tech(tech, period_list))

            sub_list.append(create_subsector(subsector, tech_list))

        sector_list.append(create_sector(sector, sub_list))

    return sector_list

def create_demand_sectors(df, commodity, targets, priceUnitConv=0):
    sector_list = []

    for sector in df.sector.unique():
        sub_df = df[df.sector == sector]

        sub_list = []
        for subsector in sub_df.subsector.unique():
            tech_df = sub_df[sub_df.subsector == subsector]
            tech_list = []
            for tech in tech_df.technology.unique():
                period_list = []
                for year, coefficient in targets:
                    period = create_demand_period(year, commodity, coefficient or SMALL_NUMBER,
                                                  priceUnitConv=priceUnitConv)
                    period_list.append(period)

                tech_list.append(create_tech(tech, period_list))

            sub_list.append(create_subsector(subsector, tech_list))

        sector_list.append(create_sector(sector, sub_list))

    return sector_list

def firstYear(targets):
    """
    Return the first year in targets (a list of tuples of (year, coefficient)
    for which the coefficient is > 0.
    """
    return min([int(pair[0]) for pair in targets if pair[1] > 0])

def create_RES(tech_df, regions, commodity, market, targets, filename=None,
               outputRatio=1, pMultiplier=1, priceUnitConv=0, minPrice=None):

    startYear = firstYear(targets)

    # Create "targets" with zero coefficient in years prior to start year so market exists
    prepolicy = [(year, 0) for year in GCAM_YEARS if year < startYear]

    targets = prepolicy + targets

    consumer_df = tech_df.query('consumer == 1')
    consumer_elts = create_demand_sectors(consumer_df, commodity, targets,
                                          priceUnitConv=priceUnitConv)

    producer_df = tech_df.query('producer == 1')
    producer_elts = create_supply_sectors(producer_df, commodity, targets,
                                          outputRatio=outputRatio, pMultiplier=pMultiplier)

    region_list = [create_policy_region(region, commodity, market,
                                        deepcopy(consumer_elts), deepcopy(producer_elts),
                                        startYear=startYear, minPrice=minPrice) for region in regions]
    scenario = Element('scenario')
    world = SubElement(scenario, 'world')
    merge_elements(world, region_list)

    tree = ET.ElementTree(scenario)
    if filename:
        print("Writing", filename)
        write_xml(tree, filename)

def get_electricity_techs():
    from pygcam.config import getParam, pathjoin
    from pygcam.XMLFile import XMLFile
    electricity_xml = pathjoin(getParam('GCAM.RefWorkspace'), 'input', 'gcamdata', 'xml', 'electricity_water.xml')
    tree = XMLFile(electricity_xml).getTree()

    tech_dict = {}

    locations = tree.xpath('//global-technology-database/location-info[starts-with(@sector-name, "elec_")]')

    for location in locations:
        sector    = location.get('sector-name')
        subsector = location.get('subsector-name')
        techs     = location.xpath('./technology/@name') + location.xpath('./intermittent-technology/@name')

        tech_dict[(sector, subsector)] = techs

    return tech_dict

if __name__ == '__main__':
    tech_dict = get_electricity_techs()

    # technologies that consume RE certificates
    consumer_techs = []

    # These are just the techs with cooling technology variants
    for pair, techs in tech_dict.items():
        sector = pair[0]
        subsector = pair[1]

        for tech in techs:
            isProducer = tech.startswith('CSP') # has cooling so it's in the consumer list
            consumer_techs.append((sector, subsector, tech, isProducer, 1))

    consumer_techs.append(('electricity', 'hydro', 'hydro', 0, 1))  # might be a credit producer in some policies

    consumer_tups_old = [
        # Adapted from gcam-v5.1.2/input/gcamdata/inst/extdata/energy/A23.globaltech_capacity_factor.csv
        # except for the REC producer/consumer columns, which define the techs the policy applies to.
        #
        #                                                                REC        REC
        # sector         subsector          technology                 producer   consumer
        # ============== =============      ====================       ========   ========
        ('electricity',  'coal',            'coal (conv pul)',            0,         1),
        ('electricity',  'coal',            'coal (conv pul CCS)',        0,         1),
        ('electricity',  'coal',            'coal (IGCC)',                0,         1),
        ('electricity',  'coal',            'coal (IGCC CCS)',            0,         1),
        ('electricity',  'gas',             'gas (steam/CT)',             0,         1),
        ('electricity',  'gas',             'gas (CC)',                   0,         1),
        ('electricity',  'gas',             'gas (CC CCS)',               0,         1),
        ('electricity',  'refined liquids', 'refined liquids (steam/CT)', 0,         1),
        ('electricity',  'refined liquids', 'refined liquids (CC)',       0,         1),
        ('electricity',  'refined liquids', 'refined liquids (CC CCS)',   0,         1),
        ('electricity',  'nuclear',         'Gen_II_LWR',                 0,         1),
    #   ('electricity',  'nuclear',         'GEN_III',                    0,         1),    # doesn't exist in reference case?
        ('electricity',  'geothermal',      'geothermal',                 0,         1),
        ('electricity',  'biomass',         'biomass (conv)',             0,         1),
        ('electricity',  'biomass',         'biomass (conv CCS)',         0,         1),
        ('electricity',  'biomass',         'biomass (IGCC)',             0,         1),
        ('electricity',  'biomass',         'biomass (IGCC CCS)',         0,         1),

        # ('electricity_net_ownuse', 'electricity_net_ownuse', 'electricity_net_ownuse', 0, 1)
    ]

    # Technologies that produce RE certificates
    producer_techs = [
        ('electricity',  'solar',      'PV',            1, 1),
        ('electricity',  'solar',      'PV_storage',    1, 1),
        ('electricity',  'wind',       'wind',          1, 1),
        ('electricity',  'wind',       'wind_storage',  1, 1),
        ('elect_td_bld', 'rooftop_pv', 'rooftop_pv',    1, 1),
        # CSP has cooling, so we don't set it here
    ]

    tech_tups = consumer_techs + producer_techs

    tech_df = pd.DataFrame(data=tech_tups,
                           columns=['sector', 'subsector', 'technology', 'producer', 'consumer'])

    regions    = ('USA',) # 'Canada')  # works for multiple regions
    market     = 'USA'
    commodity  = 'WindSolarREC'

    targets = [(2020, 0.10), (2025, 0.15), (2030, 0.21), (2035, 0.28), (2040, 0.35), (2045, 0.45), (2050, 0.55)]

    create_RES(tech_df, regions, commodity, market, targets,
               # minPrice=-1000,
               filename="/Users/rjp/bitbucket/gcam_res/xmlsrc/test/generated_res.xml")
