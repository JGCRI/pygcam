#
# Goal is eventually to translate a file like ../etc/exampleRES.xml into standard GCAM XML.
#
from copy import deepcopy
import re
from lxml import etree as ET
from lxml.etree import Element, SubElement
from .config import pathjoin, getParam, mkdirs
from .constants import QRESULTS_DIRNAME
from .log import getLogger
from .XMLFile import XMLFile

_logger = getLogger(__name__)

# We deal only with one historical year (2010) and all future years
TIMESTEP = 5
LAST_HISTORICAL_YEAR = 2010
FIRST_MODELED_YEAR = LAST_HISTORICAL_YEAR + TIMESTEP
END_YEAR = 2100
GCAM_YEARS = [1975, 1990, 2005] + [year for year in range(LAST_HISTORICAL_YEAR, END_YEAR + 1, TIMESTEP)]

States = []

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
    Add each element in elt_list to parent if none of parent's children has the same tag
    and attributes as element. If a match is found, merge element's children with those
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

def create_tech(tech, period_list): #, stub=False):
    # tag = 'stub-technology' if stub else 'technology'
    tag = 'stub-technology'
    return create_elt(tag, tech, period_list)

def create_subsector(subsector, tech_list):
    return create_elt('subsector', subsector, tech_list)


def create_sector(sector, subsector_list, sectorTag):
    return create_elt(sectorTag, sector, subsector_list)

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

def sector_tag(sector, elecPassThru):
    tag = 'pass-through-sector' if elecPassThru and sector == 'electricity' else 'supplysector'
    return tag


def create_supply_sectors(df, commodity, targets, elecPassThru,
                          outputRatio=1, pMultiplier=1):
    sector_list = []

    for sector in df.sector.unique():
        sectorTag = sector_tag(sector, elecPassThru)
        sub_df = df[df.sector == sector]

        sub_list = []
        for subsector in sub_df.subsector.unique():
            tech_df = sub_df[sub_df.subsector == subsector]
            tech_list = []
            for tech in tech_df.technology.unique():
                period_list = []
                for year, coefficient in targets:
                    period = create_supply_period(year, commodity, outputRatio, pMultiplier)
                    period_list.append(period)

                tech_list.append(create_tech(tech, period_list))

            sub_list.append(create_subsector(subsector, tech_list))

        sector_list.append(create_sector(sector, sub_list, sectorTag))

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

def create_demand_sectors(df, commodity, targets, elecPassThru, priceUnitConv=0):
    sector_list = []

    coef_xml_dict = create_adjusted_coefficients(targets)

    for sector in df.sector.unique():
        sectorTag = sector_tag(sector, elecPassThru)
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

        sector_list.append(create_sector(sector, sub_list, sectorTag))

    return sector_list

def firstTarget(targets):
    """
    Return the first (year, coefficient) tuple in targets with coefficient != 0.
    """
    targets.sort(key=lambda tup: tup[0])    # sort by year

    for year, coefficient in targets:
        if coefficient: # ignore zeros
            return (year, coefficient)

def create_RES(tech_df, regions, market, commodity, targets, subsector_dict,
               outputRatio=1, pMultiplier=1, priceUnitConv=0, minPrice=None):

    #print("{}:\n{}".format(regions, tech_df[['technology', 'consumer', 'producer']]))

    startYear, startTarget = firstTarget(targets)

    # Create "targets" with initial policy target in years prior to start year
    # since older plants will retain this as their definition (until GCAM is patched)
    prepolicy = [(year, startTarget) for year in GCAM_YEARS if year < startYear]

    # avoid duplicating years by starting targets at "startYear"
    targets = prepolicy + [t for t in targets if t[0] >= startYear]

    # N.B. We assume that a RES is applied either to a subset of states, or of regions,
    # but never to both states and non-US regions in the same market. For states, the
    # electricity sector tag is 'pass-through-sector' rather than 'supplysector'.
    elecPassThru = (regions[0] in States)

    consumer_df = tech_df.query('consumer == 1')
    consumer_elts = create_demand_sectors(consumer_df, commodity, targets, elecPassThru,
                                          priceUnitConv=priceUnitConv)

    producer_df = tech_df.query('producer == 1')
    producer_elts = create_supply_sectors(producer_df, commodity, targets, elecPassThru,
                                          outputRatio=outputRatio, pMultiplier=pMultiplier)

    region_list = [create_policy_region(region, commodity, market,
                                        deepcopy(consumer_elts), deepcopy(producer_elts),
                                        startYear=startYear, minPrice=minPrice) for region in regions]

    supply_sector_tag = 'pass-through-sector' if elecPassThru else 'supplysector'
    subsect_xpath = '/region/{}/subsector'.format(supply_sector_tag)

    # Excise non-existent subsectors (e.g., geothermal) in each region
    for region_elt in region_list:
        region = region_elt.attrib['name']
        subsects = subsector_dict[region]

        to_remove = []
        for subsect_elt in region_elt.xpath(subsect_xpath):
            subsect_name = subsect_elt.attrib['name']
            if not subsects.get(subsect_name, False):
                to_remove.append(subsect_elt)

        # Skip non-existent subsectors (e.g., geothermal), with a warning. Remove them
        # after iterating over subsectors.
        if to_remove:
            sector_elt = region_elt.find(supply_sector_tag)
            for elt in to_remove:
                sector_elt.remove(elt)
                _logger.warn("Ignoring non-existent subsector '%s' in region '%s'",
                             elt.attrib['name'], region)


    scenario = Element('scenario')
    world = SubElement(scenario, 'world')
    merge_elements(world, region_list)

    return scenario

