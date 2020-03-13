'''
Created on Dec 20, 2012

@author: Rich Plevin
@author: Sam Fendell

Copyright (c) 2012-2015. The Regents of the University of California (Regents)
and Richard Plevin. See the file COPYRIGHT.txt for details.

Implements the Latin Hypercube Sampling technique as described by Iman and Conover, 1982,
including correlation control both for no correlation or for a specified correlation
matrix for the sampled parameters.

Heavily modified from http://nullege.com/codes/show/src@m@o@model-builder-HEAD@Bayes@lhs.py
'''
import numpy as np
from scipy import stats
from pandas import DataFrame

def rankCorrCoef(m):
    '''
    Take a 2-D array of values and produce a array of rank correlation
    coefficients representing the rank correlation among the columns.
    '''
    dummy, cols = m.shape
    corrCoef = np.zeros((cols, cols))  # @UndefinedVariable

    for i in range(cols):
        corrCoef[i, i] = 1.  # All columns are perfectly correlated with themselves
        for j in range(i + 1, cols):
            corr = stats.spearmanr(m[:, i], m[:, j])[0]
            corrCoef[i, j] = corrCoef[j, i] = corr

    return corrCoef


def genRankValues(params, trials, corrMat):
    '''
    Generate a data set of 'trials' ranks for 'params'
    parameters that obey the given correlation matrix.

    params: integer denoting number of parameters.

    trials: integer denoting number of trials.

    corrMat: rank correlation matrix for parameters.
    corrMat[i,j] denotes the rank correlation between parameter
    i and j.

    Output is a matrix with 'trials' rows and 'params' columns.
    The i'th column represents the ranks for the i'th parameter.

    So an input with params=3 and trials=6 might output:

    [[1,4,6],
     [2,3,5],
     [4,1,3],
     [6,5,2],
     [5,2,1],
     [3,6,4]]
    '''
    # Create van der Waarden scores
    strata = np.arange(1.0, trials + 1) / (trials + 1)
    vdwScores = stats.norm().ppf(strata)

    S = np.zeros((trials, params))
    for i in xrange(params):
        np.random.shuffle(vdwScores)
        S[:, i] = vdwScores

    P = np.linalg.cholesky(corrMat)

    E = rankCorrCoef(S)
    Q = np.array(np.linalg.cholesky(E))
    final = np.dot(np.dot(S, np.linalg.inv(Q).T), P.T)

    ranks = np.zeros((trials, params), dtype='i')
    for i in xrange(params):
        ranks[:, i] = stats.rankdata(final[:, i])

    return ranks


def getPercentiles(trials=100):
    '''
    Generate a list of 'trials' values, one from each of 'trials' equal-size
    segments from a uniform distribution. These are used with an RV's ppf
    (percent point function = inverse cumulative function) to retrieve the
    values for that RV at the corresponding percentiles.
    '''
    segmentSize = float(1. / trials)
    points = stats.uniform.rvs(size=trials) * segmentSize + np.arange(trials) * segmentSize  # @UndefinedVariable
    return points


def lhs(paramList, trials, corrMat=None, columns=None, skip=None):
    """
    Produce an ndarray or DataFrame of 'trials' rows of values for the given parameter
    list, respecting the correlation matrix 'corrMat' if one is specified, using Latin
    Hypercube (stratified) sampling.

    The values in the i'th column are drawn from the ppf function of the i'th parameter
    from paramList, and each columns i and j are rank correlated according to corrMat[i,j].

    :param paramList: (list of rv-like objects representing parameters) Only requirement
           on parameter objects is that they must implement the ppf function.
    :param trials: (int) number of trials to generate for each parameter.
    :param corrMat: a numpy matrix representing the correlation between the parameters.
           corrMat[i,j] should give the correlation between the i'th and j'th
           entries of paramlist.
    :param columns: (None or list(str)) Column names to use to return a DataFrame.
    :param skip: (list of params)) Parameters to process later because they are
           dependent on other parameter values (e.g., they're "linked"). These
           cannot be correlated.
    :return: ndarray or DataFrame with `trials` rows of values for the `paramList`.
    """
    ranks = genRankValues(len(paramList), trials, corrMat) if corrMat is not None else None

    samples = np.zeros((trials, len(paramList)))  # @UndefinedVariable

    skip = skip or []

    for i, param in enumerate(paramList):
        if param in skip:
            continue    # process later

        values = param.ppf(getPercentiles(trials))  # extract values from the RV for these percentiles

        if corrMat is None:
            # Sequence is a special case for which we don't shuffle (and we ignore stratified sampling)
            if param.param.dataSrc.distroName != 'sequence':
                np.random.shuffle(values)  # randomize the stratified samples
        else:
            indices = ranks[:, i] - 1  # make them 0-relative
            values = values[indices]   # reorder to respect correlations

        samples[:, i] = values

    return DataFrame(samples, columns=columns) if columns else samples

def lhsAmend(df, rvList, trials, shuffle=True):
    """
    Amend the DataFrame with LHS data by adding columns for the given parameters.
    This allows "linked" parameters to refer to values of other parameters.

    :param df: (DataFrame) Generated by prior call to LHS or something similar.
    :param paramList: (list of params) The parameters to fill in the df with
    :param trials: (int) the number of trials to generate for each parameter
    :param shuffle (bool): if True, shuffle the values. Set this to false for
        linked params.
    :return: none
    """
    for rv in rvList:
        values = rv.ppf(getPercentiles(trials))  # extract values from the RV for these percentiles
        if not isinstance(values, np.ndarray):
            values = values.values               # convert pandas Series if needed

        if shuffle:
            np.random.shuffle(values)            # randomize the stratified samples

        param = rv.getParameter()
        paramName = param.getName()
        df[paramName] = values
        #continue
