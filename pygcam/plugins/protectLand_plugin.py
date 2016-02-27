from pygcam.config import DEFAULT_SECTION
from pygcam.landProtection import UnmanagedLandClasses, DefaultTemplate, driver
from pygcam.plugin import PluginBase

class Plugin(PluginBase):
    def __init__(self, subparsers):
        helptext = '''Generate versions of GCAM's land_input XML files that protect a
                      given fraction of land of the given land types in the given regions. The script can be
                      run multiple times on the same file to apply different percentage protection to
                      distinct regions or land classes. The script detects if you attempt to protect
                      already-protected land class and region combinations, as this fails in GCAM.'''

        description = helptext + ' ' + '''[Add more details]'''

        kwargs = {'help' : helptext, 'description' : description}
        super(Plugin, self).__init__('protect', kwargs, subparsers)

    def addArgs(self):
        parser = self.parser

        parser.add_argument('-b', '--backup', action='store_true',
                            help='''Make a copy of the output file, if it exists (with an added ~ after
                            filename) before writing new output.''')

        parser.add_argument('-c', '--configSection', type=str, default=DEFAULT_SECTION,
                            help='''The name of the section in the config file to read from.
                            Defaults to %s''' % DEFAULT_SECTION)

        parser.add_argument('-f', '--fraction', type=float, default=None,
                            help='''The fraction of land in the given land classes to protect. (Required)''')

        parser.add_argument('-i', '--inFile', action='append',
                            help='''One or more input files to process. Use separate -i flags for each file.''')

        parser.add_argument('--inPlace', action='store_true',
                            help='''Edit the file in place. This must be given explicitly, to avoid overwriting
                            files by mistake.''')

        parser.add_argument('-l', '--landClasses', action='append',
                            help='''The land class or classes to protect in the given regions. Multiple,
                            comma-delimited land types can be given in a single argument, or the -l flag can
                            be repeated to indicate additional land classes. By default, all unmanaged land
                            classes are protected. Allowed land classes are %s''' % UnmanagedLandClasses)

        parser.add_argument('-m', '--mkdir', action='store_true',
                            help='''Make the output dir if necessary.''')

        parser.add_argument('-o', '--outDir', type=str, default='.',
                            help='''The directory into which to write the modified files. Default is current directory.''')

        parser.add_argument('-t', '--template', type=str, default=DefaultTemplate,
                            help='''Specify a template to use for output filenames. The keywords {fraction}, {filename},
                            {regions}, and {classes} (with surrounding curly braces) are replaced by the following values
                            and used to form the name of the output files, written to the given output directory.
                            fraction: 100 times the given fraction (i.e., int(fraction * 100));
                            filename: the name of the input file being processed (e.g., land_input_2.xml or land_input_3.xml);
                            basename: the portion of the input filename prior to the extension (i.e., before '.xml');
                            regions: the given regions, separated by '-', or the word 'global' if no regions are specified;
                            classes: the given land classes, separated by '-', or the word 'unmanaged' if no land classes
                            are specified. The default pattern is "%s".''' % DefaultTemplate)

        parser.add_argument('-r', '--regions', action='append',
                            help='''The region or regions for which to protect land. Multiple, comma-delimited
                            regions can be given in a single argument, or the -r flag can be repeated to indicate
                            additional regions. By default, all regions are protected.''')

        parser.add_argument('-s', '--scenario', default=None,
                            help='''The name of a land-protection scenario defined in the file given by the --scenarioFile
                            argument or it's default value.''')

        parser.add_argument('-S', '--scenarioFile', default=None,
                            help='''An XML file defining land-protection scenarios. Default is the value
                            of configuration file parameter GCAM.LandProtectionXmlFile.''')

        parser.add_argument('-w', '--workspace', type=str, default=None,
                            help='''Specify the path to the GCAM workspace to use. If input files are not identified
                            explicitly, the files in {workspace}/input/gcam-data-system/xml/aglu-xml/land_input_{2,3}.xml
                            are used as inputs. Default is value of configuration parameter GCAM.ReferenceWorkspace.''')

    def run(self, args):
        driver(args)


#PluginClass = ProtectCommand
