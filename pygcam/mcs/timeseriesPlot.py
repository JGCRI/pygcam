# -*- coding: utf-8 -*-
"""
Created on Thu Jul 24 18:51:21 2014

@author: Ryan Jones

Copyright (c) 2014 Ryan Jones and Richard Plevin.
See the file COPYRIGHT.txt for details.
"""
import numpy as np
from pygcam.matplotlibFix import plt
import pandas as pd
import seaborn as sns

from . import tsplotModified as tsm
from .analysis import printExtraText

# TBD: Generalize this when integrating into pygcam
def plotForcingSubplots(tsdata, filename=None, ci=95, cum_rf=False, show_figure=False, save_fig_kwargs=None):
    sns.set()
    sns.set_context('paper')
    expList = tsdata['expName'].unique()

    nrows = 1
    ncols = len(expList)
    width  = 2.5 * ncols
    height = 2.5
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, sharey=True, figsize=(width, height))

    def dataForExp(expName):
        df = tsdata.query("expName == '%s'" % expName).copy()
        df.drop(['expName'], axis=1, inplace=True)
        df = pd.melt(df, id_vars=['runId'], var_name='year')
        return df

    for ax, expName in zip(axes, expList):
        df = dataForExp(expName)

        if cum_rf:
            df = df.groupby(by=['runId', 'year']).sum().groupby(level=[0]).cumsum().reset_index()

        pos = expName.find('-')
        title = expName[:pos] if pos >= 0 else expName
        ax.set_title(title.capitalize())

        tsm.tsplot(df, time='year', unit='runId', value='value', ci=ci, ax=ax)

        ylabel = 'W m$^{-2}$' if ax == axes[0] else ''
        ax.set(xlabel='', ylabel=ylabel) # eliminate xlabel "year"
        ax.axhline(0, color='gray', linewidth=0.5, linestyle='-')
        plt.setp(ax.get_xticklabels(), rotation=270)

    plt.tight_layout()

    # Save the file
    if filename:
        if isinstance(save_fig_kwargs, dict):
            fig.savefig(filename, **save_fig_kwargs)
        else:
            fig.savefig(filename)

    # Display the figure
    if show_figure:
        plt.show()

    return fig


def plotTimeSeries(datasets, timeCol, unit, valueCol='value', estimator=np.mean, estimator_linewidth=1.5,
                   ci=90, legend_loc='upper left', legend_labels=None, legend_name=None, title=None,
                   xlabel=None, ylabel=None, label_font=None, title_font=None, xlim=None, ylim=None,
                   ymin=None, ymax=None, text_label=None, show_figure=True, filename=None,
                   save_fig_kwargs=None, figure_style='darkgrid', palette_name=None, extra=None):
    """
    Plot one or more timeseries with flexible representation of uncertainty.

    This function can take a single ndarray array or a list of ndarray arrays
    and plot them against time (years) with a specified confidence interval.

    Parameters
    ----------
    datasets : ndarray, dataframe, or list of ndarrays or dataframes
        Data for the plot. Rows represent samples, columns represent years
    years : series-like
        x values for a plot when data is an array.
    estimator : function
        Function operates column wise on the datasets to produce each line in the figure
    ci : float or list of floats in [0, 100]
        Confidence interval size(s). If a list, it will stack the error
        plots for each confidence interval. Only relevant for error styles
        with "ci" in the name.
    legend_loc : String or float
        Location of the legend on the figure
    legend_labels : string or list of strings
        Either the name of the field corresponding to the data values in
        the data DataFrame (i.e. the y coordinate) or a string that forms
        the y axis label when data is an array.
    legend_name : string
        Legend title.
    title : string
        Plot title
    xlabel : string
        x axis label
    ylabel : string
        y axis label
    text_label : string or list of strings
        if a list of strings, each string gets put on a separate line
    show_figure : bool
        Boolean indicating whether figure should be shown
    filename : string
        Filename used in saving the figure
    save_fig_kwargs : dict
        Other keyword arguments are passed to savefig() call
    figure_style :
        Seaborn figure background styles, options include:
        darkgrid, whitegrid, dark, white
    palette_name : seaborn palette
        Palette for the main plots and error representation

    Returns
    -------
    fig : matplotlib figure

    """

    # Set plot style
    sns.set_style(figure_style)

    # Set up dataset
    if legend_labels is None:
        legend_labels = [None]*len(datasets)
        legend = False
    else:
        legend = True

    if isinstance(legend_labels, str):
        legend_labels = [legend_labels]

    if isinstance(datasets, np.ndarray) or isinstance(datasets, pd.DataFrame):
        datasets = [datasets]

    # Colors
    #colors = sns.color_palette(name=palette_name, n_colors=len(datasets))      # strangely claims name is not a known keyword.
    colors = sns.color_palette(n_colors=len(datasets))

    # Create the plots
    #if fig is None:
    fig, ax = plt.subplots()

    # TBD: this is probably ok, but shouldn't save if a subplot, i.e., if fig & ax were passed in
    for color, data, series_name in zip(colors, datasets, legend_labels):
        tsm.tsplot(data, time=timeCol, value=valueCol, unit=unit, ci=ci, ax=ax, color=color,
                   condition=series_name, estimator=estimator, linewidth=estimator_linewidth)
        # standard version computes CI with different semantics
        #sns.tsplot(data, time=timeCol, value=valueCol, unit=unit, ci=ci, ax=ax, color=color,
        #           condition=series_name, estimator=estimator, linewidth=estimator_linewidth)

    # Add the plot labels
    if label_font is None:
        label_font = dict()
    label_font.setdefault('size', 'medium')

    if title_font is None:
        title_font = dict()
    title_font.setdefault('size', 'large')

    if xlabel is not None:
        ax.set_xlabel(xlabel, fontdict=label_font)

    if ylabel is not None:
        ax.set_ylabel(ylabel, fontdict=label_font)

    if title is not None:
        ax.set_title(title, fontdict=title_font)

    printExtraText(fig, extra, color='grey', loc='right')

    if text_label is not None:
        axis = ax.axis()
        if not isinstance(text_label, str):
            text_label = '\n'.join(text_label)
        ax.text(axis[0]+(axis[1]-axis[0])*.03, axis[2]+(axis[3]-axis[2])*.7, text_label, fontdict=label_font)

    if legend:
        legend1 = ax.legend(loc=legend_loc, title=legend_name, prop={'size': 'medium'})

    for label in (ax.get_xticklabels() + ax.get_yticklabels()):
        label.set(fontsize='medium')

    # Axis limits
    if xlim is not None:
        ax.set_xlim(xlim[0], xlim[1])

    if ymin is not None or ymax is not None:
        ax.set_autoscale_on(False)
        ax.set_ylim(ymin, ymax)

    elif ylim is not None:
        ax.set_ylim(ylim[0], ylim[1])

    # Save the file
    if filename:
        if isinstance(save_fig_kwargs, dict):
            fig.savefig(filename, **save_fig_kwargs)
        else:
            fig.savefig(filename)

    # Display the figure
    if show_figure:
        plt.show()

    return fig
