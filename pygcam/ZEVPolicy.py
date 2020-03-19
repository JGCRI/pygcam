#
# Goal is eventually to translate a file like ../etc/exampleRES.xml into standard GCAM XML.
#
from copy import deepcopy
import re
from lxml import etree as ET
from lxml.etree import Element, SubElement
from .config import pathjoin, getParam
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

# def ref_pathname(basename):
#     refWorkspace = getParam('GCAM.RefWorkspace')
#     xmlfile = pathjoin(refWorkspace, 'input', 'gcamdata', 'xml', basename)
#     return xmlfile
#
# def ref_xmltree(basename):
#     pathname = ref_pathname(basename)
#     tree = XMLFile(pathname).getTree()
#     return tree
#
# def read_state_names():
#     global States
#
#     xmlfile = pathjoin(getParam('GCAM.RefWorkspace'), 'input', 'gcamdata', 'xml', 'socioeconomics_USA.xml')
#     tree = XMLFile(xmlfile).getTree()
#     States = tree.xpath('//region/@name')
#
def is_abspath(pathname):
    """Return True if pathname is an absolute pathname, else False."""
    import re
    return bool(re.match(r"^([/\\])|([a-zA-Z]:)", pathname))

def get_path(pathname, defaultDir):
    """Return pathname if it's an absolute pathname, otherwise return
       the path composed of pathname relative to the given defaultDir"""
    return pathname if is_abspath(pathname) else pathjoin(defaultDir, pathname)
#
# def read_csv(pathname):
#     import pandas as pd
#
#     _logger.debug("Reading '%s'", pathname)
#
#     df = pd.read_csv(pathname, index_col='region', skiprows=1)
#     return df

# def validate(scenario, csv_path, useGcamUSA):
#     import pandas as pd
#     param_df = read_csv(csv_path)
#
#     year_cols = [col for col in param_df.columns if str.isdigit(col)]
#     tech_cols = [col for col in param_df.columns if not str.isdigit(col) and col != 'market']
#
#     sandboxDir  = getParam('GCAM.SandboxDir')
#
#     query_name  = 'ElecGenBySubsectorNoRECs'
#     if useGcamUSA:
#         query_name += 'ByState'
#
#     result_csv = pathjoin(sandboxDir, scenario, 'queryResults', '{}-{}.csv'.format(query_name, scenario))
#
#     print("Reading", result_csv)
#     result_df = pd.read_csv(result_csv, skiprows=1)
#     result_df.reset_index(inplace=True)
#
#     keep = ['region', 'output', 'subsector'] + year_cols
#     df2 = result_df[keep]
#     regions = list(param_df.index)
#     df3 = df2.query('region in @regions and output in ("electricity", "elect_td_bld")')
#
#     elec_total = {}
#     rec_total = {}
#     fraction = {}
#
#     for region in regions:
#         elec = df3.query('region == @region')
#         elec_total[region] = elec[year_cols].sum()
#
#         re_techs = get_re_techs(tech_cols, param_df, region)  # N.B. interpolated in query below
#         recs = elec.query('subsector in @re_techs')
#         rec_total[region] = recs[year_cols].sum()
#
#         fraction[region] = rec_total[region] / elec_total[region]
#
#     result = None
#     for region in regions:
#         df = pd.DataFrame(round(fraction[region] * 100, 2)).T
#         df['region'] = region
#         result = df if result is None else result.append(df)
#
#     result.set_index('region', inplace=True)
#     print('{}:\n{}'.format(scenario, result))

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

def validate_years(years):
    pair = years.split('-')
    if len(pair) != 2:
        return None

    (first, last) = pair
    if not (first.isdigit() and last.isdigit()):
        return None

    first = int(first)
    last  = int(last)

    if not (first < last):
        return None

    return [i for i in range(first, last+1, 5)]

def zevPolicyMain(args):
    import os
    import pandas as pd
    from .error import CommandlineError
    # from .utils import mkdirs

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

    # TBD: make this more flexible, e.g., based on tag rather than filename
    gcamDir = getParam('GCAM.RefWorkspace')
    pathname = os.path.join(gcamDir, 'input', 'gcamdata', 'xml', 'transportation_UCD_CORE.xml')
    _logger.info("Reading {}".format(pathname))

    xml = XMLFile(pathname)
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


