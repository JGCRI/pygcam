from __future__ import print_function
import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import json
import numpy as np
import pandas as pd
import os
import plotly.figure_factory as ff
import plotly.graph_objs as go
import plotly.subplots as subplots
from scipy import stats

from pygcam.log import getLogger
from pygcam.mcs.analysis import getCorrDF
from pygcam.config import getConfig, DEFAULT_SECTION, getParam, setParam, setSection, getSections
from pygcam.mcs.Database import getDatabase
from pygcam.gui.widgets import dataStore
from pygcam.gui.styles import getColor, getStyle, updateStyle, getFont

_logger = getLogger(__name__)

CORR_STEP = 100

Oct16 = False       # special mode for specific presentation

def projectsWithDatabases():
    withDatabases = []

    for project in getSections():
        dbPath = getParam('MCS.DbPath', section=project, raiseError=False)
        if dbPath and os.path.exists(dbPath):
            withDatabases.append(project)

    return withDatabases

# Render slider labels in a consistent font and size
def sliderLabel(value):
    return {'label': str(value),
            'style': {'font-size': 10, 'font-family': 'Lato'}}

def cached(func):
    """
    Simple decorator to cache results keyed on method args plus project name.
    Note that this is not general purpose, but specialized for the McsData class.
    """
    cache = {}

    #@wraps  # keeps the name and doc string of wrapped function intact
    def wrapper(*args, **kwargs):
        self = args[0]
        key = (func.__name__, self.project, args[1:])

        try:
            return cache[key]
        except KeyError:
            cache[key] = result = func(*args, **kwargs)
            return result

    return wrapper

