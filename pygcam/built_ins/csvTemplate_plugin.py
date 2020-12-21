"""
.. Generate a CSV file template used to define mitigation policies

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2020  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
#
# TBD: need to merge aspects of ZEVPolicy into this, e.g., handling of
# TBD: --include flag, including "market" in CSV output.
#
# There are two basic policy types: RES policies (ZEV and RES) and technology
# forcing policies that directly change efficiency or coefficients over time.
#

from ..subcommand import SubcommandABC, clean_help
from ..log import getLogger

_logger = getLogger(__name__)

def element_path(elt):
    """
    Walk up the XML structure from the given element, producing a tuple with the
    names of the region, sector, subsector, technology, and input found in this
    "path".

    :param elt: (lxml.etree.Element) an "input" element to start from
    :return: tuple of strings: (region, sector, subsector, technology, input)
    """
    input = elt.attrib['name']
    sector = subsector = technology = region = None

    for node in elt.iterancestors():    # walk up the hierarchy
        tag = node.tag
        attr = node.attrib

        if tag == 'period':
            continue

        elif tag == 'location-info':
            sector = attr['sector-name']
            subsector = attr['subsector-name']

        elif tag == 'region':
            region = attr['name' ]
            break

        elif tag == 'supplysector':
            sector = attr['name']

        elif tag in ('stub-technology', 'technology'):
            technology = attr['name']

        elif tag in ('subsector', 'tranSubsector'):
            subsector = attr['name']

        elif tag in ('global-technology-database'):
            break

    return (region, sector, subsector, technology, input)


def save_template(f, args, years, xml_file, xpath, which):
    from ..config import getParam
    from ..utils import pathjoin
    from ..XMLFile import XMLFile

    # TBD: Make this more flexible. Create config param for this, let user override?
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

DEFAULT_OUTPUT_FILE = '{target}_template.csv'

class CsvTemplateCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Dump combinations of regions, sectors, subsectors, techs, and fuels 
            for use in generating XML policy input files.'''}
        super(CsvTemplateCommand, self).__init__('csvTemplate', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        # positional argument
        parser.add_argument('target', choices=['buildingTech', 'buildingElec', 'transportTech', 'RES', 'ZEV'],
                            help=clean_help('''The policy target.'''))

        parser.add_argument('-i', '--include', action='append', default=None,
                            help=clean_help('''A colon (":") delimited list of comma-delimited sectors, 
                                subsectors, and technologies to include in the CSV template file.
                                Example: "--include trn_pass_road_LDV_4W::BEV,FCEV" means include only two 
                                technologies (BEV,FCEV), but for any subsector under the specified sector. 
                                Multiple -I arguments are allowed.'''))

        parser.add_argument('-o', '--outputFile', default=None,
                            help=clean_help('''The CSV file to create with lists of unique regions, sectors, 
                            subsectors, technologies, and inputs. Default is "[GCAM.CsvTemplateDir]/{}".
                            Use an absolute path to generate the file to another location.'''.format(
                                DEFAULT_OUTPUT_FILE)))

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
        from ..utils import pathjoin, validate_years, get_path
        from ..config import getParam
        from ..error import CommandlineError

        years = validate_years(args.years)
        if years is None:
            raise CommandlineError('Year argument must be two integers separated by a hyphen, '
                                   'with second > first. Got "{}"'.format(args.years))

        target = args.target
        outputFile = args.outputFile or DEFAULT_OUTPUT_FILE.format(target=target)
        outputPath = get_path(outputFile, pathjoin(getParam("GCAM.ProjectDir"), "etc"))

        # TBD: allow specification of full path to xml files?

        if target == 'buildingTech':
            main_xml_file = 'building_det.xml'
            usa_xml_file = 'building_USA.xml'

            main_xpath = '//supplysector/subsector/stub-technology/period/minicam-energy-input'
            usa_xpath = '//global-technology-database/location-info/technology/period/minicam-energy-input'

        elif target == 'buildingElec':
            pass    # TBD

        elif target == 'transportTech':
            pass    # TBD

        elif target == 'RES':
            pass    # TBD

        elif target == 'ZEV':
            pass    # TBD

        _logger.info('Writing %s', outputPath)

        with open(outputPath, 'w') as f:
            # column headers
            f.write("which,region,market,sector,subsector,technology,input,")
            f.write(','.join(map(str, years)))
            f.write("\n")

            save_template(f, args, years, main_xml_file, main_xpath, 'GCAM-32')

            if args.GCAM_USA:
                save_template(f, args, years, usa_xml_file, usa_xpath, 'GCAM-USA')
