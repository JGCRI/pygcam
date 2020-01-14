"""
.. Support for generating land-protection scenarios described in an XML file.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC, clean_help
from ..constants import UnmanagedLandClasses

DefaultTemplate = 'prot_{fraction}_{filename}'


class ProtectLandCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {#'aliases' : ['pro'],
                 'help': clean_help('''Generate versions of GCAM's land_input XML files that protect a
                 given fraction of land of the given land types in the given regions.''')}

        super(ProtectLandCommand, self).__init__('protect', subparsers, kwargs, group='project')

    def addArgs(self, parser):
        parser.add_argument('-b', '--backup', action='store_true',
                            help=clean_help('''Make a copy of the output file, if it exists (with an added ~ after
                            filename) before writing new output. This option is ignored if a scenario
                            file is specified.'''))

        parser.add_argument('-f', '--fraction', type=float, default=None,
                            help=clean_help('''The fraction of land in the given land classes to protect. (Required,
                            unless a scenario file is specified, in which case this option is ignored.)'''))

        parser.add_argument('--inPlace', action='store_true',
                            help=clean_help('''Edit the file in place. This must be given explicitly, to avoid overwriting
                            files by mistake.'''))

        parser.add_argument('-l', '--landClasses', action='append',
                            help=clean_help('''The land class or classes to protect in the given regions. Multiple,
                            comma-delimited land types can be given in a single argument, or the -l flag can
                            be repeated to indicate additional land classes. By default, all unmanaged land
                            classes are protected. Allowed land classes are %s.
                            This option is ignored if a scenario file is specified. ''' % UnmanagedLandClasses))

        parser.add_argument('-m', '--mkdir', action='store_true',
                            help=clean_help('''Make the output dir if necessary.'''))

        parser.add_argument('-o', '--outDir', type=str, default='.',
                            help=clean_help('''The directory into which to write the modified files.
                                    Default is current directory.'''))

        parser.add_argument('-O', '--otherArable', action='store_true',
                            help=clean_help('''Include OtherArableLand in the list of default land classes to protect.
                            This flag is ignored if the -l (--landClasses) argument is used.'''))

        parser.add_argument('-t', '--template', type=str, default=DefaultTemplate,
                            help=clean_help('''Specify a template to use for output filenames. The keywords {fraction}, {filename},
                            {regions}, and {classes} (with surrounding curly braces) are replaced by the following values
                            and used to form the name of the output files, written to the given output directory.
                            fraction: 100 times the given fraction (i.e., int(fraction * 100));
                            filename: the name of the input file being processed (e.g., land_input_2.xml or land_input_3.xml);
                            basename: the portion of the input filename prior to the extension (i.e., before '.xml');
                            regions: the given regions, separated by '-', or the word 'global' if no regions are specified;
                            classes: the given land classes, separated by '-', or the word 'unmanaged' if no land classes
                            are specified. The default pattern is "%s".
                            This option is ignored if a scenario file is specified.''' % DefaultTemplate))

        parser.add_argument('-r', '--regions', action='append',
                            help=clean_help('''The region or regions for which to protect land. Multiple, comma-delimited
                            regions can be given in a single argument, or the -r flag can be repeated to indicate
                            additional regions. By default, all regions are protected.
                            This option is ignored if a scenario file is specified.'''))

        parser.add_argument('-s', '--scenario', default=None,
                            help=clean_help('''The name of a land-protection scenario defined in the file given by the --scenarioFile
                            argument or it's default value.'''))

        parser.add_argument('-S', '--scenarioFile', default=None,
                            help=clean_help('''An XML file defining land-protection scenarios. Default is the value
                            of configuration file parameter GCAM.LandProtectionXmlFile.'''))

        parser.add_argument('-w', '--workspace', type=str, default=None,
                            help=clean_help('''Specify the path to the GCAM workspace to use. The files in
                            {workspace}/input/gcam-data-system/xml/aglu-xml/land_input_{2,3}.xml (before GCAM v5.1), or
                            {workspace}/input/gcamdata/xml/land_input_{2,3,4,5}*.xml (starting in GCAM v5.1)
                            are used as inputs. Default is value of configuration parameter
                            GCAM.RefWorkspace.'''))

        return parser

    def run(self, args, tool):
        from ..landProtection import protectLandMain

        protectLandMain(args)
