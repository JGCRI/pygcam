from lxml import etree as ET
from .config import pathjoin, getParam
from .log import getLogger
from .XMLFile import XMLFile

_logger = getLogger(__name__)

def element_path(elt):
    d = {'technology' : elt.attrib['name']}

    for node in elt.iterancestors():    # walk up the hierarchy
        tag = node.tag
        attr = node.attrib

        if tag == 'region':
            d['region'] = attr['name' ]
            break

        # elif tag == 'location-info':
        #     d['sector'] = attr['sector-name']
        #     d['subsector'] = attr['subsector-name']

        elif tag == 'supplysector':
            d['sector'] = attr['name']

        elif tag == 'tranSubsector':
            d['subsector'] = attr['name']

    return (d['region'], d['sector'], d['subsector'], d['technology'])


def zevPolicyMain(args):
    import pandas as pd
    from .error import CommandlineError
    from .xmlSetup import scenarioXML
    from .utils import validate_years, get_path

    years = validate_years(args.years)
    if years is None:
        raise CommandlineError(
            'Year argument must be two integers separated by a hyphen, with second > first. Got "{}"'.format(
                args.years))

    outputCSV  = args.outputCSV
    useGcamUSA = args.GCAM_USA

    outPath = get_path(outputCSV, pathjoin(getParam("GCAM.ProjectDir"), "etc"))

    # parse sect:subsect:tech args
    tuples = []
    for arg in args.include:
        # adding 2 colons ensures that split() returns at least 3 substrings
        (sectors, subsects, techs) = (arg + "::").split(':')[0:3]
        tuples.append((sectors.split(','), subsects.split(','), techs.split(',')))

    def match_expr(names):
        expr = " or ".join(['@name = "{}"'.format(name) for name in names if name])
        return ('[' + expr +']') if expr else ''

    xpaths =[]
    for (sectors, subsects, techs)  in tuples:
        sector_match  = match_expr(sectors)
        subsect_match = match_expr(subsects)
        tech_match    = match_expr(techs)
        xpath = '/supplysector{}/tranSubsector{}/stub-technology{}'.format(sector_match, subsect_match, tech_match)
        xpaths.append(xpath)

    transportXML = scenarioXML(args.scenario, args.tag) # read the file associated with the given tag
    xml = XMLFile(transportXML)
    root = xml.getRoot()

    if args.regions:
        regions = args.regions.split(',')
        comps = ['@name="{}"'.format(r) for r in regions]
        regionPrefix = '//region[{}]'.format(' or '.join(comps))
    else:
        regionPrefix = '//region'

    techs = []
    combos = dict()
    for xpath in xpaths:
        full_xpath = regionPrefix + xpath

        nodes = root.xpath(full_xpath)
        techs += [node.attrib['name'] for node in nodes]

        combos.update({element_path(node) : True for node in nodes})

    unique_techs = sorted(set(techs))
    print("techs:", unique_techs)

    # create list of tuples without techs
    active_subsects = [list(tup) for tup in sorted(set([key[0:3] for key in combos.keys()]))]

    year_cols = [str(year) for year in years]

    # generate CSV template
    columns = ['region', 'market', 'supplysector', 'tranSubsector'] + unique_techs + year_cols
    df = pd.DataFrame(columns=columns, index=range(0, len(active_subsects)))

    df[year_cols] = 0

    # convert row tuples to columns to update the df
    all_regs, all_sects, all_subsects = zip(*active_subsects)
    df['market'] = all_regs     # default market is same as region name
    df['region'] = all_regs
    df['supplysector'] = all_sects
    df['tranSubsector'] = all_subsects

    for idx, row in df.iterrows():
        for tech in unique_techs:
            key = (row.region, row.supplysector, row.tranSubsector, tech)
            if combos.get(key, False):
               df.loc[idx, tech] = 1

    _logger.info("Writing '%s'", outPath)
    df.to_csv(outPath, index=None)


BtuToMJ = 1.055

