from __future__ import print_function
from pygcam.matplotlibFix import plt

import pandas as pd
from pandas.plotting import parallel_coordinates
import seaborn as sns

from .analysis import spearmanCorrelation

# get_ipython().magic(u'matplotlib inline')

Feedstocks = ['corn', 'soy', 'sugarcane', 'grass']

def isLinked(colname):
    pos = colname.find('[')
    colname = colname if pos < 0 else colname[0:pos]
    return colname.endswith('-linked')

def getCorrDF(inputs, output):
    corrDF = pd.DataFrame(spearmanCorrelation(inputs, output))
    corrDF['abs'] = corrDF.spearman.abs()
    corrDF.sort_values('abs', ascending=False, inplace=True)
    return corrDF

def normalize(df):
    result = df.copy()
    for name in df.columns:
        mn = df[name].max()
        mx = df[name].min()
        result[name] = (df[name] - mn) / (mx - mn)
    return result

def topContributors(inputs, output, count):
    corrDF = getCorrDF(inputs, output)
    top = list(corrDF.index[:count])
    return top

def importantParams(df, outputs, count):
    result = {key: topContributors(df, outputs[key], count) for key in Feedstocks}
    return result

def extractCols(df, colnames):
    extracted = df[colnames]
    df.drop(extracted.columns, axis=1, inplace=True)
    return extracted

def flipCorrSign(df, colNames, corrDF):
    df = df.loc[:, colNames]
    for name in colNames:
        if corrDF.spearman[name] < 0:
            df[name] = 1 - df[name]
            df.rename(columns={name: "(1 - %s)" % name}, inplace=True)
    return df

def categorizeCI(count, inputDF, title=None, addCount=False):
    largest = inputDF.nlargest(count, 'ci')
    smallest = inputDF.nsmallest(count, 'ci')
    largest['tag'] = 'High CI'
    smallest['tag'] = 'Low CI'
    joined = pd.concat((largest,smallest))
    joined.drop(['ci'], axis=1, inplace=True)

    g = parallel_coordinates(joined, 'tag', color=[[0.8,0,0.1,0.3],[0,0.1,0.8,0.3]])
    plt.xticks(rotation=270)
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    if title:
        if addCount:
            title += ' (n=%d)' % count
        g.set_title(title)
    return g

def categorizeCI2(inputDF, subsampleFactor=10, title=None):
    #inputDF = normalize(inputDF)
    binLabels = ['Low', 'Medium', 'High']
    indices = list(range(0, inputDF.shape[0], subsampleFactor))
    plotDF = inputDF.iloc[indices].copy()
    plotDF['bin'] = pd.qcut(inputDF['ci'], len(binLabels), labels=binLabels)
    plotDF.drop(['ci'], axis=1, inplace=True)
    alpha = 0.3
    g = parallel_coordinates(plotDF, 'bin',
                             color=[[0.8,0.0,0.1,alpha],
                                    [0.0,0.8,0.1,alpha],
                                    [0.1,0.1,0.8,alpha],
                                   ])
    plt.xticks(rotation=270)
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    if title:
        title += ' (factor=%d)' % subsampleFactor
        g.set_title(title)
    return g

def createInputDF(df, topContribs, feedstock):
    inputDF = df[topContribs[feedstock]].copy()
    inputDF['ci'] = ci[feedstock]
    return normalize(inputDF.dropna())


if __name__ == "__main__":
    filename = 'Combined.csv'
    df = pd.read_table(filename, sep=',', index_col='trial')

    linked = list(filter(isLinked, df.columns))
    if linked:
        df.drop(linked, axis=1, inplace=True)

    ci = extractCols(df, Feedstocks)
    contribs = importantParams(df, ci, 5)

    g = sns.boxplot(ci)
    g.axes.set_title('All data')

    categorizeCI2(createInputDF(df, contribs, 'soy'),
                  subsampleFactor=20,
                  title='Soy biodiesel')

    categorizeCI2(createInputDF(df, contribs, 'corn'),
                  subsampleFactor=10,
                  title='Corn ethanol')

    categorizeCI2(createInputDF(df, contribs, 'grass'),
                  subsampleFactor=20,
                  title='Energy grass ethanol')

    categorizeCI2(createInputDF(df, contribs, 'sugarcane'),
                  subsampleFactor=25,
                  title='Sugarcane ethanol')

    categorizeCI(100, createInputDF(df, contribs, 'corn'), title='Corn ethanol', addCount=True)

    cornCorrDF = getCorrDF(df, ci['corn'])
    inputDF = createInputDF(df, contribs, 'corn')
    inputDF = flipCorrSign(inputDF, contribs['corn'], cornCorrDF)
    inputDF['ci'] = ci['corn']
    categorizeCI(100, inputDF, title='Corn ethanol', addCount=True)

    # THIS ISNT QUITE RIGHT
    inputDF = flipCorrSign(inputDF, contribs['corn'], cornCorrDF)
    inputDF