class McsData(object):
    def __init__(self, app):
        getConfig()

        # include only projects that have MCS databases
        self.projects = projectsWithDatabases()

        self.app = app
        self.db = None
        self.project = None
        self.simId = None
        self.inputs = None
        self.inputsDF = None
        self.resultDict = None
        self.histogramContext = None
        self.paraCoordsVars = None
        self.resetSliderButtonClicks = None
        self.selectedResults = None
        self.corrDF = None

    def readMetaData(self, project=None):
        if project:
            setParam('GCAM.DefaultProject', project, DEFAULT_SECTION)
            setSection(project)
        else:
            project = getParam('GCAM.DefaultProject')

        self.project = project
        self.inputsDF = None
        self.resultDict = None
        self.selectedResults = None
        self.corrDF = None

        self.simId = None

        if self.db:
            self.db.close()

        db = self.db = getDatabase()
        self.inputs = db.getInputs()

    @cached
    def getParameterValues(self, simId):
        db = self.db
        _logger.debug('Reading inputDF...',)
        inputsDF = db.getParameterValues2(simId)

        # Drop any inputs with names ending in '-linked' since they're redundant
        linked = [s for s in inputsDF.columns if s.endswith('-linked')]
        if linked:
            inputsDF = inputsDF.drop(linked, axis=1, inplace=False)

        # Handle special case of ramp-index by rounding to integer
        col = 'ramp-index'
        if col in inputsDF.columns:
            inputsDF[col] = inputsDF[col].apply(round)

        numParams = inputsDF.shape[0] * inputsDF.shape[1]
        _logger.info('%d parameter values read' % numParams)
        return inputsDF

    @cached
    def getOutputsWithValues(self, simId, scenario):
        outputs = self.db.getOutputsWithValues(simId, scenario)
        return outputs

    @cached
    def getOutValues(self, simId, scenario, resultName, limit=None):
        """
        Just a layer over db.getOutValues to provide caching of results, and
        to convert result from a DataFrame to a Series
        """
        df = self.db.getOutValues(simId, scenario, resultName, limit=limit)
        series = df[resultName]

        return series

    def projectChooser(self):
        layout = dcc.Dropdown(id='project-chooser',
                              options=[{'label':name, 'value':name} for name in self.projects],
                              value=getParam('GCAM.DefaultProject'))
        return layout

    def simChooser(self, optionsOnly=False):
        sims = self.db.getSims()
        if sims is None:
            sims = []

        def simLabel(sim):
            desc  = sim.description or '[no description]'
            label = "%d. %s (%d trials)" % (sim.simId, desc, sim.trials)
            return label

        options = [{'label':simLabel(sim), 'value':sim.simId} for sim in sims]

        if optionsOnly:
            return options

        layout = dcc.Dropdown(
            id='sim-chooser',
            options=options,
            value=sims[0].simId if sims else None)
        return layout

    def scenarioChooser(self, simId=None, multi=False, optionsOnly=False):
        scenarios = [] if simId is None else (self.db.scenariosWithResults(simId) or [])
        options = [{'label': s, 'value': s} for s in scenarios]

        if optionsOnly:
            _logger.debug("scenarioChooser returning %s" % options)
            return options

        layout = dcc.Dropdown(
            id='scenario-chooser',
            options=options,
            value=options[0]['value'] if options else '',
            multi=multi
        )
        _logger.debug("scenarioChooser returning %s" % layout)
        return layout

    def inputChooser(self, multi=False, optionsOnly=False):
        options = [{'label': name, 'value': name} for name in self.inputs]

        if optionsOnly:
            return options

        layout = dcc.Dropdown(
            id='input-chooser',
            options=options,
            multi=multi,
            value=[])
        return layout

    def outputChooser(self, simId=None, scenario=None, optionsOnly=False):
        _logger.debug("outputChooser: simId={}, scenario={}".format(simId, scenario))
        outputs = self.getOutputsWithValues(simId, scenario) \
            if scenario and (simId is not None) else []

        options = [{'label': name, 'value': name} for name in outputs]

        if optionsOnly:
            return options

        layout = dcc.Dropdown(
            id='output-chooser',
            options=options,
            multi=False,
            value=options[0]['value'] if options else '')
        return layout

    def multiOutputChooser(self, simId=None, scenario=None, optionsOnly=False):
        outputs = self.getOutputsWithValues(simId, scenario) \
            if scenario and (simId is not None) else []

        options = [{'label': name, 'value': name} for name in outputs]

        if optionsOnly:
            return options

        layout = dcc.Checklist(
            id='multi-output-chooser',
            options=options,
            value=outputs, # pre-select everything
            labelStyle={'display': 'inline-block', 'margin': '6px'})

        return layout

    def distPlot(self, simId, scenario, outputName, sliderInfo, distOptions, selectedData):
        """
        Generate the plot data for the distribution plot. Return three items:
        the plot data, title, and annotations (might be empty list).
        """
        annotations = []
        colors = []

        values = self.getOutValues(simId, scenario, outputName)

        if values is None:
            title = 'Please select a model output to plot'
            plotData = [dict(type='bar', x=[], y=[],
                             name=outputName, showlegend=False,)]
            return plotData, title, annotations

        title = 'Distribution of %s for scenario %s' % (outputName, scenario)

        bins = min(100, len(values)) or 1 # 1 for corner case of no data; bins must be > 0

        # Generate histogram data to be able to color bars directly
        counts, edges = np.histogram(values, bins, density=True)
        barCount = len(counts)

        # Plot the counts on x-axis at the mean of each pair of edges
        barValues = [np.mean(edges[i:i + 1]) for i in range(barCount)]

        if sliderInfo:
            minQ, maxQ = sliderInfo
            minX = values.quantile(q=minQ / 100.0, interpolation='linear')
            maxX = values.quantile(q=maxQ / 100.0, interpolation='linear')
        else:
            minX, maxX = selectedData['range']['x'] if selectedData else (edges[0], edges[-1])

        # Sub-select trials based on selection range to show in parallel coords plot
        self.selectedResults = values[values.between(minX, maxX, inclusive=True)]

        # highlight selected bars by desaturating non-selected items
        active   = getColor('DistBarsActive')
        inactive = getColor('DistBarsInactive')
        for i in range(barCount):
            colors.append(active if minX <= barValues[i] <= maxX else inactive)

        distPlot = ff.create_distplot([values], [outputName], bin_size=1,
                                      show_hist=False, show_rug=False, curve_type='kde')

        # TBD: generalize this
        if outputName == 'percent-change':
            tickvalues = ['%d%%' % int(value) for value in barValues]
        else:
            tickvalues = ['%.2f' % value for value in barValues]

        plotData = [dict(type='bar',
                         x=barValues,
                         y=list(counts),
                         name=outputName,
                         histnorm='probability density',
                         marker=dict(color=colors),
                         showlegend=False,
                         text=tickvalues,
                         hoverinfo='text'
                         )]

        if 'kde' in distOptions:
            distData = distPlot.data[0]
            plotData.append(dict(type='scatter',
                                 x=distData['x'],
                                 y=distData['y'],
                                 marker=dict(color=getColor('KDE')),
                                 hoverinfo='skip', # prevents hover events
                                 showlegend=False,
                                 ))

        showMean = 'mean' in distOptions
        showMedian = 'median' in distOptions

        if showMean or showMedian:
            info = values.describe()
            maxY = max(counts)
            labelSize = 12
            bgcolor = getColor('PlotBg')

            mean   = info['mean']
            median = info['50%']

            def lineData(name, x, maxY, color):
                d = dict(type='scatter', mode='lines',
                         name=name,
                         x=[x, x], y=[0.0000001, maxY],
                         marker=dict(color=color))
                return d

            def notation(x, y, xanchor, color):
                # TBD: generalize this
                if outputName == 'percent-change':
                    text = '%d%%' % x
                else:
                    text = '%.2f' % x

                d = dict(x=x, y=y,
                         text=text,
                         xanchor=xanchor, yanchor='top',
                         showarrow=False,
                         bgcolor=bgcolor, opacity=0.7,
                         font=dict(family='Lato', size=labelSize, color=color))
                return d

            if showMean:
                color = getColor('MeanLineColor')
                xanchor = 'right' if mean <= median else 'left'
                plotData.append(lineData('mean', mean, maxY, color))
                annotations.append(notation(mean, 0.95 * maxY, xanchor, color))

            if showMedian:
                color = getColor('MedianLineColor')
                xanchor = 'right' if median < mean else 'left'
                plotData.append(lineData('median', median, maxY, color))
                annotations.append(notation(median, maxY, xanchor, color))

        return plotData, title, annotations

    @cached
    def getCorrDF(self, simId, scenario, resultName):
        results = self.getOutValues(simId, scenario, resultName)
        inputsDF = self.getParameterValues(simId)
        inputsDF = inputsDF.iloc[results.index]      # select only trials for which we have results

        corrDF = getCorrDF(inputsDF, results)
        return corrDF

    @cached
    def getCorrByTrials(self, simId, scenario, resultName):
        results  = self.getOutValues(simId, scenario, resultName)
        inputsDF = self.getParameterValues(simId)

        # # TBD: a hack to examine failures
        # idx = set(inputsDF.index[:max(results.index)]) - set(results.index)
        # failures = inputsDF.iloc[list(idx)]
        #   failures.to_csv('/Users/rjp/tmp/failures.csv')

        # shuffle the results order (which we use to index the inputs) to avoid
        # artifacts when using pseudo variables
        from random import shuffle
        idx = list(results.index)
        shuffle(idx) # performed in place
        results = results[idx]

        inputsDF = inputsDF.iloc[results.index]      # select only trials for which we have results

        paramsToShow = 10
        fullDF = getCorrDF(inputsDF, results)
        topParams = list(fullDF[:paramsToShow].index)

        colsToDrop = set(inputsDF.columns) - set(topParams)
        inputsDF = inputsDF.drop(colsToDrop, axis=1, inplace=False) # not inplace since it's a slice of the original

        trialSteps = list(range(CORR_STEP, len(results), CORR_STEP))    # produce corrDF for increments of 100 trials
        trialSteps.append(len(results))                                 # final value is for however many trials there were

        corrByTrials = pd.DataFrame()

        for count in trialSteps:
            corrDF = getCorrDF(inputsDF[:count], results[:count])
            corrDF['count'] = count
            corrByTrials = corrByTrials.append(corrDF)

        corrByTrials.reset_index(inplace=True)
        return corrByTrials


    def parcoordsPlot(self, simId, scenario, resultName, numVars):
        if simId is None or not (scenario and resultName):
            return ''

        result   = self.getOutValues(simId, scenario, resultName)
        inputsDF = self.getParameterValues(simId)
        inputsDF = inputsDF.iloc[result.index]      # select only trials for which we have results

        corrDF = self.getCorrDF(simId, scenario, resultName)
        varCount = min(numVars, inputsDF.shape[1])
        varNames = corrDF.index[:varCount]
        self.paraCoordsVars = list(varNames)

        def appendDim(series, name, constraint=None):
            d = dict(range=[round(min(series), 2),
                            round(max(series), 2)],
                     label=name,
                     values=series)

            if constraint:
                # constrain by selection from distribution plot
                d['constraintrange'] = constraint

            dimensions.append(d)

        dimensions = []
        for name in varNames:
            appendDim(inputsDF[name], name)

        selected = self.selectedResults
        appendDim(result, resultName, constraint=[min(selected), max(selected)])

        plotData = [go.Parcoords(
            line=dict(color=result,
                      colorscale='Jet',
                      showscale=True,
                      reversescale=False,
                      cmin=min(result),
                      cmax=max(result)),
            dimensions=dimensions,
            rangefont={'color': 'rgba(255,0,0,0)'}, # zero alpha => invisible
            )]

        layout = dict(autosize=True,
                      height=500,
                      margin=dict(l=75, r=40, b=35, t=35),
                      hovermode="closest",
                      title='',
                      showlegend=False,
                      legend=dict(font=dict(size=10), orientation='h'),
                      )
        figure = dict(data=plotData, layout=layout)
        return figure

    def tornadoPlot(self, simId, scenario, resultName, tornadoType,
                    sliderValue, selectedData):
        corrDF = self.getCorrDF(simId, scenario, resultName)

        if tornadoType == 'normalized':
            squared = corrDF.spearman ** 2
            corrDF['normalized'] = squared / squared.sum()
            corrDF['sign'] = 1
            corrDF.ix[(corrDF.spearman < 0), 'sign'] = -1
            corrDF['value'] = corrDF.normalized * corrDF.sign     # normalized squares with signs restored
            plotColumn = 'value'
            title = 'Normalized rank correlation'
        else:
            plotColumn = 'spearman'
            title = 'Rank correlation'

        title += ' of {} for scenario {}'.format(resultName, scenario)

        varCount = min(20, len(corrDF)) # if sliderValue is None else len(corrDF[corrDF['abs'] >= sliderValue]))
        varNames = list(reversed(corrDF.index[:varCount]))
        values   = list(reversed(corrDF[plotColumn][:varCount]))

        plotData = go.Bar(
            orientation='h',
            x=values,
            y=varNames,
            width=0.6,
            marker=dict(
                color=getColor('TornadoPlotBar'),
                line=dict(
                    color=getColor('TornadoPlotLine'),
                    width=0),
            ),

            textposition='none',
            name='Rank correlation',
            hoverinfo='skip', # prevents hover events
        )

        layout = updateStyle('Plot',
                             title=title,
                             margin=updateStyle('PlotMargin', l=300),
                             xaxis=dict(range=[-1, 1]),
                             dragmode='select')

        figure = dict(data=[plotData], layout=layout)
        return figure

    def corrConvergencePlot(self, simId, scenario, resultName):
        df = self.getCorrByTrials(simId, scenario, resultName)
        params = list(df['paramName'].unique())
        traces = []

        count = max(df['count'])

        # create a trace for each parameter
        for paramName in params:
            paramData = df.query('paramName == "%s"' % paramName)

            trace = go.Scatter(x=list(paramData['count']),
                               y=list(paramData['spearman']),
                               name=paramName, mode='lines')
            traces.append(trace)

        # Round up to nearest integral value of CORR_STEP
        endX = count + (CORR_STEP - count % CORR_STEP)

        # I cannot center a narrower plot for reasons I don't understand
        layout = updateStyle('Plot',
                             width=None,
                             title='Correlation Convergence for %s' % resultName,
                             xaxis=dict(range=[CORR_STEP, endX]))
                             # margin=updateStyle('PlotMargin', l=40)

        figure = dict(data=traces, layout=layout)
        return figure

    def scatterPlots(self, simId, scenario, inputs, outputs):
        """
        Plot a set of small scatterplots showing correlation between chosen
        model inputs and outputs.

        :param simId: (int) simulation id
        :param scenario: (str) scenario name
        :param inputs: (iterable of str) names of inputs to plot
        :param outputs: (iterable of str) names of outputs to plot

        :return: dash 'figure' data.
        """
        allInputs = self.getParameterValues(simId)
        inputsDF  = allInputs[inputs]

        outputsDF = pd.DataFrame(columns=outputs)
        for output in outputs:
            outputsDF[output] = self.getOutValues(simId, scenario, output)

        inputsDF = inputsDF.iloc[outputsDF.index]      # select only trials for which we have results

        numIns  = len(inputs)
        numOuts = len(outputs)
        fig = subplots.make_subplots(rows=numOuts, cols=numIns,
                                     vertical_spacing=0.01,
                                     shared_xaxes=True,
                                     shared_yaxes=True,
                                     column_titles=inputs,
                                     row_titles=outputs,
                                     )

        for ann in fig['layout']['annotations']:
            ann['font'] = dict(size=10)

        layout = fig['layout']
        for row, output in enumerate(outputs):
            yAxisNum = row + 1
            xAxisNum = 0

            for col, input in enumerate(inputs):
                xAxisNum += 1

                trace = go.Scatter(
                    x=inputsDF[input],
                    y=outputsDF[output],
                    hoverinfo='skip',       # don't show or fire events
                    mode='markers',
                    marker=dict(size=1,
                                opacity=0.9,
                                color=getColor('ScatterPoints'))
                )

                fig.add_trace(trace, row+1, col+1)

                # Compute the names of the corresponding axes
                # xaxis = "xaxis{}".format(xAxisNum)
                # yaxis = "yaxis{}".format(yAxisNum)

        fig.update_xaxes(showgrid=False, zeroline=False)
        fig.update_yaxes(showgrid=False, zeroline=False)

        layout.update(margin=dict(l=50, r=30, t=30, b=30),
                      height=140 * numOuts + 20,
                      #width= 130 * numIns,
                      showlegend=False,
                      font=dict(size=9,
                                family=getFont('PlotText')))
        return fig

    def distributionSectionLayout(self):
        # slider, distribution, checklist
        layout = [
            html.P([
                html.Span('Filter using the percentile slider or select a range in the histogram. Selected range: '),
                html.Span(id='percentile-text')
            ], style=getStyle('HelpText')),

            html.Div([
                html.Div([
                    dcc.RangeSlider(
                        id='dist-slider',
                        min=0,
                        max=100,
                        step=0.1,
                        marks={percentile: sliderLabel(str(percentile) + '%') for percentile in range(0, 101, 10)},
                        # marks={percentile: str(percentile) + '%' for percentile in range(0, 101, 10)},
                        # updatemode='drag', # too slow redrawing parcoords
                        value=[0, 100]),
                ], style={'width': '350px',
                          'display': 'inline-block'
                         }
                ),

                # gap between slider and button
                html.Div(' ',
                         style={'width': '10px', 'display': 'inline-block'}),

                html.Div([
                    html.Button('Reset',
                                id='dist-slider-reset-button',
                                style=getStyle('Button')
                                )
                ], style={'width': '55px',
                          'display': 'inline-block'})

            ], style={'margin-left': '10px'}),

            html.Div(
                dcc.Graph(id='distribution'),
                style={'margin-top': '20px'}),

            dcc.Checklist(
                id='dist-options',
                options=[{'label': 'KDE', 'value': 'kde'},
                         {'label': 'Mean', 'value': 'mean'},
                         {'label': 'Median', 'value': 'median'}],
                value=['kde'],
                labelStyle={'display': 'inline-block',
                            'margin': '6px'})
        ]

        return layout

    def tornadoSectionLayout(self):
        layout = [

            html.P([
                html.Span('Adjust the number of variables to show by setting the correlation cut-off'),
                html.Span(id='corr-cutoff-text')
            ], style=updateStyle('HelpText', display='none')),   # getStyle('HelpText')),

            html.Div([
                html.Div([
                    dcc.Slider(
                        id='tornado-slider',
                        disabled=True,
                        min=0, max=0.4, step=0.01,
                        marks={value: sliderLabel(value) for value in np.arange(0, 0.4, 0.1)},
                        updatemode='drag',
                        value=0.01),
                ], style={
                    'width': 300,
                    # 'display': 'inline-block'
                    'display': 'none'
                    }
                ),
            ]),

            html.Div(
                dcc.Graph(id='tornado'),
                style={'margin-top': 74}),  # 20}),

            dcc.RadioItems(
                id='tornado-type-chooser',
                options=[{'label': 'Rank correlation',
                          'value': 'spearman'},
                         {'label': 'Normalized',
                          'value': 'normalized'}],
                value='normalized',
                labelStyle={'display': 'inline-block', 'margin': '6px'})
        ]
        return layout

    def layout(self):
        layout = html.Div([
            dataStore(id='paraCoords-vars'),
            dataStore(id='dist-selected'),

            html.H1('Monte Carlo Simulation Explorer', className='title'),
            html.Table([
                html.Tr([
                    html.Th('Project'),
                    html.Th('Simulation'),
                    html.Th('Scenario'),
                    html.Th('Model Output'),
                ]),
                html.Tr([
                    html.Td(self.projectChooser()),
                    html.Td(self.simChooser()),
                    html.Td(self.scenarioChooser()),
                    html.Td(self.outputChooser())
                ])

            ], style={'width': '100%',
                      'border': '1px solid black',
                      'table-layout': 'fixed',
                      'background-color': getColor('ChooserBgColor')}),

            html.Div([
                # distribution cluster and tornado chart
                html.Div([
                    html.Div(self.distributionSectionLayout(),
                             className='cell twocol'),

                    html.Div(self.tornadoSectionLayout(),
                             className='cell twocol')
                ], className='row'),

                # parallel coordinates section
                html.Div([
                    html.Div([
                        html.P(['Brush vertically over ranges to filter; click outside the selected range to reset. ',
                                'Drag variable names below to reorder. Slider sets the number of vars to plot'],
                           style=getStyle('HelpText')),

                        html.Div([
                            dcc.Slider(
                                id='paraCoords-slider',
                                min=1, max=10, step=1,
                                marks={value: sliderLabel(value) for value in range(1, 11, 1)},
                                updatemode='drag',
                                value=6),
                        ], style={'margin-bottom': 30,
                                  'margin-left':  'auto',
                                  'margin-right': 'auto',
                                  'width': 400}),

                        html.Div(dcc.Graph(id='paraCoords')),

                    ], className='cell onecol')
                ], className='row'),

                # Correlation convergence section
                html.Div([
                    html.Div([
                        html.Span('Correlation convergence', style=getStyle('Label')),
                        html.Div('', style={'height': 15}),
                        html.Div(dcc.Graph(id='corr-convergence')),
                    ], className='cell onecol')
                ], className='row'),

                # Scatterplot section
                html.Div([
                    html.Div([
                        html.Div([
                            html.Div(style={'height': 15}),
                            html.Span('Model Inputs (random variables)', style=getStyle('Label')),
                            html.Div(style={'height': 15}),
                            self.inputChooser(multi=True)
                        ], style=updateStyle('Chooser', width=900)),

                        html.Div(style={'height':15}),

                        html.Div([
                            html.Span('Model Outputs', style=getStyle('Label')),
                            self.multiOutputChooser()
                        ], style=updateStyle('Chooser', width=900)),

                        html.Div([
                            html.Button('Create scatterplot',
                                        id='scatterplot-button',
                                        style=getStyle('Button')
                                        )
                        ], style={'margin': '5px'}),

                        html.Div([
                            dcc.Graph(id='scatter-matrix')
                        ], style=updateStyle('AutoMargins'))
                    ], className='cell onecol')
                ], className='row'),

            ], className='table',
                style={'width': 1200,
                       'margin-left': 'auto',
                       'margin-right': 'auto'}),

        ], style=getStyle('Page'))

        return layout

