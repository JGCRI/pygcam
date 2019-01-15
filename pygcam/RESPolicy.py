#
# Goal is eventually to translate a file like ../etc/exampleRES.xml into standard GCAM XML.
#
from copy import deepcopy
import pandas as pd
from lxml import etree as ET
from lxml.etree import Element, SubElement

# Sadly, we must re-parse the XML to get the formatting right.
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

#
# Policy setup
#
def create_policy_region(region, commodity, market, consumer_elts, producer_elts, startYear=2015):
    policy_template =  """
    <policy-portfolio-standard name="{commodity}">
      <market>{market}</market>
      <policyType>RES</policyType>
      <constraint fillout="1" year="{startYear}">0</constraint>
      <min-price  fillout="1" year="{startYear}">-1000</min-price>
    </policy-portfolio-standard>"""

    policy_elt = ET.XML(policy_template.format(commodity=commodity, market=market,
                                               startYear=startYear))

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

# TBD: unclear when to use technology vs stub-technology
def create_stub_tech(tech, period_list):
    return create_elt('stub-technology', tech, period_list)

def create_tech(tech, period_list):
    return create_elt('technology', tech, period_list)

def create_subsector(subsector, tech_list):
    return create_elt('subsector', subsector, tech_list)

def create_sector(sector, subsector_list):
    return create_elt('supplysector', sector, subsector_list)

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

def create_supply_sectors(df, commodity, targets, outputRatio=1, pMultiplier=1):
    years = [pair[0] for pair in targets]
    sector_list = []

    for sector in df.sector.unique():
        sub_df = df[df.sector == sector]

        sub_list = []
        for subsector in sub_df.subsector.unique():
            tech_df = sub_df[sub_df.subsector == subsector]
            tech_list = []
            for tech in tech_df.technology.unique():
                period_list = []
                for year in years:
                    period = create_supply_period(year, commodity,
                                                  outputRatio=outputRatio,
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
                    period = create_demand_period(year, commodity, coefficient,
                                                  priceUnitConv=priceUnitConv)
                    period_list.append(period)

                tech_list.append(create_stub_tech(tech, period_list))

            sub_list.append(create_subsector(subsector, tech_list))

        sector_list.append(create_sector(sector, sub_list))

    return sector_list

def create_RES(tech_df, regions, commodity, market, targets, filename=None,
               outputRatio=1, pMultiplier=1, priceUnitConv=0):

    startYear = min([int(pair[0]) for pair in targets])

    consumer_df = tech_df.query('consumer == 1')
    consumer_elts = create_demand_sectors(consumer_df, commodity, targets,
                                          priceUnitConv=priceUnitConv)

    producer_df = tech_df.query('producer == 1')
    producer_elts = create_supply_sectors(producer_df, commodity, targets,
                                          outputRatio=outputRatio, pMultiplier=pMultiplier)

    region_list = [create_policy_region(region, commodity, market,
                                        deepcopy(consumer_elts), deepcopy(producer_elts),
                                        startYear=startYear) for region in regions]
    scenario = Element('scenario')
    world = SubElement(scenario, 'world')
    merge_elements(world, region_list)

    tree = ET.ElementTree(scenario)
    if filename:
        write_xml(tree, filename)

if __name__ == '__main__':
    tech_tups = [
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

        ('electricity',  'solar',           'PV',                         1,         1),
        ('electricity',  'solar',           'CSP',                        1,         1),
        ('electricity',  'solar',           'PV_storage',                 1,         1),
        ('electricity',  'solar',           'CSP_storage',                1,         1),
        ('electricity',  'wind',            'wind',                       1,         1),
        ('electricity',  'wind',            'wind_storage',               1,         1),
        ('elect_td_bld', 'rooftop_pv',      'rooftop_pv',                 1,         1)
    ]

    tech_df = pd.DataFrame(data=tech_tups,
                           columns=['sector', 'subsector', 'technology', 'producer', 'consumer'])

    regions    = ('USA',) # 'Canada')
    market     = 'USA'
    commodity  = 'WindSolarREC'
    targets    = ((2020, 0.15), (2025, 0.20), (2030, 0.25), (2035, 0.25),
                  (2040, 0.25), (2045, 0.25), (2050, 0.25))


    create_RES(tech_df, regions, commodity, market, targets, filename="/Users/rjp/bitbucket/gcam_res/xmlsrc/test/generated_res.xml")
