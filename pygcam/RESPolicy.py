#
# Goal is eventually to translate a file like ../etc/exampleRES.xml into standard GCAM XML.
#
from copy import copy, deepcopy
import pandas as pd
from lxml import etree as ET
from lxml.etree import Element, SubElement

# We deal only with one historical year (2010) and all future years
TIMESTEP = 5
LAST_HISTORICAL_YEAR = 2010
FIRST_MODELED_YEAR = LAST_HISTORICAL_YEAR + TIMESTEP
END_YEAR = 2100
GCAM_YEARS = [1975, 1990, 2005] + [year for year in range(LAST_HISTORICAL_YEAR, END_YEAR + 1, TIMESTEP)]

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
                         minPrice=0, startYear=FIRST_MODELED_YEAR):
    policy_template =  """
    <policy-portfolio-standard name="{commodity}">
      <market>{market}</market>
      <policyType>RES</policyType>
      <constraint fillout="1" year="{startYear}">0</constraint>
    </policy-portfolio-standard>"""

    policy_elt = ET.XML(policy_template.format(commodity=commodity, market=market,
                                               minPrice=minPrice,
                                               startYear=startYear))
    if minPrice:
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

def create_supply_sectors(df, commodity, targets, outputRatio=1, pMultiplier=1):
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
                                                  outputRatio=outputRatio,
                                                  pMultiplier=pMultiplier)
                    period_list.append(period)

                tech_list.append(create_tech(tech, period_list))

            sub_list.append(create_subsector(subsector, tech_list))

        sector_list.append(create_sector(sector, sub_list))

    return sector_list

#
# REC demand
#
def create_adjusted_coefficients(targets):
    """
    Create a dictionary of "adjusted-coefficient" elements (as XML text) for the given targets,
    where the key is the year and the value is the text for all elements starting at that year.
    """
    template = '<adjusted-coefficient year="{year}">{coefficient}</adjusted-coefficient>\n'

    # reverse a copy of the targets
    targets = sorted(targets, key=lambda tup: tup[0], reverse=True)  # sort by year, descending

    xml_dict = {}
    xml = ''

    for year, coefficient in targets:
        xml = template.format(year=year, coefficient=coefficient) + xml
        xml_dict[year] = xml

    return xml_dict

def create_demand_period(year, commodity, coefficients, priceUnitConv=0):
    template = '''
<period year="{year}">
  <minicam-energy-input name="{commodity}">
    {coefficients}
    <price-unit-conversion>{priceUnitConv}</price-unit-conversion>
  </minicam-energy-input>
</period>'''

    xml = template.format(year=year, commodity=commodity,
                          coefficients=coefficients, priceUnitConv=priceUnitConv)
    elt = ET.XML(xml)
    return elt

def create_demand_sectors(df, commodity, targets, priceUnitConv=0):
    sector_list = []

    coef_xml_dict = create_adjusted_coefficients(targets)

    for sector in df.sector.unique():
        sub_df = df[df.sector == sector]

        sub_list = []
        for subsector in sub_df.subsector.unique():
            tech_df = sub_df[sub_df.subsector == subsector]
            tech_list = []
            for tech in tech_df.technology.unique():
                period_list = []
                for year, coefficient in targets:
                    period = create_demand_period(year, commodity, coef_xml_dict[year],
                                                  priceUnitConv=priceUnitConv)
                    period_list.append(period)

                tech_list.append(create_tech(tech, period_list))

            sub_list.append(create_subsector(subsector, tech_list))

        sector_list.append(create_sector(sector, sub_list))

    return sector_list

def firstTarget(targets):
    """
    Return the first (year, coefficient) tuple in targets with coefficient != 0.
    """
    targets.sort(key=lambda tup: tup[0])    # sort by year

    for year, coefficient in targets:
        if coefficient: # ignore zeros
            return (year, coefficient)

