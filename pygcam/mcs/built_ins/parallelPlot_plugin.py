# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from ..error import PygcamMcsUserError
from .McsSubcommandABC import McsSubcommandABC, clean_help

class ParallelPlotCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Generate a parallel coordinates plot for a set
        of simulation results. '''}
        super(ParallelPlotCommand, self).__init__('parallelPlot', subparsers, kwargs)
        self.group = None # don't display this in GUI for now

    def addArgs(self, parser):
        # Required arguments
        parser.add_argument('-r', '--resultName', type=str, required=True,
                            help=clean_help('''The name of the result to create the plot for'''))

        parser.add_argument('-s', '--simId',    type=int, required=True, help=clean_help('The id of the simulation'))

        parser.add_argument('-S', '--scenario', type=str, required=True, help=clean_help('The name of the scenario'))

        # Optional Arguments
        parser.add_argument('-b', '--inputBins', type=int, default=None,
                            help=clean_help('''Allocate values for each variable into the given number of bins. By
                            default, the bins boundaries are evenly spaced. If the -q/--quantile flag
                            is given, the bins will contain an equal number of values. Use -l / --labels
                            to assign category names to the bins.'''))

        parser.add_argument('-l', '--outputLabels', type=str, default='Low,Medium,High',
                            help=clean_help('''Category names for the output bins. Value must be a comma-delimited
                            list of strings.'''))

        parser.add_argument('--limit', type=int, default=0,
                            help=clean_help('''Limit analysis to this number of trials'''))

        parser.add_argument('-i', '--numInputs', type=int,
                            help=clean_help('''The number of most-highly rank-correlated inputs to include in the figure.
                            By default, an attempt is made to plot all inputs.'''))

        parser.add_argument('-I', '--invert', action='store_true',
                            help=clean_help('''Plot negatively correlated data as (1 - x) rather than (x).'''))

        parser.add_argument('-o', '--output', type=str,
                            help=clean_help('''The name of the graphic output file to create. File format is determined from
                            the filename extension. Default is
                            {plotDir}/s{scenarioId}/{scenario}-{resultName}-parallel.png'''))

        parser.add_argument('-q', '--quantiles', action='store_true',
                            help=clean_help('''Create bins with an (approx.) equal number of values rather the
                            default, which is to space the bin boundaries equally across the range of values.'''))

        parser.add_argument('-R', '--rotate', type=int, default=None,
                            help=clean_help('''Angle of rotation for X-axis labels'''))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ..analysis import Analysis, makePlotPath

        simId = args.simId
        scenarioList = args.scenario.split(',')
        resultList = args.resultName.split(',')
        outputLabels = args.outputLabels.split(',')
        numInputs = args.numInputs
        bins = args.inputBins
        invert = args.invert
        quantiles = args.quantiles
        rotation = args.rotate

        anaObj = Analysis(args.simId, scenarioList, resultList, limit=args.limit)

        inputDF = anaObj.getInputs()

        # Drop any inputs with names ending in '-linked' since these are an artifact
        linked = [s for s in inputDF.columns if s.endswith('-linked')]
        if linked:
            inputDF = inputDF.drop(linked, axis=1)

        if not (scenarioList and resultList):
            raise PygcamMcsUserError("scenario and resultName must be specified")

        resultDict = anaObj.getResults(scenarioList=scenarioList, resultList=resultList)

        for scenario in scenarioList:
            resultDF = resultDict[scenario]

            for resultName in resultList:
                resultSeries = resultDF[resultName]

                basename = '%s-s%02d-%s-parallel' % (scenario, simId, resultName)
                if bins:
                    basename += '-%d-bins' % bins
                if quantiles:
                    basename += '-quantiles'
                if invert:
                    basename += '-inverted'

                filename = makePlotPath(basename, simId)

                anaObj.plotParallelCoordinates(inputDF, resultSeries, inputBins=bins,
                                               numInputs=numInputs, outputLabels=outputLabels,
                                               invert=invert, rotation=rotation,
                                               quantiles=quantiles, filename=filename,
                                               extra=filename)