def match_str_or_regex(strings, name):
    if not name:
        return strings

    if name in strings:
        return [name]

    pattern = re.compile(name)
    matches = [s for s in strings if pattern.match(s)]
    return matches

def find_techs(tree, tups):
    """
    Return a list of (sector, subsector, technology) triads that occur in any of the
    indicated sectors and/or subsectors indicated in`pairs`. Each tuple in the list
    `pairs` must be also be the form (sector, subsector, technology), but in this case,
    each of these three element can be a string to match exactly items in the Global
    Technology Database with the same value for this attribute, or a regular expression.
    The value can also be `None` to match all values in the tech database for the given
    attributes. Thus, you can indicate all technologies in all subsectors of the 'electricity'
    sector as `('electricity', None, None)`, (or, equivalently, as `('electricity',)`), or
    all technologies whose name starts with "elec_" using a regex: `("^elec_.*",)`

    :param tree: (etree.ElementTree) in-memory representation of XML file
    :param tups: Tuples or lists of 1, 2, or 3 elements. If the tuple contains 1 element,
       is considered the sector, and the other elements are set to `None`. A 2-element
       tuple specifies sectors and subsectors, with technology set to `None`

    :return: (pandas.DataFrame) with three columns: sector, subsector, and technology,
      populated based on the given `tups`.
    """
    import re

    gtdb = tree.find('//global-technology-database')

    all_sectors = set(gtdb.xpath('./location-info/@sector-name'))
    tech_triads = []

    for tup in tups:
        tup = tup + (None, None, None)        # ensure length >= 3,
        sector, subsector, technology = tup[0:3]    # use first 3 elements

        sects = match_str_or_regex(all_sectors, sector)
        if not sects:
            _logger.warn("Sector name '{}' failed to match anything.".format(sector))
            continue

        for sect in sects:
            all_subsects = set(gtdb.xpath('./location-info[@sector-name="{}"]/@subsector-name'.format(sect)))

            subsects = match_str_or_regex(all_subsects, subsector)
            if not subsects:
                _logger.warn("In sector {}, subsector name '{}' failed to match anything.".format(sect, subsector))
                continue

            for subsect in subsects:
                locations = gtdb.xpath('./location-info[@sector-name="{}" and @subsector-name="{}"]'.format(sect, subsect))
                for location in locations:
                    # missing techs (with names above) => pass-through, so we ignore empty returns
                    all_techs = location.xpath('./technology/@name') + location.xpath('./intermittent-technology/@name')

                    matching_techs = match_str_or_regex(all_techs, technology)
                    for tech in matching_techs:
                        tech_triads += [(sect, subsect, tech)]

    return tech_triads

# TBD: move this to a library of functions that process GCAM XML

def get_tech_df(tree, tech_specs):
    import pandas as pd

    tech_triads = find_techs(tree, tech_specs)

    tech_df = pd.DataFrame(data=tech_triads, columns=['sector', 'subsector', 'technology'])
    return tech_df

def ref_pathname(basename):
    refWorkspace = getParam('GCAM.RefWorkspace')
    xmlfile = pathjoin(refWorkspace, 'input', 'gcamdata', 'xml', basename)
    return xmlfile

def ref_xmltree(basename):
    pathname = ref_pathname(basename)
    tree = XMLFile(pathname).getTree()
    return tree

