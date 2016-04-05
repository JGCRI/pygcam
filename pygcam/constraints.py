#! /usr/bin/env python
'''
Created on 4/26/15

@author: rjp
'''
import os
import pandas as pd
from .log import getLogger
from .subcommand import SubcommandABC
from .utils import mkdirs, getBatchDir, getYearCols, printSeries
from .query import readQueryResult, readCsv

_logger = getLogger(__name__)

__version__ = "0.1"

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

def generateConstraintXML(name, series, gcamPolicy=DEFAULT_POLICY, policyType=None,
                          region=DEFAULT_REGION, market=DEFAULT_MARKET,
                          preConstraint='', summary=''):

    def genConstraint(year):
        constraint = _ConstraintTemplate.format(year=year, value="{year%s}" % year)
        return constraint

    # Is this the most common case?
    if policyType and not preConstraint:
        preConstraint = '<policyType>{policyType}</policyType>'.format(policyType=policyType)

    constraints = map(genConstraint, series.index)
    constraintText = '\n'.join(constraints)

    template = _MetaTemplate.format(name=name, gcamPolicy=gcamPolicy, policyType=policyType,
                                    region=region, market=market, summary=summary,
                                    preConstraint=preConstraint, constraints=constraintText)

    args = {'year' + col: value for col, value in series.iteritems()}
    xml = template.format(**args)
    return xml


def saveConstraintFile(xml, dirname, constraintName, policyType, scenario, subdir='', fromMCS=False):
    basename = '%s-%s' % (constraintName, policyType)
    constraintFile = basename + '-constraint.xml'
    policyFile     = basename + '.xml'

    dirname = os.path.join(dirname, subdir, scenario)
    mkdirs(dirname)

    pathname = os.path.join(dirname, constraintFile)
    _logger.debug("Generating constraint file: %s", pathname)
    with open(pathname, 'w') as f:
        f.write(xml)

    # compute relative location of local-xml directory
    levels = 2
    levels += 2 if fromMCS else 0
    levels += 1 if subdir else 0

    localxml = '../' * levels + 'local-xml'

    source   = os.path.join(localxml, subdir, scenario, policyFile)
    linkname = os.path.join(dirname, policyFile)

    _logger.debug("Linking to: %s", source)
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

cellEtohConstraintTemplate ='''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
	<output-meta-data>
		<summary>
		  Cellulosic ethanol constraints.
          This is a generated constraint file. Edits will be overwritten!
		</summary>
	</output-meta-data>
	<world>
		<region name="USA">
			<policy-portfolio-standard name="cellulosic-etoh-{cellEtohPolicyType}">
				<market>USA</market>
				<policyType>{cellEtohPolicyType}</policyType>
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

cellEtohComboConstraintTemplate ='''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
	<output-meta-data>
		<summary>
		  Combined cellulosic ethanol.
          This is a generated constraint file. Edits will be overwritten!
		</summary>
	</output-meta-data>
	<world>
		<region name="USA">
			<policy-portfolio-standard name="cellulosic-etoh-tax">
				<market>USA</market>
				<policyType>tax</policyType>
				<constraint year="2020">{level2020}</constraint>
				<constraint year="2025">{level2025}</constraint>
				<constraint year="2030">{level2030}</constraint>
				<constraint year="2035">{level2035}</constraint>
				<constraint year="2040">{level2040}</constraint>
				<constraint year="2045">{level2045}</constraint>
				<constraint year="2050">{level2050}</constraint>
			</policy-portfolio-standard>

			<policy-portfolio-standard name="cellulosic-etoh-subsidy">
				<market>USA</market>
				<policyType>subsidy</policyType>
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

