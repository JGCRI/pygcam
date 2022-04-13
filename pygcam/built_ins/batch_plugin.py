'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2022 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from ..subcommand import SubcommandABC, clean_help

class BatchCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : clean_help('''Run a set of queries in batch mode and write 
            results to the indicated CSV file.''')}

        super(BatchCommand, self).__init__('batch', subparsers, kwargs, group='query')

    def addArgs(self, parser):
        parser.add_argument('-c', '--csvPath',
                            help=clean_help('''The pathname of the CSV file to which output should be written'''))

        parser.add_argument('-d', '--xmldb',
                             help=clean_help('''The XML database to query (default is computed as
                             {GCAM.SandboxDir}/output/{GCAM.DbFile}. Overrides the -w flag.'''))

        parser.add_argument('-D', '--noDelete', action="store_true",
                            help=clean_help('''Don't delete any temporary file created by extracting a query 
                                from a query file. Used mainly for debugging.'''))

        parser.add_argument('-g', '--groupDir', default='',
                            help=clean_help('''The scenario group directory name, if any. Used with to compute default
                            for --workspace argument.'''))

        parser.add_argument('-q', '--queryNames',
                            help=clean_help('''A path-type delimited string holding the names
                               of the queries to run'''))

        parser.add_argument('-Q', '--queryPath',
                            help=clean_help('''A path-type delimited string holding the names
                               of XML query files holding the queries to extract'''))

        parser.add_argument('-s', '--scenario',
                            help=clean_help('''The scenario to run the query for'''))

        parser.add_argument('-w', '--workspace', default='',
                            help=clean_help('''The workspace directory in which to find the XML database.
                                    Defaults computed as {GCAM.SandboxDir}/{groupDir}/{scenario}.
                                    Overridden by the -d flag.'''))
        return parser

    def run(self, args, tool):
        from ..config import pathjoin, getParam
        from ..query import runExtractedQueries

        sandbox = args.workspace or pathjoin(getParam('GCAM.SandboxDir'), args.groupDir, args.scenario)
        xmldb = args.xmldb or pathjoin(sandbox, 'output', getParam('GCAM.DbFile'))

        runExtractedQueries(args.scenario, args.queryNames, args.queryPath, args.csvPath, xmldb=xmldb, delete=not args.noDelete)


PluginClass = BatchCommand