def get_electricity_tech_df(useGcamUSA):
    tech_specs = [('electricity', None, None),
                  ('elect_td_bld', 'rooftop_pv', 'rooftop_pv')]

    if useGcamUSA:
        basename = 'electricity.xml'
    else:
        basename = 'electricity_water.xml'
        tech_specs.append(('^elec_.*', None, None))

    tree = ref_xmltree(basename)

    tech_df = get_tech_df(tree, tech_specs)
    tech_df['producer'] = 0
    tech_df['consumer'] = 0

    return tech_df

def read_state_names():
    global States

    xmlfile = pathjoin(getParam('GCAM.RefWorkspace'), 'input', 'gcamdata', 'xml', 'socioeconomics_USA.xml') # TBD: ref_pathname('socioeconomics_USA.xml')
    tree = XMLFile(xmlfile).getTree()
    States = tree.xpath('//region/@name')

def set_actor(tech_df, tech_tups, actor, value=1):
    """
    Actor must be 'producer' or 'consumer'
    """
    tech_df[actor] = 0  # reset producer or consumer col, since we reuse the DF

    for tup in tech_tups:
        tup = tup + (None, None, None)      # ensure that we have at least 3 items
        sector, subsector, tech = tup[0:3]

        mask = (tech_df.sector == sector)
        if not any(mask):
            mask = tech_df.sector.str.contains(sector)

        if subsector:
            subsects = (tech_df.subsector == subsector)
            if not any(subsects):
                subsects = tech_df.subsector.str.contains(subsector)

            mask &= subsects

        if tech:
            techs = (tech_df.technology == tech)
            if not any(techs):
                techs = tech_df.technology.str.contains(tech)

            mask &= techs

        tech_df.loc[mask, actor] = value


class RECertificate(object):
    def __init__(self, node):
        self.elt = node
        self.name = node.get('name')
        self.targets   = self.parseTargets()
        self.producers = self.parseTechs('producers')
        self.consumers = self.parseTechs('consumers')

    def parseTargets(self):
        from .xmlEditor import expandYearRanges

        targetsNode = self.elt.find('targets')
        targetTups = [(t.get('years'), t.get('fraction')) for t in targetsNode.findall('target')]
        expanded = expandYearRanges(targetTups)
        return expanded

    def parseTechs(self, groupName):
        groupNode = self.elt.find(groupName)
        techs = groupNode.findall('tech')
        techTups = [(t.get('sector'), t.get('subsector'), t.get('technology')) for t in techs]
        return techTups

class PortfolioStandard(object):
    def __init__(self, elt):
        self.elt = elt
        self.market = elt.get('market')
        self.regions = [s.strip() for s in elt.get('regions').split(',')]
        self.certs = self.parseRES()

    def parseRES(self):
        certs = [RECertificate(cert) for cert in self.elt.findall('certificate')]
        return certs

class RESPolicy(XMLFile):
    def __init__(self, filename, useGcamUSA):
        super(RESPolicy, self).__init__(filename, load=True, schemaPath='etc/RES-schema.xsd')

        self.root = root = self.tree.getroot()
        self.standards = [PortfolioStandard(elt) for elt in root.findall('portfolio-standard')]

target_template = '''        <target years="{year}" fraction="{fraction}"/>'''

rooftop_pv        = '''        <tech sector="elect_td_bld" subsector="rooftop_pv"/>'''

cert_template = '''    <certificate name="{market}-REC">
      <targets>
{targets}
      </targets>
      <producers>
{producers}
      </producers>
      <consumers>
{consumers}
      </consumers>
    </certificate>
'''

tech_map = None

