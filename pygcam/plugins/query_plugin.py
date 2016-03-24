from pygcam.subcommand import SubcommandABC
from pygcam.query import main as queryMain
from pygcam.log import getLogger

_logger = getLogger(__name__)

VERSION = '0.2'

class QueryCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'fromfile_prefix_chars' : '@',      # use "@" before value to substitute contents of file as arguments

                  'help' : '''Run one or more GCAM database queries by generating and running the
                  named XML queries.''',

                  'description' : '''Run one or more GCAM database queries by generating and running the
                  named XML queries. The results are placed in a file in the specified
                  output directory with a name composed of the basename of the
                  XML query file plus the scenario name. For example,
                  "gcamtool query -o. -s MyReference,MyPolicyCase liquids-by-region"
                  would generate query results into the files ./liquids-by-region-MyReference.csv
                  and ./liquids-by-region-MyPolicyCase.csv.

                  The named queries are located using the value of config variable GCAM.QueryPath,
                  which can be overridden with the -Q argument. The QueryPath consists of one or
                  more colon-delimited elements that can identify directories or XML files. The
                  elements of QueryPath are searched in order until the named query is found. If
                  a path element is a directory, the filename composed of the query + '.xml' is
                  sought in that directory. If the path element is an XML file, a query with a
                  title matching the query name (first literally, then by replacing '_' and '-'
                  characters with spaces) is sought. Note that query names are case-sensitive.

                  This script populates an initial configuration file in ~/.pygcam.cfg when
                  first run. The config file should be customized as needed, e.g., to set "GcamRoot"
                  to the directory holding your Main_User_Workspace unless it happens to live in
                  ~/GCAM, which is the default value.'''}

        super(QueryCommand, self).__init__('query', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('queryName', nargs='*',
                            help='''A file or files, each holding an XML query to run. (The ".xml" suffix will be added if needed.)
                                    If an argument is preceded by the "@" sign, it is read and its contents substituted as the
                                    values for this argument. That means you can store queries to run in a file (one per line) and
                                    just reference the file by preceding the filename argument with "@".''')

        parser.add_argument('-d', '--xmldb',
                             help='''The XML database to query (default is value of GCAM.DbFile, in the GCAM.Workspace's
                             "output" directory. Overrides the -w flag.''')

        parser.add_argument('-D', '--noDelete', action="store_true",
                            help='''Don't delete any temporary file created by extracting a query from a query file. Used
                                    mainly for debugging.''')

        parser.add_argument('-R', '--regionMap',
                            help='''A file containing tab-separated pairs of names, the first being a GCAM region
                                    and the second being the name to map this region to. Lines starting with "#" are
                                    treated as comments. Lines without a tab character are also ignored. This arg
                                    overrides the value of config variable GCAM.RegionMapFile.''')

        parser.add_argument('-n', '--noRun', action="store_true",
                            help="Show the command to be run, but don't run it")

        parser.add_argument('-o', '--outputDir',
                             help='Where to output the result (default taken from config parameter "GCAM.OutputDir")')

        parser.add_argument('-Q', '--queryPath',
                            help='''A semicolon-delimited list of directories or filenames to look in to find query files.
                                    Defaults to value of config parameter GCAM.QueryPath''')

        parser.add_argument('-r', '--regions',
                            help='''A comma-separated list of regions on which to run queries found in query files structured
                                    like Main_Queries.xml. If not specified, defaults to querying all 32 regions.''')

        parser.add_argument('-s', '--scenario', default='Reference',
                            help='''A comma-separated list of scenarios to run the query/queries for (default is "Reference")
                                    Note that these refer to a scenarios in the XML database.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + VERSION)

        parser.add_argument('-w', '--workspace', default='',
                            help='''The workspace directory in which to find the XML database.
                                    Defaults to value of config file parameter GCAM.Workspace.
                                    Overridden by the -d flag.''')

        return parser

    def run(self, args, tool):
        queryMain(args)


PluginClass = QueryCommand
