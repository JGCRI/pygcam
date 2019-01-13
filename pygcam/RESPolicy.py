#
# Goal is eventually to translate a file like ../etc/exampleRES.xml into standard GCAM XML.
#
import pandas as pd
from lxml import etree as ET

# Clean up an xml string
def prettify(xml, xml_declaration=True, encoding='utf-8'):
    elt = ET.XML(xml)
    xml = ET.tostring(elt, xml_declaration=xml_declaration, encoding=encoding, pretty_print=True)
    return xml

def cat(str_list):
    return '\n'.join(str_list)

electricity_producers = [
    #   sector      subsector     technology
    #   ------      ---------     ----------
    ('electricity', 'nuclear',    'Gen_II_LWR'),
    ('electricity', 'nuclear',    'GEN_III'),
    ('electricity', 'geothermal', 'geothermal'),
    ('electricity', 'solar',      'PV'),
    ('electricity', 'solar',      'CSP'),
    ('electricity', 'solar',      'PV_storage'),
    ('electricity', 'solar',      'CSP_storage'),
    ('electricity', 'wind',       'wind'),
    ('electricity', 'wind',       'wind_storage'),
    ('electricity', 'biomass',    'biomass (conv)'),
    ('electricity', 'biomass',    'biomass (conv CCS)'),
    ('electricity', 'biomass',    'biomass (IGCC)'),
    ('electricity', 'biomass',    'biomass (IGCC CCS)'),
    ('elect_td_bld','rooftop_pv', 'rooftop_pv')
]

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

#
# TBD: Write a function to merge XML trees following GCAM's rules
#
def merge_element(parent, new_elt):
    """
    Add an element if none of parent's children has the same tag and attributes
    as element. If a match is found, add element's children to those of the
    matching element.
    """
    for sibling in parent:
        if match_element(new_elt, sibling):
            for child in new_elt:
                merge_element(sibling, child)
            return

    parent.append(new_elt)

def techs_dataframe(tups=electricity_producers):
    return pd.DataFrame(data=tups, columns=['sector', 'subsector', 'technology'])

def query_techs(df, sectors=None, subsectors=None, techs=None):
    subqueries = []

    if sectors:
        subqueries.append("sector in {}".format(sectors))
    if subsectors:
        subqueries.append("subsector in {}".format(subsectors))
    if techs:
        subqueries.append("technology in {}".format(techs))

    if len(subqueries) == 0:
        return None

    query = ' or '.join(subqueries)
    rows = df.query(query)
    return rows

#
# Policy setup
#
def create_policy_region(region, commodity, market, consumer_xml, producer_xml, startYear=2015):
    template = '''    
<region name="{region}">
  <policy-portfolio-standard name="{commodity}">
    <market>{market}</market>
    <policyType>RES</policyType>
    <constraint fillout="1" year="{startYear}">0</constraint>
    <min-price year="{startYear}" fillout="1">-1000</min-price>
  </policy-portfolio-standard>
  {consumer_xml}
  {producer_xml}
</region>'''

    xml = template.format(region=region, commodity=commodity, market=market,
                          consumer_xml=consumer_xml, producer_xml=producer_xml,
                          startYear=startYear)
    return xml

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
    return xml

# TBD: it won't always be the global tech DB, i.e., stub-technology we want to affect
def create_demand_tech(tech, period_xml):
    template = '''
<stub-technology name="{technology}">
  {period_xml}
</subsector>'''

    xml = template.format(technology=tech, period_xml=period_xml)
    return xml

def create_demand_subsector(subsector, tech_xml):
    template = '''
<subsector name="{subsector}">
  {tech_xml}
</subsector>'''

    xml = template.format(subsector=subsector, tech_xml=tech_xml)
    return xml

def create_demand_sector(sector, subsector_xml):
    template = '''  
<supplysector name="{sector}">
  {subsector_xml}
</supplysector>'''

    xml = template.format(sector=sector, subsector_xml=subsector_xml)
    return xml

# def create_ownuse_demand_sector(periods):
#     name = 'electricity_net_ownuse'
#     xml = create_demand_sector(name, name, name, periods)
#     return xml
#
# def create_rooftop_PV_demand_sector(periods):
#     xml = create_demand_sector('elect_td_bld', 'rooftop_pv', 'rooftop_pv', periods)
#     return xml

#
# REC supply
#

def create_supply_period(year, commodity, outputRatio=1, pMultiplier=1):
    template = '''
<period year="{year}">
  <res-secondary-output name="{commodity}">
    <output-ratio>{outputRatio}</output-ratio>
    <pMultiplier>{pMultiplier}</pMultiplier>
  </res-secondary-output>
</period>'''

    xml = template.format(year=year, commodity=commodity,
                          outputRatio=outputRatio, pMultiplier=pMultiplier)
    return xml