def set_tech_map(useGcamUSA):
    global tech_map

    if useGcamUSA:
        tech_map = {
            'solar'       : ['''        <tech sector="electricity" subsector="solar"/>'''],
            'CSP'         : ['''        <tech sector="electricity" subsector="solar"/>'''],
            'wind'        : ['''        <tech sector="electricity" subsector="wind"/>'''],
            'wind_storage': ['''        <tech sector="electricity" subsector="wind"/>'''],
            'hydro'       : ['''        <tech sector="electricity" subsector="hydro"/>'''],
            'biomass'     : ['''        <tech sector="electricity" subsector="biomass"/>'''],
            'nuclear'     : ['''        <tech sector="electricity" subsector="nuclear"/>'''],
            'geothermal'  : ['''        <tech sector="electricity" subsector="geothermal"/>''']
        }
    else:
        tech_map = {
            'solar'      : ['''        <tech sector="electricity" subsector="solar"/>''',
                            '''        <tech sector="elec_CSP"/>'''],
            'wind'       : ['''        <tech sector="electricity" subsector="wind"/>'''],
            'hydro'      : ['''        <tech sector="electricity" subsector="hydro"/>'''],
            'biomass'    : ['''        <tech sector="elec_biomass"/>'''],
            'CSP'        : ['''        <tech sector="elec_CSP"/>'''],
            'nuclear'    : ['''        <tech sector="electricity" subsector="nuclear"/>'''],
            'geothermal' : ['''        <tech sector="elec_geothermal"/>''']
        }

    tech_map['rooftop_pv'] = [rooftop_pv]

def get_producers(row, tech_cols):
    producers = []

    for tech in tech_cols:
        if row[tech]:
            producers += tech_map[tech]

    return '\n'.join(producers)

def read_csv(pathname):
    import pandas as pd

    _logger.debug("Reading '%s'", pathname)

    df = pd.read_csv(pathname, index_col='region', skiprows=1)
    return df

def res_from_csv(csv_path, useGcamUSA):
    from .temp_file import getTempFile
    from .error import FileFormatError

    xml_path = getTempFile(suffix='.xml', delete=True)

    df = read_csv(csv_path)
    year_cols = [col for col in df.columns if str.isdigit(col)]
    tech_cols = [col for col in df.columns if not str.isdigit(col) and col != 'market']

    for tech in tech_cols:
        if not tech in tech_map:
            raise FileFormatError("Unrecognized technology name: {}".format(tech))

    # TBD: this supports state policies but not together with non-USA regional policies
    if useGcamUSA:
        all_elec = ['''        <tech sector="electricity"/>''']
    else:
        all_elec = ['''        <tech sector="electricity" subsector="solar|wind|hydro"/>''',
                    '''        <tech sector="^elec_.*"/>''']

    _logger.info("Writing '%s'", xml_path)
    with open(xml_path, 'w') as f:
        f.write('''<portfolio-standards xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="RES-schema.xsd">\n''')

        for (region, row) in df.iterrows():
            f.write('''  <portfolio-standard market="{market}" regions="{region}">\n'''.format(market=row.market, region=region))

            targets = '\n'.join([target_template.format(year=year, fraction=row[year]) for year in year_cols])

            producers = get_producers(row, tech_cols)

            consumer_list = all_elec + ([rooftop_pv] if row.rooftop_pv else [])
            consumers = '\n'.join(consumer_list)

            cert = cert_template.format(market=row.market, targets=targets, producers=producers, consumers=consumers)
            f.write(cert)

            f.write('''  </portfolio-standard>\n''')

        f.write("</portfolio-standards>\n")

    return RESPolicy(xml_path, useGcamUSA)

def get_re_techs(tech_cols, params, region):
    return [tech for tech in tech_cols if params.loc[region, tech] == 1]

def validate(scenario, csv_path, useGcamUSA):
    import pandas as pd
    param_df = read_csv(csv_path)

    year_cols = [col for col in param_df.columns if str.isdigit(col)]
    tech_cols = [col for col in param_df.columns if not str.isdigit(col) and col != 'market']

    sandboxDir  = getParam('GCAM.SandboxDir')

    query_name  = 'ElecGenBySubsectorNoRECs'
    if useGcamUSA:
        query_name += 'ByState'

    result_csv = pathjoin(sandboxDir, scenario, QRESULTS_DIRNAME, f'{query_name}-{scenario}.csv')

    print("Reading", result_csv)
    result_df = pd.read_csv(result_csv, skiprows=1)
    result_df.reset_index(inplace=True)

    keep = ['region', 'output', 'subsector'] + year_cols
    df2 = result_df[keep]
    regions = list(param_df.index)
    df3 = df2.query('region in @regions and output in ("electricity", "elect_td_bld")')

    elec_total = {}
    rec_total = {}
    fraction = {}

    for region in regions:
        elec = df3.query('region == @region')
        elec_total[region] = elec[year_cols].sum()

        re_techs = get_re_techs(tech_cols, param_df, region)  # N.B. interpolated in query below
        recs = elec.query('subsector in @re_techs')
        rec_total[region] = recs[year_cols].sum()

        fraction[region] = rec_total[region] / elec_total[region]

    result = None
    for region in regions:
        df = pd.DataFrame(round(fraction[region] * 100, 2)).T
        df['region'] = region
        result = df if result is None else result.append(df)

    result.set_index('region', inplace=True)
    print('{}:\n{}'.format(scenario, result))

