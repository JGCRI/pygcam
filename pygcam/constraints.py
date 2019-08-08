#! /usr/bin/env python
'''
.. Created on 4/26/15
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.

'''
from .config import pathjoin
from .constants import LOCAL_XML_NAME
from .log import getLogger
from .query import readQueryResult
from .utils import mkdirs, getBatchDir, getYearCols, printSeries

_logger = getLogger(__name__)

PolicyChoices = ['tax', 'subsidy']
DefaultYears = '2020-2050'
DefaultCellulosicCoefficients = "2010:2.057,2015:2.057,2020:2.057,2025:2.039,2030:2.021,2035:2.003,2040:1.986,2045:1.968,2050:1.950,2055:1.932,2060:1.914"

# A list of these is inserted as {constraints} in the metaTemplate
_ConstraintTemplate = '                <constraint year="{year}">{value}</constraint>'

_MetaTemplate = '''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
    <!--
    This is a generated constraint file. Edits will be overwritten!
    {summary}
    -->
    <world>
        <region name="{region}">
            <{gcamPolicy} name="{name}">
                <market>{market}</market>
                {preConstraint}
{constraints}
           </{gcamPolicy}>
        </region>
    </world>
</scenario>
'''

DEFAULT_POLICY = 'policy-portfolio-standard'
DEFAULT_REGION = 'USA'
DEFAULT_MARKET = 'USA'

def _generateConstraintXML(name, series, gcamPolicy=DEFAULT_POLICY, policyType=None,
                           region=DEFAULT_REGION, market=DEFAULT_MARKET,
                           preConstraint='', summary=''):

    def genConstraint(year):
        constraint = _ConstraintTemplate.format(year=year, value="{year%s}" % year)
        return constraint

    # Is this the most common case?
    if policyType and not preConstraint:
        preConstraint = '<policyType>{policyType}</policyType>'.format(policyType=policyType)

    constraints = [genConstraint(i) for i in series.index]
    constraintText = '\n'.join(constraints)

    template = _MetaTemplate.format(name=name, gcamPolicy=gcamPolicy, policyType=policyType,
                                    region=region, market=market, summary=summary,
                                    preConstraint=preConstraint, constraints=constraintText)

    args = {'year' + col: value for col, value in series.items()}
    xml = template.format(**args)
    return xml


def _saveConstraintFile(xml, dirname, constraintName, policyType, scenario, groupName='',
                        policySrcDir=None): #, fromMCS=False):
    basename = '%s-%s' % (constraintName, policyType)
    constraintFile = basename + '-constraint.xml'
    policyFile     = basename + '.xml'

    fullDirname = pathjoin(dirname, groupName, scenario)
    mkdirs(fullDirname)

    pathname = pathjoin(fullDirname, constraintFile)
    _logger.debug("Generating constraint file: %s", pathname)
    with open(pathname, 'w') as f:
        f.write(xml)

    # TBD: test this
    prefix = '../../../' if groupName else '../../'
    localxml = prefix + LOCAL_XML_NAME

    # ToDo: replace subdir with groupDir?
    #source   = pathjoin(localxml, subdir, scenario, policyFile)

    # TBD: isn't this already handled by addMarketConstraint with baselinePolicy?
    return

    # if policySrcDir:
    #     scenario = policySrcDir
    #     # parentName = os.path.basename(dirname)
    #     # grandparentDir = os.path.dirname(os.path.dirname(dirname))
    #     # fullDirname = pathjoin(grandparentDir, policySrcDir, parentName)
    #     localxml = pathjoin('../..', policySrcDir, LOCAL_XML_NAME)
    #
    # source   = pathjoin(localxml, groupName, scenario, policyFile)
    # linkname = pathjoin(fullDirname, policyFile)
    #
    # mode = 'Copy' if getParamAsBoolean('GCAM.CopyAllFiles') else 'Link'
    # _logger.debug("%sing %s to %s", mode, source, linkname)
    # if os.path.lexists(linkname):
    #     os.remove(linkname)
    # symlinkOrCopyFile(source, linkname)