def generate_zev_xml(scenario, csvPath, xmlPath, transportTag, pMultiplier, outputRatio):
    import os
    import pandas as pd
    from .utils import mkdirs
    from .RESPolicy import write_xml
    from .xmlSetup import scenarioXML

    df = pd.read_csv(csvPath, index_col=None)

    common_cols = ['region', 'market', 'supplysector', 'tranSubsector']
    year_cols = [col for col in df.columns if col.isdigit()]
    tech_cols = list(set(df.columns) - set(common_cols + year_cols))

    def set_text(elt, value):
        elt.text = str(value)
        return elt

    def rec_name(region, subsector, year, policy='ZEC'):
        name = '{} {} {} {}'.format(region, subsector, policy, year)
        return name

    # we use the indicated transportation XML file to extract load factors
    transportXML = scenarioXML(scenario, transportTag) # read the file associated with the given tag
    xml = XMLFile(transportXML)
    trans_root = xml.getRoot()

    def load_factor(region, sector, subsector, tech, year):
        xpath = "//region[@name='{}']/supplysector[@name='{}']/tranSubsector[@name='{}']/stub-technology[@name='{}']/period[@year='{}']/loadFactor".format(
            region, sector, subsector, tech, year)
        nodes = trans_root.xpath(xpath)
        if len(nodes) == 0:
            raise Exception('ZEVPolicy: Failed to find loadFactor for "{}"'.format(xpath))

        return float(nodes[0].text)

    def find_or_create(parent, tag, name):
        elt = parent.find('{}[@name="{}"]'.format(tag, name))
        if elt is None:
            elt = ET.SubElement(parent, tag, name=name)

        return elt

    root = ET.Element('scenario')
    world = ET.SubElement(root, 'world')

    # If the standard is zero in some years, emit no policy-portfolio-standard, no
    # coefficients, and no secondary-res-outputs for that year.

    for region in sorted(df.region.unique()):
        region_df = df.query('region == @region')

        region_elt = find_or_create(world, 'region', region)

        for idx, row in region_df.iterrows():
            sector    = row.supplysector
            subsector = row.tranSubsector
            market    = row.market

            # <policy-portfolio-standard name="{region} {tranSubsector} ZEC {year}">
            #   <market>{market}</market>
            #   <policyType>RES</policyType>
            #   <constraint year="{year}">1</constraint>
            # </policy-portfolio-standard>
            for year in year_cols:
                target = region_df.loc[idx, year]
                if target:
                    name = rec_name(market, subsector, year)
                    std_elt = ET.SubElement(region_elt, 'policy-portfolio-standard', name=name)
                    set_text(ET.SubElement(std_elt, 'market'), market)
                    set_text(ET.SubElement(std_elt, 'policyType'), 'RES')
                    set_text(ET.SubElement(std_elt, 'constraint', year=year), 1)

            sect_elt  = None  # created on demand in loop below

            # <supplysector name="trn_freight_road">
            #   <tranSubsector name="Truck (>32t)">
            #     <stub-technology name="electric">
            #       <period year="2030">
            #         <minicam-energy-input name="EU15 Truck (>32t) ZEC 2030">
            #           <coefficient>1544.0758</coefficient>
            #         </minicam-energy-input>
            #         <res-secondary-output name="EU15 Truck (>32t) ZEC 2030">
            #           <output-ratio>0.000001</output-ratio>
            #           <pMultiplier>1.25E10</pMultiplier>
            #         </res-secondary-output>
            #       </period>
            for tech in tech_cols:
                for year in year_cols:
                    target = region_df.loc[idx, year]
                    if not target:
                        continue

                    sect_elt = sect_elt if sect_elt is not None else find_or_create(region_elt, 'supplysector', sector)
                    subsect_elt = find_or_create(sect_elt, 'tranSubsector', subsector)

                    tech_elt = find_or_create(subsect_elt, 'stub-technology', tech)
                    period_elt = ET.SubElement(tech_elt, 'period', year=year)
                    name = rec_name(market, subsector, year)

                    en_input_elt = ET.SubElement(period_elt, 'minicam-energy-input', name=name)

                    value = target / BtuToMJ * 1E3 * load_factor(region, sector, subsector, tech, year)
                    set_text(ET.SubElement(en_input_elt, 'coefficient'), value)

                    # create res-secondary-output elements only for technologies included in the policy
                    if region_df.loc[idx, tech]:
                        sec_input_elt = ET.SubElement(period_elt, 'res-secondary-output', name=name)
                        set_text(ET.SubElement(sec_input_elt, 'output-ratio'), outputRatio)
                        set_text(ET.SubElement(sec_input_elt, 'pMultiplier'), pMultiplier)

    # delete empty regions
    emptyRegs = [reg for reg in world if len(reg) == 0]
    for reg in emptyRegs:
        world.remove(reg)

    _logger.info("Writing '%s'", xmlPath)
    mkdirs(os.path.dirname(xmlPath))    # ensure the location exists
    tree = ET.ElementTree(root)
    write_xml(tree, xmlPath)