def genBioConstraints(**kwargs):
    fromMCS = kwargs.get('fromMCS', False)
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

    leafDir = 'queryResults' if fromMCS else 'batch-{baseline}'.format(baseline=baseline)
    batchDir = os.path.join(resultsDir, baseline, leafDir)
    #'{resultsDir}/{baseline}/{leafDir}'.format(resultsDir=resultsDir, baseline=baseline, leafDir=leafDir)
    totalBiomassFile   = os.path.join(batchDir, 'Total_biomass_consumption-%s.csv' % baseline)
    refinedLiquidsFile = os.path.join(batchDir, 'refined-liquids-prod-by-tech-USA-%s.csv' % baseline)
    purposeGrownFile   = os.path.join(batchDir, 'Purpose-grown_biomass_production-%s.csv' % baseline)

    totalBiomassDF   = readCsv(totalBiomassFile)
    refinedLiquidsDF = readCsv(refinedLiquidsFile)

    yearCols = getYearCols(kwargs['years'])

    totalBiomassUSA = totalBiomassDF.query(US_REGION_QUERY)[yearCols]
    _logger.debug('totalBiomassUSA:\n', totalBiomassUSA)

    cellulosicEtOH  = refinedLiquidsDF.query('technology == "cellulosic ethanol"')[yearCols]
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

    xml = generateConstraintXML('regional-biomass-constraint', biomassConstraint,
                                policyType=biomassPolicyType, summary='Regional biomass constraint.')
    saveConstraintFile(xml, xmlOutputDir, 'regional-biomass', biomassPolicyType, policy,
                       subdir=subdir, fromMCS=fromMCS)

    # For switchgrass, we generate a constraint file to adjust purpose-grown biomass
    # by the same amount as the total regional biomass, forcing the change to come from switchgrass.
    purposeGrownDF   = readCsv(purposeGrownFile)
    purposeGrownUSA  = purposeGrownDF.query(US_REGION_QUERY)[yearCols]

    if kwargs.get('switchgrass', False):
        constraint = purposeGrownUSA.iloc[0] + deltaCellulose.iloc[0]
    else:
        constraint = purposeGrownUSA.iloc[0]

    xml = generateConstraintXML('purpose-grown-constraint', constraint, policyType=purposeGrownPolicyType,
                                summary='Purpose-grown biomass constraint.')
    saveConstraintFile(xml, xmlOutputDir, 'purpose-grown', purposeGrownPolicyType, policy,
                       subdir=subdir, fromMCS=fromMCS)

    # Create dictionary to use for template processing
    xmlArgs = {"level" + year : value for year, value in desiredCellEtoh.iteritems()}
    xmlArgs['cellEtohPolicyType'] = 'subsidy' if cellEtohPolicyType == 'subs' else cellEtohPolicyType

    template = cellEtohComboConstraintTemplate if cellEtohPolicyType == 'combo' else cellEtohConstraintTemplate
    xml = template.format(**xmlArgs)

    saveConstraintFile(xml, xmlOutputDir, 'cell-etoh', cellEtohPolicyType, policy,
                       subdir=subdir, fromMCS=fromMCS)


def bioMain(args):
    genBioConstraints(**vars(args))


yearConstraintTemplate = '''                <constraint year="{year}">{level}</constraint>'''

fuelConstraintTemplate ='''<?xml version="1.0" encoding="UTF-8"?>
<scenario>
	<output-meta-data>
		<summary>
		  Define fuel constraints.
          This is a generated constraint file. Edits will be overwritten!
		</summary>
	</output-meta-data>
	<world>
		<region name="USA">
			<policy-portfolio-standard name="{fuelTag}-{fuelPolicyType}">
				<market>USA</market>
				<policyType>{fuelPolicyType}</policyType>
{yearConstraints}
			</policy-portfolio-standard>
		</region>
	</world>
</scenario>
'''

