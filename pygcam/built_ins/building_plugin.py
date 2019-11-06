#!/usr/bin/env python
"""
.. "new" sub-command (creates a new project)

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from datetime import datetime

from ..subcommand import SubcommandABC

DFLT_PROJECT = 'gcam_res'
OUTPUT_FILE  = 'building_tech_template.csv'

def get_re_techs(tech_cols, params, region):
    return [tech for tech in tech_cols if params.loc[region, tech] == 1]

def element_path(elt):
    d = {'input' : elt.attrib['name']}

    for node in elt.iterancestors():    # walk up the hierarchy
        tag = node.tag
        attr = node.attrib

        if tag == 'period':
            pass

        elif tag == 'location-info':
            d['sector'] = attr['sector-name']
            d['subsector'] = attr['subsector-name']

        elif tag == 'supplysector':
            d['sector'] = attr['name']

        elif tag in ('stub-technology', 'technology'):
            d['technology'] = attr['name']

        elif tag == 'subsector':
            d['subsector'] = attr['name']

        elif tag in ('global-technology-database', 'region'):
            break

    return (d['sector'], d['subsector'], d['technology'], d['input'])

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

def save_bldg_techs(f, args, years, xml_file, xpath, which):
    from ..config import getParam
    from ..utils import pathjoin
    from ..XMLFile import XMLFile

    gcamDir = getParam('GCAM.RefWorkspace', section=args.project)
    pathname = pathjoin(gcamDir, 'input', 'gcamdata', 'xml', xml_file)

    print("Reading", pathname)
    xml = XMLFile(pathname)
    root = xml.getRoot()

    nodes = root.xpath(xpath)
    paths = sorted(set([element_path(node) for node in nodes])) # use 'set' to remove dupes

    # filter out sectors missing from cmdline arg, if specified
    if args.sectors:
        desired = []
        sectors = set(args.sectors.split(','))
        for path in paths:
            if path[0] in sectors:
                desired.append(path)
        paths = desired

    all_regions = root.xpath('//region/@name')
    all_regions = set(all_regions).difference(['USA'])  # we remove USA from both sets

    regions = args.regions.split(',') if args.regions else all_regions
    regions = sorted(regions)

    zeroes = ',0' * len(years)    # fill in with zeroes for reading into a dataframe

    # data values
    for region in regions:
        if region not in all_regions:   # use only regions defined for this XML file
            continue

        for tup in paths:
            f.write(which + ',' + region + ',')
            f.write(','.join(tup))
            f.write(zeroes + '\n')


class BuildingCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Dump combinations of building energy use sectors, techs, and fuels.'''}
        super(BuildingCommand, self).__init__('building', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        parser.add_argument('-p', '--project', default=DFLT_PROJECT,
                            help='''The name of the project to use to locate GCAM reference files. Default is "{}"'''.format(
                                DFLT_PROJECT))

        parser.add_argument('-o', '--outputFile', default=OUTPUT_FILE,
                            help='''The CSV file to create with lists of unique building sectors, 
                            subsectors, and technologies. Default is "{}"'''.format(OUTPUT_FILE))

        parser.add_argument('-s', '--sectors', default=None,
                            help='''A comma-delimited list of sectors to include in the generated template. Use quotes 
                            around the argument if there are embedded blanks. By default, all known building technology
                            sectors are included.''')

        parser.add_argument('-r', '--regions', default=None,
                            help='''A comma-delimited list of regions to include in the generated template. 
                             By default all regions are included. ''')

        parser.add_argument('-u', '--GCAM-USA', action="store_true",
                            help='''If set, produce output compatible with GCAM-USA regions.''')

        parser.add_argument('-y', '--years', default='2015-2100',
                            help='''A hyphen-separated range of timestep years to include in the generated template.
                            Default is "2015-2100"''')

        return parser


    def run(self, args, tool):
        main_xml_file = 'building_det.xml'
        usa_xml_file = 'building_USA.xml'

        main_xpath = '//supplysector/subsector/stub-technology/period/minicam-energy-input'
        usa_xpath = '//global-technology-database/location-info/technology/period/minicam-energy-input'

        with open(args.outputFile, 'w') as f:
            years = validate_years(args.years)
            if years is None:
                raise Exception(
                    'Year argument must be two integers separated by a hyphen, with second > first. Got "{}"'.format(
                        args.years))

            # column headers
            f.write("which,region,sector,subsector,technology,input,")
            f.write(','.join(map(str, years)))
            f.write("\n")

            save_bldg_techs(f, args, years, main_xml_file, main_xpath, 'GCAM-32')

            if args.GCAM_USA:
                save_bldg_techs(f, args, years, usa_xml_file, usa_xpath, 'GCAM-USA')
