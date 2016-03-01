#! /usr/bin/env python
'''
Created on 1/19/16

@author: rjp

Functions common to constraint-generation scripts.
'''
import os
import pandas as pd

DefaultYears = '2020-2050'
DefaultCellulosicCoefficients = "2010:2.057,2015:2.057,2020:2.057,2025:2.039,2030:2.021,2035:2.003,2040:1.986,2045:1.968,2050:1.950,2055:1.932,2060:1.914"

# A list of these is inserted as {constraints} in the metaTemplate
_ConstraintTemplate = '                <constraint year="{year}">{value}</constraint>'

_MetaTemplate = '''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
	<output-meta-data>
		<summary>
		  This is a generated constraint file. Edits will be overwritten!
		  {summary}
        </summary>
	</output-meta-data>
	<world>
		<region name="{region}">
			<{policy} name="{name}">
				<market>{market}</market>
				{preConstraint}
{constraints}
			</{policy}>
		</region>
    </world>
</scenario>
'''

OTAQ_CASE = '''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
    <world>
        <region name="USA">
            <ghgpolicy name="ElecCO2">
                <market>USA</market>
                <fixedTax year="2015">0</fixedTax>
                <constraint year="2020">583</constraint>
                <constraint year="2025">512</constraint>
                <constraint year="2030">442</constraint>
                <constraint year="2035">442</constraint>
                <constraint year="2040">442</constraint>
                <constraint year="2045">442</constraint>
                <constraint year="2050">442</constraint>
            </ghgpolicy>
        </region>
    </world>
</scenario>
'''

# To generate the above:
#
# generateConstraintXML('ElecCO2', pd.Series({'2020':583, '2025':512, '2030':442, '2035':442,
#                                             '2040':442, '2045':442, '2050':442,}),
#                       policy='ghgpolicy', region='USA', market='USA',
#                       preConstraint='<fixedTax year="2015">0</fixedTax>')

DEFAULT_POLICY = 'policy-portfolio-standard'
DEFAULT_REGION = 'USA'
DEFAULT_MARKET = 'USA'

def generateConstraintXML(name, series, policy=DEFAULT_POLICY, policyType=None,
                          region=DEFAULT_REGION, market=DEFAULT_MARKET,
                          preConstraint=None, summary=''):

    def genConstraint(year):
        constraint = _ConstraintTemplate.format(year=year, value="{year%s}" % year)
        return constraint

    # Is this the most common case?
    if policyType and not preConstraint:
        preConstraint = '<policyType>{policyType}</policyType>'.format(policyType=policyType)

    constraints = map(genConstraint, series.index)
    constraintText = '\n'.join(constraints)

    template = _MetaTemplate.format(name=name, policy=policy, policyType=policyType, region=region,
                                    market=market, summary=summary, constraints=constraintText)

    args = {'year' + col: value for col, value in series.iteritems()}
    xml = template.format(**args)
    return xml


def yearCols(years, timestep=5):
    """
    Generate a list of names of year columns in GCAM result files from a
    string indicating a year range.
    :param years: a string of the form "2020-2050"
    :param timestep: the number of years between timesteps
    :return: the names of the corresponding columns
    """
    try:
        yearRange = map(int, years.split('-'))
        if not len(yearRange) == 2:
            raise Exception
    except:
        raise Exception('Years must be specified as two years separated by a hyphen, as in "2020-2050"')

    cols = map(str, range(yearRange[0], yearRange[1]+1, timestep))
    return cols

def mkdirs(newdir):
    'Try to create the full path and ignore error if it already exists'
    from errno import EEXIST

    try:
        os.makedirs(newdir, 0775)
    except OSError, e:
        if e.errno != EEXIST:
            raise

def batchDir(baseline, resultsDir, fromMCS=False):
    leafDir = 'queryResults' if fromMCS else 'batch-{baseline}'.format(baseline=baseline)
    pathname = '{resultsDir}/{baseline}/{leafDir}'.format(resultsDir=resultsDir, baseline=baseline, leafDir=leafDir)
    return pathname

def readGcamCsv(filename, skiprows=1):
    'Syntactic sugar: just adds comma separator and no index to create DF'
    print "    Reading", filename
    try:
        df = pd.read_table(filename, sep=',', skiprows=skiprows, index_col=None)
        return df
    except IOError, e:
        print "    ERROR: failed to read " + filename
        raise

def readQueryResult(batchDir, baseline, queryName):
    '''
    Compose the name of the 'standard' result file, read it into a DF and return the DF.
    '''
    pathname = os.path.join(batchDir, '%s-%s.csv' % (queryName, baseline))
    df= readGcamCsv(pathname)
    return df

def saveToFile(txt, dirname, filename):
    mkdirs(dirname)
    pathname = os.path.join(dirname, filename)
    print "    Generating file:", pathname
    with open(pathname, 'w') as f:
        f.write(txt)

def saveConstraintFile(xml, dirname, constraintName, policyType, scenario, subdir='', fromMCS=False):
    basename = '%s-%s' % (constraintName, policyType)
    constraintFile = basename + '-constraint.xml'
    policyFile     = basename + '.xml'

    dirname = os.path.join(dirname, subdir, scenario)
    mkdirs(dirname)

    pathname = os.path.join(dirname, constraintFile)
    print "    Generating constraint file", pathname
    with open(pathname, 'w') as f:
        f.write(xml)

    # compute relative location of local-xml directory
    levels = 2
    levels += 2 if fromMCS else 0
    levels += 1 if subdir else 0

    localxml = '../' * levels + 'local-xml'

    source   = os.path.join(localxml, subdir, scenario, policyFile)
    linkname = os.path.join(dirname, policyFile)

    print "    Linking to", source
    if os.path.lexists(linkname):
        os.remove(linkname)
    os.symlink(source, linkname)

def parseStringPairs(argString, datatype=float):
    """
    Convert a string of comma-separated pairs of colon-delimited values to
    a pandas Series where the first value of each pair is the index name and
    the second value is a float, or the type given.
    """
    pairs = argString.split(',')
    dataDict = {year:datatype(coef) for (year, coef) in map(lambda pair: pair.split(':'), pairs)}
    coefficients = pd.Series(data=dataDict)
    return coefficients

def printSeries(series, label):
    df = pd.DataFrame(series)  # DF is more convenient for printing
    df.columns = [label]
    pd.set_option('precision', 5)
    print df.T


if __name__ == '__main__':
    xml = generateConstraintXML('myPolicy', [2010,2015,2020,2030], 'tax', market='global', summary='This is a test case.')
    print xml