def genDeltaConstraints(**kwargs):
    fromMCS  = kwargs.get('fromMCS', False)
    baseline = kwargs['baseline']
    policy   = kwargs['policy']
    subdir   = kwargs.get('subdir', '')
    fuelTag  = kwargs.get('fuelTag')
    fuelName = kwargs.get('fuelName')
    resultsDir  = kwargs['resultsDir']
    switchgrass = kwargs.get('switchgrass', False)
    defaultDelta = float(kwargs.get('defaultDelta', 0))
    coefficients = parseStringPairs(kwargs.get('coefficients', None) or DefaultCellulosicCoefficients)
    annualDeltas = kwargs.get('annualDeltas', None)
    xmlOutputDir = kwargs['xmlOutputDir'] # required
    fuelPolicyType = kwargs['fuelPolicyType']
    biomassPolicyType = kwargs.get('biomassPolicyType', None)
    purposeGrownPolicyType = kwargs.get('purposeGrownPolicyType', None)

    batchDir = getBatchDir(baseline, resultsDir, fromMCS=fromMCS)
    refinedLiquidsDF = readQueryResult(batchDir, baseline, 'refined-liquids-prod-by-tech-USA')

    yearCols = getYearCols(kwargs['years'])

    fuelBaseline = refinedLiquidsDF.query('technology == "%s"' % fuelName)[yearCols]
    if fuelBaseline.shape[0] == 0:
        fuelBaseline = 0

    _logger.debug('fuelBaseline: %s\n', fuelBaseline)
    _logger.debug("Default fuel delta %.2f EJ", defaultDelta)

    deltas = pd.Series(data={year: defaultDelta for year in yearCols})
    if annualDeltas:
        annuals = parseStringPairs(annualDeltas)
        deltas.loc[annuals.index] = annuals    # override any default for the given years
        _logger.debug("Annual deltas: %s", deltas)

    # Calculate fuel target after applying deltas
    fuelTargets = fuelBaseline.iloc[0] + deltas
    _logger.debug('fuelTargets:')
    printSeries(fuelTargets, fuelTag)

    # Generate annual XML for <constraint year="{year}">{level}</constraint>
    yearConstraints = [yearConstraintTemplate.format(year=year, level=level) for year, level in fuelTargets.iteritems()]

    xmlArgs = {}
    xmlArgs['fuelPolicyType'] = fuelPolicyType
    xmlArgs['fuelTag'] = fuelTag
    xmlArgs['yearConstraints'] = '\n'.join(yearConstraints)

    xml = fuelConstraintTemplate.format(**xmlArgs)

    saveConstraintFile(xml, xmlOutputDir, fuelTag, fuelPolicyType, policy,
                       subdir=subdir, fromMCS=fromMCS)

    if switchgrass:
        # Calculate additional biomass required to meet required delta
        deltaCellulose = deltas * coefficients[yearCols]

        _logger.debug('\ndeltaCellulose:')
        printSeries(deltaCellulose, 'cellulose')

        totalBiomassDF = readQueryResult(batchDir, baseline, 'Total_biomass_consumption')
        totalBiomassUSA = totalBiomassDF.query(US_REGION_QUERY)[yearCols]

        biomassConstraint = totalBiomassUSA.iloc[0] + deltaCellulose.iloc[0]
        _logger.debug('biomassConstraint:')
        printSeries(biomassConstraint, 'regional-biomass')

        # For switchgrass, we generate a constraint file to adjust purpose-grown biomass
        # by the same amount as the total regional biomass, forcing the change to come from switchgrass.
        purposeGrownDF = readQueryResult(batchDir, baseline, 'Purpose-grown_biomass_production')

        # For some reason, purpose grown results are returned for 1990, 2005, then
        # 2020, 2025, but not 2010 or 2015. So we add any missing columns here.
        missingCols = list(set(yearCols) - set(purposeGrownDF.columns))
        if len(missingCols) > 0:
            purposeGrownDF = pd.concat([purposeGrownDF, pd.DataFrame(columns=missingCols)])

        purposeGrownDF.fillna(0, inplace=True)
        purposeGrownUSA  = purposeGrownDF.query(US_REGION_QUERY)[yearCols]

        xml = generateConstraintXML('regional-biomass-constraint', biomassConstraint, policyType=biomassPolicyType,
                                    summary='Regional biomass constraint.')

        saveConstraintFile(xml, xmlOutputDir, 'regional-biomass', biomassPolicyType, policy,
                           subdir=subdir, fromMCS=fromMCS)

        constraint = purposeGrownUSA.iloc[0] + deltaCellulose.iloc[0]

        xml = generateConstraintXML('purpose-grown-constraint', constraint,  policyType=purposeGrownPolicyType,
                                    summary='Purpose-grown biomass constraint.')

        saveConstraintFile(xml, xmlOutputDir, 'purpose-grown', purposeGrownPolicyType, policy,
                           subdir=subdir, fromMCS=fromMCS)


# def deltaMain(program, version):
#     args = parseDeltaArgs(program, version)
#     genDeltaConstraints(**vars(args))


class GenConstraintsCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Bioenergy constraint generator''',
                  'description' : '''Longer description for sub-command'''}

        super(GenConstraintsCommand, self).__init__('bioConstraint', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('-b', '--biomassPolicyType', default='tax',
                             help='Regional biomass policy type: must be one of {subs, tax}')

        parser.add_argument('-B', '--baseline', default=None,
                            help='The baseline on which the policy scenario is based')

        parser.add_argument('-c', '--coefficients',
                            help='''A comma-separated string of year:coefficient pairs. This
                            sets the cellulosic ethanol conversion coefficients. Defaults to
                            standard GCAM values: %s.''' % DefaultCellulosicCoefficients)

        parser.add_argument('-e', '--cellEtohPolicyType', default='tax',
                             help='Cellulosic ethanol policy type: must be one of {subs, tax}')

        parser.add_argument('-l', '--defaultLevel', type=float, default=0.0,
                            help='''Target cellulosic biofuel level (EJ). All or individual years
                            values can be set (overriding -l flag values) using the -L flag.''')

        parser.add_argument('-L', '--annualLevels', required=False,
                            help='''Optional cellulosic biofuel production levels by year. Value
                            must be a comma-delimited string of year:level pairs, where level is
                            given in EJ. If -l is not used to set default for all years, you must
                            specify values for all years using this option.''')

        parser.add_argument('-m', '--fromMCS', action='store_true',
                             help="Used when calling from gcammcs so correct pathnames are computed.")

        parser.add_argument('-p', '--purposeGrownPolicyType', default='subs',
                             help='Purpose-grown biomass policy type: must be one of {subs, tax}')

        parser.add_argument('-P', '--policy',
                            help='The policy scenario name')

        parser.add_argument('-R', '--resultsDir',
                            help='The parent directory holding the GCAM output workspaces')

        parser.add_argument('-s', '--switchgrass', action='store_true',
                             help="Generate constraints for switchgrass")

        parser.add_argument('-S', '--subdir', default='',
                             help='Sub-directory for local-xml files, if any')

        parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)

        parser.add_argument('-x', '--xmlOutputDir',
                             help='''The directory into which to generate XML files. Defaults to
                             policy name in the current directory.''')

        parser.add_argument('-y', '--years', default=DefaultYears,
                            help='''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "%s"''' % DefaultYears)
        return parser


    def run(self, args, tool):
        genBioConstraints(**vars(args))



DefaultName  = 'cellulosic ethanol'
DefaultTag   = 'cell-etoh'
PolicyChoices = ['tax', 'subsidy']


class DeltaConstraintsCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Specify incremental values to add to the production of a given fuel,
                              by year, and generate the corresponding constraint file.''',
                  'description' : '''Longer description for sub-command'''}

        super(DeltaConstraintsCommand, self).__init__('deltaConstraint', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('-c', '--coefficients',
                            help='''A comma-separated string of year:coefficient pairs. This
                            sets the cellulosic ethanol conversion coefficients. Defaults to
                            standard GCAM values: %s.''' % DefaultCellulosicCoefficients)

        parser.add_argument('-b', '--biomassPolicyType', choices=PolicyChoices, default='subsidy',
                            help='Regional biomass policy type. Default is subsidy.')

        parser.add_argument('-B', '--baseline', required=True,
                            help='The baseline on which the policy scenario is based')

        parser.add_argument('-f', '--fuelName', default=DefaultName,
                            help="The fuel to generate constraints for. Default is %s" % DefaultName)

        parser.add_argument('-l', '--defaultDelta', type=float, default=0.0,
                            help='''Default increment to add to each year (EJ). All or individual
                            years values can be set (overriding -l flag values) using the -L flag.''')

        parser.add_argument('-L', '--annualDeltas', default='',
                            help='''Optional production increments by year. Value must be a
                            comma-delimited string of year:level pairs, where level in is EJ.
                            If -l is not used to set default for all years, you must specify
                            values for all years using this option.''')

        parser.add_argument('-m', '--fromMCS', action='store_true',
                             help="Used when calling from gcammcs so correct pathnames are computed.")

        parser.add_argument('-p', '--purposeGrownPolicyType', choices=PolicyChoices, default='subsidy',
                             help='Purpose-grown biomass policy type. Default is subsidy.')

        parser.add_argument('-P', '--policy', required=True,
                            help='The policy scenario name')

        parser.add_argument('-R', '--resultsDir', default='.',
                            help='The parent directory holding the GCAM output workspaces')

        parser.add_argument('-S', '--subdir', default='',
                             help='Sub-directory for local-xml files, if any')

        parser.add_argument('-t', '--fuelTag', default=DefaultTag,
                             help="The fuel tag to generate constraints for. Default is %s" % DefaultTag)

        parser.add_argument('-T', '--policyType', choices=PolicyChoices, default='tax',
                             help='Type of policy to use for the fuel. Default is tax.')

        parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__)

        parser.add_argument('-x', '--xmlOutputDir',
                             help='''The directory into which to generate XML files.
                             Defaults to policy name in the current directory.''')

        parser.add_argument('-y', '--years', default=DefaultYears,
                            help='''Years to generate constraints for. Must be of the form
                            XXXX-YYYY. Default is "%s"''' % DefaultYears)
        return parser


    def run(self, args, tool):
        genDeltaConstraints(**vars(args))


if __name__ == '__main__':
    # <?xml version="1.0" encoding="UTF-8"?>
    # <scenario>
    #     <world>
    #         <region name="USA">
    #             <ghgpolicy name="ElecCO2">
    #                 <market>USA</market>
    #                 <fixedTax year="2015">0</fixedTax>
    #                 <constraint year="2020">583</constraint>
    #                 <constraint year="2025">512</constraint>
    #                 <constraint year="2030">442</constraint>
    #                 <constraint year="2035">442</constraint>
    #                 <constraint year="2040">442</constraint>
    #                 <constraint year="2045">442</constraint>
    #                 <constraint year="2050">442</constraint>
    #             </ghgpolicy>
    #         </region>
    #     </world>
    # </scenario>

    # Generate the XML above
    xml = generateConstraintXML('ElecCO2',
                                pd.Series({'2020':583, '2025':512, '2030':442, '2035':442,
                                           '2040':442, '2045':442, '2050':442,}),
                                gcamPolicy='ghgpolicy',
                                region='USA',
                                market='USA',
                                preConstraint='<fixedTax year="2015">0</fixedTax>')
    print xml