# getTimeSeries(self, simId, paramName, expList)


def generateDropdownDefaults(app, ids):
    """
    Generate dropdown default-setting using the 'callback' decorator function.

    :param app: a Dash app instance
    :param ids: (list(str)) ids of Dropdown controllers to generate callbacks for.
    :return: none
    """
    def dropdownDefault(options, current):
        if not options:
            return ''

        optionValues = [opt['value'] for opt in options]

        # if current value is legit, leave it, otherwise choose first item
        return current if current in optionValues else optionValues[0]

    for id in ids:
        _logger.debug("Generating default-setting callback for %s" % id)
        app.callback(Output(id, 'value'),
                     [Input(id, 'options')],
                     state=[State(id, 'value')])(dropdownDefault)

def _setup_werkzeug_log(level, host, port):
    import logging

    consoleFormat = getParam('GCAM.LogConsoleFormat')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(consoleFormat))
    log = logging.getLogger('werkzeug')
    log.addHandler(handler)
    log.setLevel(level)
    log.propagate = False

    # Setting Flask.LogLevel > INFO quashes this useful message, so we restore it
    if log.level > logging.INFO:
        print('* Running on http://{}:{}/ (Press CTRL+C to quit)'.format(host, port))


def main(args):
    app = dash.Dash(name='mcs-explorer')

    level = getParam('Flask.LogLevel')
    flaskLog = app.server.logger
    flaskLog.setLevel(level)
    _setup_werkzeug_log(level, args.host, args.port)

    # app.config.suppress_callback_exceptions = True
    app.css.config.serve_locally = False
    app.css.append_css({"external_url": "https://fonts.googleapis.com/css?family=Dosis:regular,bold|Lato"})
    app.css.append_css({"external_url": "https://codepen.io/plevin/pen/MvpeNV.css"})

    data = McsData(app)
    data.readMetaData()

    app.layout = data.layout()

    #
    # Callbacks
    #
    generateDropdownDefaults(app, ['scenario-chooser', 'output-chooser'])


    @app.callback(Output('output-chooser', 'options'),
                  [Input('project-chooser', 'value'),
                   Input('sim-chooser', 'value'),
                   Input('scenario-chooser', 'value')])
    def updateOutputChooser(project, simId, scenario):
        _logger.debug('updateOutputChooser(%s, %s, %s)' % (project, simId, scenario))
        layout = data.outputChooser(simId=simId, scenario=scenario, optionsOnly=True)
        return layout

    @app.callback(Output('multi-output-chooser', 'options'),
                  [Input('project-chooser', 'value'),
                   Input('sim-chooser', 'value'),
                   Input('scenario-chooser', 'value')])
    def updateMultiOutputChooser(project, simId, scenario):
        _logger.debug('updateMultiOutputChooser(%s, %s, %s)' % (project, simId, scenario))
        layout = data.multiOutputChooser(simId=simId, scenario=scenario, optionsOnly=True)
        return layout

    @app.callback(Output('scenario-chooser', 'options'),
                  [Input('project-chooser', 'value'),
                   Input('sim-chooser', 'value')])
    def updateScenarioChooser(project, simId):
        _logger.debug('updateScenarioChooser(%s, %s)' % (project, simId))
        layout = data.scenarioChooser(simId, multi=False, optionsOnly=True)

        return layout

    @app.callback(Output('sim-chooser', 'options'),
                  [Input('project-chooser', 'value')])
    def updateSimChooser(project):
        _logger.debug('updateSimChooser(%s)' % project)
        data.readMetaData(project)
        layout = data.simChooser(optionsOnly=True)
        return layout

    # TBD: finish writing these methods to store data in hidden div for
    # TBD: reset button and selection to simplify callback for drawing dist

    #
    # The next few callbacks use a hidden <div> to store
    # communicate the variables used in the parallel coords
    # figure with those in the output chooser.
    #

    @app.callback(Output('paraCoords-vars', 'children'),
                  [Input('paraCoords', 'figure')])
    def updateParaCoordsVars(figure):
        varNames = data.paraCoordsVars
        _logger.debug('updateParaCoordsVars vars=%s' % varNames)
        varNamesJSON = json.dumps(varNames)
        return varNamesJSON

    @app.callback(Output('input-chooser', 'value'),
                  [Input('paraCoords-vars', 'children')])
    def updateInputChooser(varNamesJSON):
        varNames = json.loads(varNamesJSON)
        _logger.debug('updateInputChooser(%s)' % varNames)
        return varNames

    @app.callback(Output('paraCoords', 'figure'),
                  [Input('project-chooser', 'value'),
                   Input('sim-chooser', 'value'),
                   Input('scenario-chooser', 'value'),
                   Input('output-chooser', 'value'),
                   Input('paraCoords-slider', 'value'),
                   Input('distribution', 'figure'),     # force this to plot last
                   ])
    def showParallelCoords(project, simId, scenario, resultName, varsToShow, figure):
        return data.parcoordsPlot(simId, scenario, resultName, varsToShow)

    @app.callback(Output('percentile-text', 'children'),
                  [Input('dist-slider', 'value')])
    def showDistSliderValues(sliderInfo):
        return '%d%%-%d%%' % tuple(sliderInfo)

    @app.callback(Output('tornado', 'figure'),
                  [Input('project-chooser', 'value'),
                   Input('sim-chooser', 'value'),
                   Input('scenario-chooser', 'value'),
                   Input('output-chooser', 'value'),
                   Input('tornado-slider', 'value'),
                   Input('tornado-type-chooser', 'value'),
                   Input('distribution', 'selectedData'),
                  ])
    def showTornado(project, simId, scenario, resultName,
                    sliderValue, tornadoType, selectedData):
        _logger.debug('showTornado(%s, %s, %s, %s, %s, %s, %s)' % (
            project, simId, scenario, resultName, sliderValue, tornadoType, selectedData))

        if not (project and scenario and resultName) or simId is None:
            return ''

        figure = data.tornadoPlot(simId, scenario, resultName, tornadoType,
                                  sliderValue, selectedData)
        return figure

    @app.callback(Output('distribution', 'figure'),
                  [Input('project-chooser', 'value'),
                   Input('sim-chooser', 'value'),
                   Input('scenario-chooser', 'value'),
                   Input('output-chooser', 'value'),
                   Input('dist-slider', 'value'),
                   Input('dist-options', 'value'),
                   Input('distribution', 'selectedData'),
                   ])
    def showDistribution(project, simId, scenario, outputName, sliderInfo, distOptions, selectedData):
        _logger.debug('showDistribution(%s, %s, %s, %s, %s)' % (
            project, simId, scenario, outputName, selectedData))

        # Clear selectedData if context changes
        context = (project, simId, scenario, outputName)
        if not data.histogramContext or context != data.histogramContext:
            _logger.debug('showDistribution: clearing context')
            selectedData = sliderInfo = None
            data.histogramContext = context

        # if called before values are known, return an empty plot
        if not (project and scenario and outputName) or simId is None:
            plotData = {'x': []}
            title = 'Please select a model output to plot'
            annotations = None
        else:
            plotData, title, annotations = data.distPlot(simId, scenario, outputName,
                                                         sliderInfo, distOptions,
                                                         selectedData)
        # TBD: generalize this
        if Oct16:
            if outputName == 'percent-change':
                xtitle = 'Change from baseline fuel'
                xticksuffix = '%'
            else:
                # latex formatting is broken, but HTML works fine
                # xtitle = '$g CO_2 MJ^{-1}$' if Oct16 else ''
                xtitle = 'g CO<sub>2</sub> MJ<sup>-1</sup>'
                xticksuffix = None
        else:
            xtitle = data.db.getOutputUnits(outputName)
            xticksuffix = ''

        layout = updateStyle('Plot',
                             title=title,
                             yaxis={'title': 'Probability density',
                                    'tickvals': []
                                    },
                             xaxis={'title': xtitle,
                                    'ticksuffix': xticksuffix,
                                    },
                             margin=getStyle('PlotMarginWithXTitle'),
                             dragmode='select',
                             showLegend=True,
                             legend=dict(x=0.0, y=1.0, bgcolor=getColor('PlotBg')))

        if annotations:
            layout['annotations'] = annotations

        figure = dict(data=plotData, layout=layout)
        return figure

    # dist -> dist slider
    @app.callback(Output('dist-slider', 'value'),
                  [Input('output-chooser', 'value'),
                   Input('distribution', 'selectedData'),
                   Input('dist-slider-reset-button', 'n_clicks')],
                  [State('sim-chooser', 'value'),
                   State('scenario-chooser', 'value')])
    def showPercentileSlider(resultName, selected, clicks, simId, scenario):
        _logger.debug('showPercentileSlider(%s, %s, %s)' % (resultName, selected, clicks))
        if clicks != data.resetSliderButtonClicks:            # recognize a new click
            data.resetSliderButtonClicks = clicks
            return (0, 100)

        if not selected or not resultName:
            return (0, 100)

        minX, maxX = selected['range']['x']
        values = data.getOutValues(simId, scenario, resultName)
        minQ = stats.percentileofscore(values, minX)
        maxQ = stats.percentileofscore(values, maxX)
        return [minQ, maxQ]

    # scatterplot matrix
    @app.callback(Output('scatter-matrix', 'figure'),
                  [Input('scatterplot-button', 'n_clicks')],
                  [State('sim-chooser', 'value'),
                   State('scenario-chooser', 'value'),
                   State('multi-output-chooser', 'value'),
                   State('input-chooser', 'value')])
    def showScatterMatrix(nclicks, simId, scenario, outputs, inputs):
        inputs = inputs or data.paraCoordsVars
        #outputs = outputs or data.getOutputsWithValues(simId, scenario)
        _logger.debug('showScatterMatrix(%s, %s, %s, %s)' % (simId, scenario, inputs, outputs))

        if not inputs or not outputs:
            return ''

        figure = data.scatterPlots(simId, scenario, inputs, outputs)
        return figure

    if True:
        # TBD: not needed in all cases; restore this as option later
        # correlation convergence plot
        @app.callback(Output('corr-convergence', 'figure'),
                      [Input('project-chooser', 'value'),
                       Input('sim-chooser', 'value'),
                       Input('scenario-chooser', 'value'),
                       Input('output-chooser', 'value')])
        def showCorrConvergence(project, simId, scenario, resultName):
            if not (project and scenario and resultName) or simId is None:
                return ''

            figure = data.corrConvergencePlot(simId, scenario, resultName)
            return figure

    app.run_server(debug=args.debug, threaded=False, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