def create_RES(tech_df, regions, commodity, market, targets, filename=None,
               outputRatio=1, pMultiplier=1, priceUnitConv=0, minPrice=None):

    startYear, startTarget = firstTarget(targets)

    # Create "targets" with initial policy target in years prior to start year
    # since older plants will retain this as their definition (until GCAM is patched)
    prepolicy = [(year, startTarget) for year in GCAM_YEARS if year < startYear]

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

    # TBD: change this to grab elec_*, electricity, and elect_td_bld
    locations = tree.xpath('//global-technology-database/location-info[starts-with(@sector-name, "elec_")]')

    for location in locations:
        sector    = location.get('sector-name')
        subsector = location.get('subsector-name')
        techs     = location.xpath('./technology/@name') + location.xpath('./intermittent-technology/@name')

        tech_dict[(sector, subsector)] = techs

    # TBD: return a DF?
    # (sector, subsector, tech, 0, 1)   # default: all consume nothing produces?
    # TBD: or just return techs and add producer/consumer cols in caller
    # tech_df = pd.DataFrame(data=tech_tups,
    #                        columns=['sector', 'subsector', 'technology', 'producer', 'consumer'])
    return tech_dict

def new_function(consumers, producers):
    """

    :param consumers: (list) tuples of REC consuming technologies expressed
      as (sector, subsector, tech), where tech or subsector and tech can be
      None => use everything in the given sector or subsector.
    :param producers: (list) analogous to `consumers` for REC producing techs.
    :return: (pandas.DataFrame) all producing and consuming technologies, with
      columns: [sector, subsector, tech, producer, consumer] where the producer
      and consumer columns are 1 where the tech is in the given category, else 0.
    """

if __name__ == '__main__':
    # TBD: change this to return all electricity techs,
    # TBD: convert to DF, then amend it to flip producer flag.
    tech_dict = get_electricity_techs()

    # technologies that consume RE certificates
    consumer_techs = []

    # These are just the techs with cooling technology variants
    for (sector, subsector), techs in tech_dict.items():
        for tech in techs:
            # handle special case of solar with cooling sub-techs
            isProducer = tech.startswith('CSP')
            consumer_techs.append((sector, subsector, tech, isProducer, 1))

    # Hydro is not treated as a credit producer in the current example
    consumer_techs.append(('electricity', 'hydro', 'hydro', 0, 1))

    # Technologies that produce RE certificates. CSP has cooling, so it's handled above.
    producer_techs = [
        ('electricity',  'solar',      'PV',            1, 1),
        ('electricity',  'solar',      'PV_storage',    1, 1),
        ('electricity',  'wind',       'wind',          1, 1),
        ('electricity',  'wind',       'wind_storage',  1, 1),
        ('elect_td_bld', 'rooftop_pv', 'rooftop_pv',    1, 1),
    ]

    tech_df = pd.DataFrame(data=consumer_techs + producer_techs,
                           columns=['sector', 'subsector', 'technology', 'producer', 'consumer'])

    regions    = ('USA',) # 'Canada')  # works for multiple regions
    market     = 'USA'
    commodity  = 'WindSolarREC'

    # targets = [(2020, 0.20), (2025, 0.25), (2030, 0.30), (2035, 0.375), (2040, 0.45),
    #            (2045, 0.55), (2050, 0.65), (2055, 0.75), (2060, 0.85)]

    # targets = [(2020, 0.20), (2025, 0.30), (2030, 0.40), (2035, 0.50), (2040, 0.60),
    #            (2045, 0.70), (2050, 0.80), (2055, 0.90), (2060, 0.975)]

    targets = [(2020, 0.20), (2025, 0.325), (2030, 0.475), (2035, 0.625), (2040, 0.75),
               (2045, 0.85), (2050, 0.95),  (2055, 0.965), (2060, 0.98)]

    create_RES(tech_df, regions, commodity, market, targets, # minPrice=-1000,
               filename="/Users/rjp/bitbucket/gcam_res/xmlsrc/test/generated_res.xml")