def parseStringPairs(argString, datatype=float):
    """
    Convert a string of comma-separated pairs of colon-delimited values to
    a pandas Series where the first value of each pair is the index name and
    the second value is a float, or the type given.
    """
    import pandas as pd

    pairs = argString.split(',')
    dataDict = {year:datatype(coef) for (year, coef) in map(lambda pair: pair.split(':'), pairs)}
    coefficients = pd.Series(data=dataDict)
    return coefficients

cellEtohConstraintTemplate ='''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
  <!--
    Cellulosic ethanol constraints.
    This is a generated constraint file. Edits will be overwritten!
  -->
  <world>
    <region name="USA">
      <policy-portfolio-standard name="cellulosic-etoh-{cellEtohPolicyType}">
        <policyType>{cellEtohPolicyType}</policyType>
        <market>USA</market>
        <min-price year="1975" fillout="1">-1e6</min-price>
        <constraint year="2020">{level2020}</constraint>
        <constraint year="2025">{level2025}</constraint>
        <constraint year="2030">{level2030}</constraint>
        <constraint year="2035">{level2035}</constraint>
        <constraint year="2040">{level2040}</constraint>
        <constraint year="2045">{level2045}</constraint>
        <constraint year="2050">{level2050}</constraint>
      </policy-portfolio-standard>
    </region>
  </world>
</scenario>
'''

US_REGION_QUERY = 'region in ["USA", "United States"]'

# TBD: make region an argument rather than assuming USA

def genBioConstraints(**kwargs):
    import pandas as pd

    #fromMCS = kwargs.get('fromMCS', False)
    resultsDir = kwargs['resultsDir']
    baseline = kwargs['baseline']
    policy = kwargs['policy']
    subdir = kwargs.get('subdir', '')
    defaultLevel = float(kwargs.get('defaultLevel', 0))
    annualLevels = kwargs.get('annualLevels', None)
    biomassPolicyType = kwargs['biomassPolicyType']
    purposeGrownPolicyType = kwargs['purposeGrownPolicyType']
    cellEtohPolicyType = kwargs['cellEtohPolicyType']
    coefficients = parseStringPairs(kwargs.get('coefficients', None) or DefaultCellulosicCoefficients)
    xmlOutputDir = kwargs['xmlOutputDir'] # required

    batchDir = getBatchDir(baseline, resultsDir)

    refinedLiquidsDF = readQueryResult(batchDir, baseline, 'Refined-liquids-production-by-technology', cache=True)
    totalBiomassDF   = readQueryResult(batchDir, baseline, 'Total_biomass_consumption', cache=True)
    purposeGrownDF   = readQueryResult(batchDir, baseline, 'Purpose-grown_biomass_production', cache=True)

    yearCols = getYearCols(kwargs['years'])

    refinedLiquidsUSA = refinedLiquidsDF.query(US_REGION_QUERY)[yearCols]
    totalBiomassUSA   = totalBiomassDF.query(US_REGION_QUERY)[yearCols]
    purposeGrownUSA   = purposeGrownDF.query(US_REGION_QUERY)[yearCols]

    _logger.debug('totalBiomassUSA:\n', totalBiomassUSA)

    cellulosicEtOH  = refinedLiquidsUSA.query('technology == "cellulosic ethanol"')[yearCols]
    if cellulosicEtOH.shape[0] == 0:
        cellulosicEtOH = 0

    _logger.debug('cellulosicEtOH:\n', cellulosicEtOH)
    _logger.debug("Target cellulosic biofuel level %.2f EJ" % defaultLevel)

    desiredCellEtoh = pd.Series(data={year: defaultLevel for year in yearCols})
    if annualLevels:
        annuals = parseStringPairs(annualLevels)
        desiredCellEtoh[annuals.index] = annuals    # override any default values
        _logger.debug("Annual levels set to:", annualLevels)

    _logger.debug("Cell EtOH coefficients:\n", coefficients)

    # Calculate biomass required to meet required level
    deltaCellulose = (desiredCellEtoh - cellulosicEtOH) * coefficients
    _logger.debug('deltaCellulose:\n', deltaCellulose)

    biomassConstraint = totalBiomassUSA.iloc[0] + deltaCellulose.iloc[0]
    _logger.debug('biomassConstraint:\n', biomassConstraint)

    xml = _generateConstraintXML('regional-biomass-constraint', biomassConstraint,
                                 policyType=biomassPolicyType, summary='Regional biomass constraint.')
    _saveConstraintFile(xml, xmlOutputDir, 'regional-biomass', biomassPolicyType, policy,
                        groupName=subdir)#, fromMCS=fromMCS)

    # For switchgrass, we generate a constraint file to adjust purpose-grown biomass
    # by the same amount as the total regional biomass, forcing the change to come from switchgrass.
    if kwargs.get('switchgrass', False):
        constraint = purposeGrownUSA.iloc[0] + deltaCellulose.iloc[0]
    else:
        constraint = purposeGrownUSA.iloc[0]

    xml = _generateConstraintXML('purpose-grown-constraint', constraint, policyType=purposeGrownPolicyType,
                                 summary='Purpose-grown biomass constraint.')
    _saveConstraintFile(xml, xmlOutputDir, 'purpose-grown', purposeGrownPolicyType, policy,
                        groupName=subdir)#, fromMCS=fromMCS)

    # Create dictionary to use for template processing
    xmlArgs = {"level" + year : value for year, value in desiredCellEtoh.items()}
    xmlArgs['cellEtohPolicyType'] = 'subsidy' if cellEtohPolicyType == 'subs' else cellEtohPolicyType

    xml = cellEtohConstraintTemplate.format(**xmlArgs)
    _saveConstraintFile(xml, xmlOutputDir, 'cell-etoh', cellEtohPolicyType, policy,
                        groupName=subdir)#, fromMCS=fromMCS)


