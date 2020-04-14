#!/usr/bin/env python
"""
.. Read GCAM's transport technology files and generate a CSV template for the sectors/regions indicated
.. by the user that can be modified to adjust the energy efficiencies of the selected technologies.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2019  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
import os
from ..config import getParam
from ..XMLFile import XMLFile
from ..subcommand import SubcommandABC, clean_help
from ..log import getLogger

_logger = getLogger(__name__)

def element_path(elt):
    d = {'input' : elt.attrib['name']}

    for node in elt.iterancestors():    # walk up the hierarchy
        tag = node.tag
        attr = node.attrib

        if tag == 'period':
            pass

        elif tag == 'region':
            d['region'] = attr['name' ]
            break

        elif tag == 'location-info':
            d['sector'] = attr['sector-name']
            d['subsector'] = attr['subsector-name']

        elif tag == 'supplysector':
            d['sector'] = attr['name']

        elif tag in ('stub-technology', 'technology'):
            d['technology'] = attr['name']

        elif tag == 'tranSubsector':
            d['subsector'] = attr['name']

    return (d['region'], d['sector'], d['subsector'], d['technology'], d['input'])

def save_transport_techs(f, args, years):
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

    xpath = regionPrefix + '/supplysector/tranSubsector/stub-technology/period/minicam-energy-input'

    nodes = root.xpath(xpath)
    paths = sorted(set([element_path(node) for node in nodes if node.find('./coefficient') is not None])) # use 'set' to remove dupes

    matched_prefix = []
    if args.prefixes:
        prefixes = set(args.prefixes.split(','))
        for path in paths:
            for prefix in prefixes:
                if path[1].startswith(prefix):
                    matched_prefix.append(path)

    # filter out sectors missing from cmdline arg, if specified
    matched_sector = []
    if args.sectors:
        sectors = set(args.sectors.split(','))
        for path in paths:
            if path[1] in sectors:
                matched_sector.append(path)

    if args.prefixes or args.sectors:
        paths = sorted(set(matched_prefix + matched_sector))

    zeroes = ',0' * len(years)    # fill in with zeroes for reading into a dataframe

    # data values
    for tup in paths:
        f.write(','.join(tup) + zeroes + '\n')


class TransportCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Write combinations of transport sectors, techs, and fuels to a template CSV file.'''}
        super(TransportCommand, self).__init__('transport', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        OUTPUT_FILE = 'transport_tech_template.csv'

        parser.add_argument('-o', '--outputFile', default=OUTPUT_FILE,
                            help=clean_help('''The CSV template file to create with transport sectors, 
                            subsectors, and technologies. Default is "[GCAM.CsvTemplateDir]/{}"
                            Use an absolute path to generate the file to another location.'''.format(OUTPUT_FILE)))

        parser.add_argument('-p', '--prefixes', default=None,
                            help=clean_help('''A comma-delimited list of sector prefixes indicating which sectors to include in the 
                            generated template. Use quotes around the argument if there are embedded blanks.'''))

        parser.add_argument('-s', '--sectors', default=None,
                            help=clean_help('''A comma-delimited list of sectors to include in the generated template. Use quotes 
                            around the argument if there are embedded blanks. By default, all known transport technology
                            sectors are included.'''))

        parser.add_argument('-r', '--regions', default=None,
                            help=clean_help('''A comma-delimited list of regions to include in the generated template. 
                             By default all regions are included. '''))

        parser.add_argument('-y', '--years', default='2015-2100',
                            help=clean_help('''A hyphen-separated range of timestep years to include in the generated template.
                            Default is "2015-2100"'''))
        return parser


    def run(self, args, tool):
        from ..utils import pathjoin, validate_years

        years = validate_years(args.years)
        if years is None:
            raise Exception(
                'Year argument must be two integers separated by a hyphen, with second > first. Got "{}"'.format(
                    args.years))

        templateDir = getParam('GCAM.CsvTemplateDir')
        outputPath = pathjoin(templateDir, args.outputFile)

        _logger.info("Writing {}".format(outputPath))
        with open(outputPath, 'w') as f:
            # column headers
            f.write("region,sector,subsector,technology,input,")
            f.write(','.join(map(str, years)))
            f.write("\n")

            save_transport_techs(f, args, years)
