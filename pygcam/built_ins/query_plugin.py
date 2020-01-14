"""
.. Support for querying GCAM's XML database and processing results.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.

"""
from ..subcommand import SubcommandABC, clean_help

class QueryCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'fromfile_prefix_chars' : '@',      # use "@" before value to substitute contents of file as arguments
                  'help' : '''Run one or more GCAM database queries by generating and running the named XML queries.'''}

        super(QueryCommand, self).__init__('query', subparsers, kwargs, group='project')


    def addArgs(self, parser):
        parser.add_argument('queryName', nargs='*',
                            help=clean_help('''A file or files, each holding an XML query to run. (The ".xml" suffix will be
                            added if needed.) If an argument is preceded by the "@" sign, it is read and its
                            contents substituted as the values for this argument. That means you can store queries
                            to run in a file (one per line) and just reference the file by preceding the filename
                            argument with "@".'''))

        parser.add_argument('-b', '--batchFile',
                             help=clean_help('''An XML batch file to run. The file will typically contain 
                             multiple queries. By default, output is written to 
                             {outputDir}/{batchFile basename}.csv. Use '-B' to change this.'''))

        parser.add_argument('-B', '--batchOutput', default='',
                             help=clean_help('''Where to write the output of the XML batch file given by 
                             the '-b' flag. Non-absolute paths are treated as relative to the given outputDir.'''))

        parser.add_argument('-d', '--xmldb',
                             help=clean_help('''The XML database to query (default is computed as
                             {GCAM.SandboxDir}/output/{GCAM.DbFile}. Overrides the -w flag.'''))

        parser.add_argument('-D', '--noDelete', action="store_true",
                            help=clean_help('''Don't delete any temporary file created by extracting a query from a query file. Used
                                    mainly for debugging.'''))

        parser.add_argument('-g', '--groupDir', default='',
                            help=clean_help('''The scenario group directory name, if any. Used with to compute default
                            for --workspace argument.'''))

        parser.add_argument('-n', '--noRun', action="store_true",
                            help=clean_help("Show the command to be run, but don't run it"))

        parser.add_argument('-o', '--outputDir',
                             help=clean_help('Where to output the result (default taken from config parameter "GCAM.OutputDir")'))

        parser.add_argument('-p', '--prequery', action="store_true",
                            help=clean_help('''Generate the XMLDBDriver.properties file and associated batch file to be
                                 run by GCAM when GCAM.BatchMultipleQueries or GCAM.InMemoryDatabase are True.'''))

        parser.add_argument('-q', '--queryXmlFile',
                            help=clean_help('''An XML file holding a list of queries to run, with optional mappings specified to
                            rewrite output. This file has the same structure as the <queries> element in project.xml.'''))

        parser.add_argument('-Q', '--queryPath',
                            help=clean_help('''A semicolon-delimited list of directories or filenames to look in to find query files.
                                    Defaults to value of config parameter GCAM.QueryPath'''))

        parser.add_argument('-r', '--regions',
                            help=clean_help('''A comma-separated list of regions on which to run queries found in query files structured
                                    like Main_Queries.xml. If not specified, defaults to querying all 32 regions.'''))

        parser.add_argument('-R', '--regionMap',
                            help=clean_help('''A file containing tab-separated pairs of names, the first being a GCAM region
                                    and the second being the name to map this region to. Lines starting with "#" are
                                    treated as comments. Lines without a tab character are also ignored. This arg
                                    overrides the value of config variable GCAM.RegionMapFile.'''))

        parser.add_argument('-s', '--scenario', default='Reference',
                            help=clean_help('''The scenario to run the query/queries for (default is "Reference")
                                    Note that this must refers to a scenarios in the XML database.'''))

        parser.add_argument('-S', '--rewriteSetsFile',
                            help=clean_help('''An XML file defining query maps by name (default taken from
                            config parameter "GCAM.RewriteSetsFile")'''))

        parser.add_argument('-w', '--workspace', default='',
                            help=clean_help('''The workspace directory in which to find the XML database.
                                    Defaults computed as {GCAM.SandboxDir}/{groupDir}/{scenario}.
                                    Overridden by the -d flag.'''))

        return parser

    def run(self, args, tool):
        from ..query import queryMain

        queryMain(args)