def bioMain(args):
    genBioConstraints(**vars(args))


yearConstraintTemplate = '''        <constraint year="{year}">{level}</constraint>'''

fuelConstraintTemplate ='''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
  <!--
    Define fuel constraints.
    This is a generated constraint file. Edits will be overwritten!
  -->
  <world>
    <region name="USA">
      <policy-portfolio-standard name="{fuelTag}-{fuelPolicyType}">
        <policyType>{fuelPolicyType}</policyType>
        <market>USA</market>
        <min-price year="1975" fillout="1">-1e6</min-price>
{yearConstraints}
      </policy-portfolio-standard>
    </region>
  </world>
</scenario>
'''

def genDeltaConstraints(**kwargs):
    import pandas as pd

    baseline  = kwargs['baseline']
    policy    = kwargs['policy']
    groupName = kwargs.get('groupName', '')
    fuelTag   = kwargs.get('fuelTag')
    fuelName  = kwargs.get('fuelName')
    resultsDir  = kwargs['resultsDir']
    switchgrass = kwargs.get('switchgrass', False)
    defaultDelta = float(kwargs.get('defaultDelta', 0))
    coefficients = parseStringPairs(kwargs.get('coefficients', None) or DefaultCellulosicCoefficients)
    annualDeltas = kwargs.get('annualDeltas', None)
    xmlOutputDir = kwargs['xmlOutputDir'] # required
    fuelPolicyType = kwargs['fuelPolicyType']
    biomassPolicyType = kwargs.get('biomassPolicyType', None)
    purposeGrownPolicyType = kwargs.get('purposeGrownPolicyType', None)
    policySrcDir = kwargs.get('policySrcDir', False)

    pd.set_option('display.width', None)    # discover width from terminal

    refinedLiquidsQuery = kwargs.get('refinedLiquidsQuery', 'Refined-liquids-production-by-technology')
    totalBiomassQuery   = kwargs.get('totalBiomassQuery',   'Total_biomass_consumption')
    purposeGrownQuery   = kwargs.get('purposeGrownQuery',   'Purpose-grown_biomass_production')

    batchDir = getBatchDir(baseline, resultsDir)
    refinedLiquidsDF = readQueryResult(batchDir, baseline, refinedLiquidsQuery, cache=True)

    yearCols = getYearCols(kwargs['years'])

    combinedQuery = US_REGION_QUERY + ' and technology == "%s"' % fuelName

    fuelBaseline = refinedLiquidsDF.query(combinedQuery)[yearCols]
    if fuelBaseline.shape[0] == 0:
        fuelBaseline = 0
    else:
        printSeries(fuelBaseline, fuelTag, header='fuelBaseline:')

    _logger.debug("Default fuel delta %.2f EJ", defaultDelta)

    deltas = pd.Series(data={year: defaultDelta for year in yearCols})
    if annualDeltas is not None:
        annuals = annualDeltas if isinstance(annualDeltas, pd.Series) else parseStringPairs(annualDeltas)
        deltas.loc[annuals.index] = annuals    # override any default for the given years
        printSeries(deltas, fuelTag, header='annual deltas:')
        #_logger.debug("Annual deltas: %s", deltas)

    # Calculate fuel target after applying deltas
    fuelTargets = fuelBaseline.iloc[0] + deltas
    printSeries(fuelTargets, fuelTag, header='fuelTargets:')

    # Generate annual XML for <constraint year="{year}">{level}</constraint>
    yearConstraints = [yearConstraintTemplate.format(year=year, level=level) for year, level in fuelTargets.items()]

    xmlArgs = {}
    xmlArgs['fuelPolicyType'] = fuelPolicyType
    xmlArgs['fuelTag'] = fuelTag
    xmlArgs['yearConstraints'] = '\n'.join(yearConstraints)

    xml = fuelConstraintTemplate.format(**xmlArgs)

    _saveConstraintFile(xml, xmlOutputDir, fuelTag, fuelPolicyType, policy,
                        groupName=groupName, policySrcDir=policySrcDir)#, fromMCS=fromMCS)

    if switchgrass:
        # Calculate additional biomass required to meet required delta
        deltaCellulose = deltas * coefficients[yearCols]
        printSeries(deltaCellulose, 'cellulose', header='deltaCellulose:')

        totalBiomassDF = readQueryResult(batchDir, baseline, totalBiomassQuery, cache=True)
        totalBiomassUSA = totalBiomassDF.query(US_REGION_QUERY)[yearCols]

        biomassConstraint = totalBiomassUSA.iloc[0] + deltaCellulose.iloc[0]
        printSeries(biomassConstraint, 'regional-biomass', header='biomassConstraint:')

        # For switchgrass, we generate a constraint file to adjust purpose-grown biomass
        # by the same amount as the total regional biomass, forcing the change to come from switchgrass.
        purposeGrownDF = readQueryResult(batchDir, baseline, purposeGrownQuery, cache=True)

        # For some reason, purpose grown results are returned for 1990, 2005, then
        # 2020, 2025, but not 2010 or 2015. So we add any missing columns here.
        missingCols = list(set(yearCols) - set(purposeGrownDF.columns))
        if len(missingCols) > 0:
            purposeGrownDF = pd.concat([purposeGrownDF, pd.DataFrame(columns=missingCols)])

        purposeGrownDF.fillna(0, inplace=True)
        purposeGrownUSA  = purposeGrownDF.query(US_REGION_QUERY)[yearCols]

        xml = _generateConstraintXML('regional-biomass-constraint', biomassConstraint, policyType=biomassPolicyType,
                                     summary='Regional biomass constraint.')

        _saveConstraintFile(xml, xmlOutputDir, 'regional-biomass', biomassPolicyType, policy,
                            groupName=groupName, policySrcDir=policySrcDir)#, fromMCS=fromMCS)

        constraint = purposeGrownUSA.iloc[0] + deltaCellulose.iloc[0]

        xml = _generateConstraintXML('purpose-grown-constraint', constraint, policyType=purposeGrownPolicyType,
                                     summary='Purpose-grown biomass constraint.')

        _saveConstraintFile(xml, xmlOutputDir, 'purpose-grown', purposeGrownPolicyType, policy,
                            groupName=groupName, policySrcDir=policySrcDir)#, fromMCS=fromMCS)
