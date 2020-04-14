"""
.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2020 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC, clean_help
from ..log import getLogger

_logger = getLogger(__name__)

def get_re_techs(tech_cols, params, region):
    return [tech for tech in tech_cols if params.loc[region, tech] == 1]

def element_path(elt, withInput):
    d = {'input' : elt.attrib['name']}

    sector = subsector = technology = None

    for node in elt.iterancestors():    # walk up the hierarchy
        tag = node.tag
        attr = node.attrib

        if tag == 'period':
            pass

        elif tag == 'location-info':
            d['sector'] = sector = attr['sector-name']
            d['subsector'] = subsector = attr['subsector-name']

        elif tag == 'supplysector':
            d['sector'] = sector = attr['name']

        elif tag in ('stub-technology', 'technology'):
            d['technology'] = technology = attr['name']

        elif tag == 'subsector':
            d['subsector'] = subsector = attr['name']

        elif tag in ('global-technology-database', 'region'):
            break

    return (sector, subsector, technology, d['input']) if withInput else (sector, subsector, technology)



def save_bldg_techs(f, args, years, xml_file, xpath, which, withInput):
    from ..config import getParam
    from ..utils import pathjoin
    from ..XMLFile import XMLFile

    gcamDir = getParam('GCAM.RefWorkspace', section=args.projectName)
    pathname = pathjoin(gcamDir, 'input', 'gcamdata', 'xml', xml_file)

    _logger.info("Reading {}".format(pathname))
    xml = XMLFile(pathname)
    root = xml.getRoot()

    nodes = root.xpath(xpath)
    paths = sorted(set([element_path(node, withInput) for node in nodes])) # use 'set' to remove dupes

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

TECH_OUTPUT_FILE = 'industry_tech_template.csv'
ELEC_OUTPUT_FILE = 'industry_elec_template.csv'

class IndustryCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Dump combinations of industry energy use sectors, techs, and fuels.'''}
        super(IndustryCommand, self).__init__('industry', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        parser.add_argument('-e', '--electricOnly', action="store_true",
                            help=clean_help('''Generate a template for electricity-based sources only.'''))


        parser.add_argument('-o', '--outputFile', default=None,
                            help=clean_help('''The CSV file to create with lists of unique industry sectors, 
                            subsectors, and technologies. Default is "[GCAM.CsvTemplateDir]/{}" or 
                            "[GCAM.CsvTemplateDir]/{}", depending on the --electricOnly flag.
                            Use an absolute path to generate the file to another location.'''.format(
                                TECH_OUTPUT_FILE, ELEC_OUTPUT_FILE)))

        parser.add_argument('-s', '--sectors', default="industrial energy use",
                            help=clean_help('''A comma-delimited list of sectors to include in the generated template. Use quotes 
                            around the argument if there are embedded blanks. By default, all known industry technology
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

        outputFile = args.outputFile or (ELEC_OUTPUT_FILE if args.electricOnly else TECH_OUTPUT_FILE)

        main_xml_file = 'industry.xml'
        usa_xml_file = 'industry_USA.xml'

        main_xpath = '//supplysector/subsector/stub-technology/period/minicam-energy-input'
        usa_xpath = '//supplysector/subsector/stub-technology/period/minicam-energy-input'

        templateDir = getParam('GCAM.CsvTemplateDir')
        outputPath = pathjoin(templateDir, outputFile)

        _logger.info('Writing {}'.format(outputPath))
        with open(outputPath, 'w') as f:
            years = validate_years(args.years)
            if years is None:
                raise Exception(
                    'Year argument must be two integers separated by a hyphen, with second > first. Got "{}"'.format(
                        args.years))

            # column headers
            f.write("which,region,sector,subsector,technology,")
            withInput = not args.electricOnly
            if withInput:
                f.write("input,")

            f.write(','.join(map(str, years)))
            f.write("\n")

            save_bldg_techs(f, args, years, main_xml_file, main_xpath, 'GCAM-32', withInput)

            if args.GCAM_USA:
                save_bldg_techs(f, args, years, usa_xml_file, usa_xpath, 'GCAM-USA', withInput)