# Create a dict of regionally-available subsectors like this:
#
# {"CA" : {("electricity", "coal") : 0,	# we just use the hash index lookup, value doesn't matter
#          ("electricity", "solar") : 0,
#          ...,
#          ("elect_td_bld", "rooftop_pv")},
#  ...
# }
def create_subsector_dict(useGcamUSA):
    from _collections import defaultdict

    tree = ref_xmltree('electricity_water.xml')
    xpath = '//region/supplysector[@name="electricity" or @name="elect_td_bld"]/subsector'
    elts = tree.xpath(xpath)

    if useGcamUSA:
        tree = ref_xmltree('electricity_USA.xml')

        xpath1 = '//region/pass-through-sector[@name="electricity"]/subsector'
        xpath2 = '//region/supplysector[@name="elect_td_bld"]/subsector'

        elts += tree.xpath(xpath1) + tree.xpath(xpath2)

    by_region = defaultdict(dict)
    for elt in elts:
        parent = elt.getparent()
        grandparent = parent.getparent()

        region = grandparent.attrib['name']

        # Skip 'USA' if we're including all the states
        if useGcamUSA and region == 'USA':
            continue

        # sector = parent.attrib['name']
        subsector = elt.attrib['name']
        # key = (sector, subsector)
        reg_dict = by_region[region]
        reg_dict[subsector] = True     # we're using dict just for hash lookup, so we don't care about dict values

    return by_region

def resPolicyMain(args):
    import os
    from .error import CommandlineError
    from .file_utils import is_abspath, get_path
    from .constants import LOCAL_XML_NAME

    scenario   = args.scenario
    inputFile  = args.inputFile or getParam("GCAM.RESDescriptionFile")           # document these
    outputXML  = args.outputXML or getParam("GCAM.RESImplementationXmlFile")
    useGcamUSA = args.GCAM_USA

    if not scenario and not (outputXML and is_abspath(outputXML)):
        raise CommandlineError(f"outputXML ({outputXML}) is not an absolute pathname; a scenario must be specified")

    inPath   = get_path(inputFile, getParam("GCAM.ProjectEtc"))

    # TBD: get this path using Sandbox class to allow for group subdirs
    outPath  = get_path(outputXML, pathjoin(getParam("GCAM.SandboxWorkspace"), LOCAL_XML_NAME, scenario))

    isCSV = (re.match('.*\.csv$', inPath, re.IGNORECASE) is not None)

    set_tech_map(useGcamUSA)

    if useGcamUSA:
        read_state_names()

    if args.display:
        if not isCSV:
            raise CommandlineError(f"When using -d/--display, the input file must be in CSV format: '{inPath}'.")

        validate(scenario, inPath, useGcamUSA)
        return  # exit

    subsector_dict = create_subsector_dict(useGcamUSA)

    _logger.info("Reading '%s'", inPath)
    resPolicy = res_from_csv(inPath, useGcamUSA) if isCSV else RESPolicy(inPath, useGcamUSA)

    # By default, all electricity techs consume RE certificates
    tech_df = get_electricity_tech_df(useGcamUSA)

    root = None

    for std in resPolicy.standards:
        if useGcamUSA and 'USA' in std.regions:
            raise CommandlineError("The 'USA' region cannot be assigned a RES policy when using GCAM-USA (via the -u/--GCAM-USA flag)")

        # TBD: this is not a complete solution when working from XML but works for CSV inputs.
        # Filter subsectors by those defined for the first of the regions.
        first_region = std.regions[0]
        subsectors = subsector_dict[first_region]

        for cert in std.certs:
            _logger.debug("  Producers:", cert.producers)
            _logger.debug("  Consumers:", cert.consumers)

            # enable the indicated producers and consumers
            set_actor(tech_df, cert.producers, 'producer')
            set_actor(tech_df, cert.consumers, 'consumer')

            res = create_RES(tech_df, std.regions, std.market, cert.name, cert.targets, subsector_dict)

            if root is None:
                root = res
            else:
                merge_elements(root, res.getchildren())

    tree = ET.ElementTree(root)
    mkdirs(os.path.dirname(outPath))    # ensure the location exists

    _logger.info("Writing '%s'", outPath)
    write_xml(tree, outPath)
