#!/usr/bin/env python
"""
.. "new" sub-command (creates a new project)

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC, clean_help
from ..log import getLogger

_logger = getLogger(__name__)

OUTPUT_FILE  = 'building_elec_template.csv'

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

    return (d['sector'], d['subsector'],d['technology'])


def save_bldg_techs(f, args, years, xml_file, xpath, which):
    from ..config import getParam
    from ..utils import pathjoin
    from ..XMLFile import XMLFile

    gcamDir = getParam('GCAM.RefWorkspace', section=args.projectName)
    pathname = pathjoin(gcamDir, 'input', 'gcamdata', 'xml', xml_file)

    _logger.info("Reading {}".format(pathname))
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

    all_regions = set(root.xpath('//region/@name'))
    if args.GCAM_USA:
        all_regions = all_regions.difference(['USA'])  # remove USA since states will be used

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

# Deprecated. Use gt building --electricOnly instead
class BuildingElecCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Dump combinations of building energy use sectors, techs, and fuels.'''}
        super(BuildingElecCommand, self).__init__('buildingElec', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        parser.add_argument('-o', '--outputFile', default=OUTPUT_FILE,
                            help=clean_help('''The CSV file to create with lists of unique building sectors, 
                            subsectors, and technologies. Default is "[GCAM.CsvTemplateDir]/{}".
                            Use an absolute path to generate the file to another location.'''.format(OUTPUT_FILE)))

        parser.add_argument('-s', '--sectors', default=None,
                            help=clean_help('''A comma-delimited list of sectors to include in the generated template. Use quotes 
                            around the argument if there are embedded blanks. By default, all known building technology
                            sectors are included.'''))

        parser.add_argument('-r', '--regions', default=None,
                            help=clean_help('''A comma-delimited list of regions to include in the generated template. 
                             By default all regions are included. '''))

        parser.add_argument('-u', '--GCAM-USA', action="store_true",
                            help=clean_help('''If set, produce output compatible with GCAM-USA regions.'''))

        parser.add_argument('-y', '--years', default='2015-2100',
                            help=clean_help('''A hyphen-separated range of timestep years to include in the generated template.
                            Default is "2015-2100"'''))

        return parser


    def run(self, args, tool):
        from ..utils import pathjoin, validate_years
        from ..config import getParam

        main_xml_file = 'building_det.xml'
        usa_xml_file = 'building_USA.xml'

        main_xpath = '//supplysector/subsector/stub-technology/period/minicam-energy-input'
        usa_xpath = '//global-technology-database/location-info/technology/period/minicam-energy-input'

        templateDir = getParam('GCAM.CsvTemplateDir')
        outputPath = pathjoin(templateDir, args.outputFile)

        _logger.info('Writing {}'.format(outputPath))
        with open(outputPath, 'w') as f:
            years = validate_years(args.years)
            if years is None:
                raise Exception(
                    'Year argument must be two integers separated by a hyphen, with second > first. Got "{}"'.format(
                        args.years))

            # column headers
            f.write("which,region,sector,subsector,technology,")
            f.write(','.join(map(str, years)))
            f.write("\n")

            save_bldg_techs(f, args, years, main_xml_file, main_xpath, 'GCAM-32')

            if args.GCAM_USA:
                save_bldg_techs(f, args, years, usa_xml_file, usa_xpath, 'GCAM-USA')