def create_supply_tech(tech, period_xml):
    template = '''
<technology name="{technology}">
  {period_xml}
</technology>'''

    xml = template.format(technology=tech, period_xml=period_xml)
    return xml

def create_supply_subsector(subsector, tech_xml):
    template = '''
<subsector name="{subsector}">
  {tech_xml}
</subsector>'''

    xml = template.format(subsector=subsector, tech_xml=tech_xml)
    return xml

def create_supply_sector(sector, subsector_xml):
    template = '''
<supplysector name="{sector}">
  {subsector_xml}
</supplysector>'''

    xml = template.format(sector=sector, subsector_xml=subsector_xml)
    return xml

def create_supply_sectors(df, commodity, years, sectors=None, subsectors=None, techs=None,
                         outputRatio=1, pMultiplier=1):
    rows = query_techs(df, sectors=sectors, subsectors=subsectors, techs=techs)

    sect_list = []
    for sector in rows.sector.unique():
        sub_rows = query_techs(df, sectors=[sector])
        sub_list = []
        for subsector in sub_rows.subsector.unique():
            tech_rows = query_techs(df, sectors=[sector], subsectors=[subsector])
            tech_list = []
            for tech in tech_rows.technology.unique():
                period_list = []
                for year in years:
                    period = create_supply_period(year, commodity,
                                                  outputRatio=outputRatio,
                                                  pMultiplier=pMultiplier)
                    period_list.append(period)

                periods_xml = cat(period_list)
                tech_list.append(create_supply_tech(tech, periods_xml))

            tech_xml = cat(tech_list)
            sub_list.append(create_supply_subsector(subsector, tech_xml))

        sub_xml = cat(sub_list)
        sect_list.append(create_supply_sector(sector, sub_xml))

    xml = cat(sect_list)
    return xml

# Defines the sectors/subsectors/techs that consume RECs
def create_REC_demand(df, market, commodity, targets, coefficient=1):
    period_list = [create_demand_period(year, commodity, coefficient) for year, _ in targets]

    # this makes sense if we attach to techs directly, rather than to net_ownuse. Allows some tech exclusions, too.
    xml_list = [create_demand_sector(row.sector, row.subsector, row.technology, period_list) for idx, row in df.iterrows()]
    xml = cat(xml_list)
    return xml

# Defines the sectors/subsectors/techs that produce RECs
def create_REC_supply(df, market, commodity, targets, outputRatio=1, pMultiplier=1):
    period_list = [create_supply_period(year, commodity, coefficient) for year, fraction in targets]

    create_supply_period(year, commodity, outputRatio=1, pMultiplier=1)

    xml_list = [create_supply_sector(row.sector, row.subsector, row.technology, period_list) for idx, row in df.iterrows()]
    xml = cat(xml_list)
    return xml

def create_RES(regions, commodity, market, targets, startYear=2015,
               sectors=None, subsectors=None, techs=None,
               outputRatio=1, pMultiplier=1, filename=None):

    template = '''
<scenario>
  <world>
    {region_xml}
  </world>
</scenario>
'''
    # TBD: maybe start with ownuse version and work up to each tech individually
    consumer_tups = [
        ('electricty_net_ownuse', 'electricty_net_ownuse', 'electricty_net_ownuse'),
        ('elect_td_bld',          'rooftop_pv',            'rooftop_pv')
    ]

    consumer_df = techs_dataframe(tups=consumer_tups)
    consumer_xml = create_REC_demand(consumer_df, market, commodity, targets,
                                     outputRatio=outputRatio, pMultiplier=pMultiplier)

    tech_df = techs_dataframe() # TBD: pass in df with constrained sectors/subsects/techs
    producer_df = query_techs(tech_df, sectors=sectors, subsectors=subsectors, techs=techs)
    producer_xml = create_REC_supply(producer_df, market, commodity, targets)

    regionList = [create_policy_region(region, commodity, market,
                                       consumer_xml, producer_xml,
                                       startYear=startYear) for region in regions]

    xml = prettify(template.format(region_xml=cat(regionList)))

    if filename:
        with open(filename, "w") as f:
            f.write(xml)

    return xml


def print_xml(element):
    print(ET.tostring(element, pretty_print=True).decode('UTF-8'))

if __name__ == '__main__':
    # scenario = ET.Element("scenario")
    # world = ET.SubElement(scenario, "world")
    # region = ET.SubElement(world, "region", name="USA")
    # print_xml(scenario)

    regions    = ('USA', 'Canada')
    market     = 'NorthAmerica'
    commodity  = 'REC'
    targets    = ((2020, 0.15), (2025, 0.20), (2030, 0.25))
    subsectors = ('solar', 'rooftop_pv')

    df = techs_dataframe()
    years = [pair[0] for pair in targets]
    xml = create_supply_sectors(df, commodity, years, subsectors=subsectors)
    print(xml)

    xml = create_RES(regions, commodity, market, targets, subsectors=subsectors)
    print(xml)

