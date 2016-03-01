#! /usr/bin/env python
'''
Created on 1/19/16

@author: rjp

Allow user to specify incremental values to add to the production of a given
fuel, by year, and generate the corresponding constraint file.

Requires baseline query results for: refined-liquids-prod-by-tech-USA
'''
import argparse
import pandas as pd
from . import utils as U

DefaultName  = 'cellulosic ethanol'
DefaultTag   = 'cell-etoh'

PolicyChoices = ['tax', 'subsidy']

def deltaArgParser(program, version):
    parser = argparse.ArgumentParser(prog=program,
                                     description='''Specify incremental values to add to the
                                                    production of a given fuel, by year, and
                                                    generate the corresponding constraint file.''')

    parser.add_argument('-c', '--coefficients', type=str, default=None,
                        help='''A comma-separated string of year:coefficient pairs. This
                        sets the cellulosic ethanol conversion coefficients. Defaults to
                        standard GCAM values: %s.''' % U.DefaultCellulosicCoefficients)

    parser.add_argument('-b', '--biomassPolicyType', choices=PolicyChoices, default='subsidy',
                         help='Regional biomass policy type. Default is subsidy.')

    parser.add_argument('-B', '--baseline', required=True,
                        help='The baseline on which the policy scenario is based')

    parser.add_argument('-P', '--policy', required=True,
                        help='The policy scenario name')

    parser.add_argument('-l', '--defaultDelta', type=float, default=0.0,
                        help='''Default increment to add to each year (EJ). All or individual
                        years values can be set (overriding -l flag values) using the -L flag.''')

    parser.add_argument('-m', '--fromMCS', action='store_true',
                         help="Used when calling from gcammcs so correct pathnames are computed.")

    parser.add_argument('-L', '--annualDeltas', default='',
                        help='''Optional production increments by year. Value must be a
                        comma-delimited string of year:level pairs, where level in is EJ.
                        If -l is not used to set default for all years, you must specify
                        values for all years using this option.''')

    parser.add_argument('-P', '--purposeGrownPolicyType', choices=PolicyChoices, default='subsidy',
                         help='Purpose-grown biomass policy type. Default is subsidy.')

    parser.add_argument('-p', '--policyType', choices=PolicyChoices, default='tax',
                         help='Type of policy to use for the fuel. Default is tax.')

    parser.add_argument('-f', '--fuelName', default=DefaultName,
                         help="The fuel to generate constraints for. Default is %s" % DefaultName)

    parser.add_argument('-R', '--resultsDir', default='.',
                        help='The parent directory holding the GCAM output workspaces')

    parser.add_argument('-S', '--subdir', default='',
                         help='Sub-directory for local-xml files, if any')

    parser.add_argument('-t', '--fuelTag', default=DefaultTag,
                         help="The fuel tag to generate constraints for. Default is %s" % DefaultTag)

    parser.add_argument('-v', '--verbose', action='store_true',
                         help="Show diagnostic messages")

    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + version)

    parser.add_argument('-x', '--xmlOutputDir', default=None,
                         help='''The directory into which to generate XML files.
                         Defaults to policy name in the current directory.''')

    parser.add_argument('-y', '--years', default=U.DefaultYears,
                        help='''Years to generate constraints for. Must be of the form
                        XXXX-YYYY. Default is "%s"''' % U.DefaultYears)

    return parser


def parseDeltaArgs(program, version, args=None):
    """
    Allows calling the arg parser programmatically.

    :param args: The parameter list to parse.
    :return: populated Namespace instance
    """
    parser = argParser(program, version)
    args = parser.parse_args(args=args)
    return args


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

US_REGION_QUERY = 'region in ["USA", "United States"]'

def genDeltaConstraints(**kwargs):
    fromMCS  = kwargs.get('fromMCS', False)
    baseline = kwargs['baseline']
    policy   = kwargs['policy']
    subdir   = kwargs.get('subdir', '')
    verbose  = kwargs.get('verbose', False)
    fuelTag  = kwargs.get('fuelTag')
    fuelName = kwargs.get('fuelName')
    resultsDir  = kwargs['resultsDir']
    switchgrass = kwargs.get('switchgrass', False)
    defaultDelta = float(kwargs.get('defaultDelta', 0))
    coefficients = U.parseStringPairs(kwargs.get('coefficients', None) or U.DefaultCellulosicCoefficients)
    annualDeltas = kwargs.get('annualDeltas', None)
    xmlOutputDir = kwargs['xmlOutputDir'] # required
    fuelPolicyType = kwargs['fuelPolicyType']
    biomassPolicyType = kwargs.get('biomassPolicyType', None)
    purposeGrownPolicyType = kwargs.get('purposeGrownPolicyType', None)

    batchDir = U.batchDir(baseline, resultsDir, fromMCS=fromMCS)
    refinedLiquidsDF = U.readQueryResult(batchDir, baseline, 'refined-liquids-prod-by-tech-USA')

    yearCols = U.yearCols(kwargs['years'])

    fuelBaseline = refinedLiquidsDF.query('technology == "%s"' % fuelName)[yearCols]
    if fuelBaseline.shape[0] == 0:
        fuelBaseline = 0

    # if verbose:
    #     print 'fuelBaseline:\n', fuelBaseline
    #     print "Default fuel delta %.2f EJ" % defaultDelta

    deltas = pd.Series(data={year: defaultDelta for year in yearCols})
    if annualDeltas:
        annuals = U.parseStringPairs(annualDeltas)
        deltas.loc[annuals.index] = annuals    # override any default for the given years
        # if verbose:
        #     print "Annual deltas:", deltas

    # Calculate fuel target after applying deltas
    fuelTargets = fuelBaseline.iloc[0] + deltas
    if verbose:
        print '\nfuelTargets:'
        U.printSeries(fuelTargets, fuelTag)

    # Generate annual XML for <constraint year="{year}">{level}</constraint>
    yearConstraints = [yearConstraintTemplate.format(year=year, level=level) for year, level in fuelTargets.iteritems()]

    xmlArgs = {}
    xmlArgs['fuelPolicyType'] = fuelPolicyType
    xmlArgs['fuelTag'] = fuelTag
    xmlArgs['yearConstraints'] = '\n'.join(yearConstraints)

    xml = fuelConstraintTemplate.format(**xmlArgs)

    U.saveConstraintFile(xml, xmlOutputDir, fuelTag, fuelPolicyType, policy,
                       subdir=subdir, fromMCS=fromMCS)

    if switchgrass:
        # Calculate additional biomass required to meet required delta
        deltaCellulose = deltas * coefficients[yearCols]

        if verbose:
            print '\ndeltaCellulose:'
            U.printSeries(deltaCellulose, 'cellulose')

        totalBiomassDF = U.readQueryResult(batchDir, baseline, 'Total_biomass_consumption')
        totalBiomassUSA = totalBiomassDF.query(US_REGION_QUERY)[yearCols]

        biomassConstraint = totalBiomassUSA.iloc[0] + deltaCellulose.iloc[0]
        if verbose:
            print '\nbiomassConstraint:'
            U.printSeries(biomassConstraint, 'regional-biomass')

        # For switchgrass, we generate a constraint file to adjust purpose-grown biomass
        # by the same amount as the total regional biomass, forcing the change to come from switchgrass.
        purposeGrownDF = U.readQueryResult(batchDir, baseline, 'Purpose-grown_biomass_production')

        # For some reason, purpose grown results are returned for 1990, 2005, then
        # 2020, 2025, but not 2010 or 2015. So we add any missing columns here.
        missingCols = list(set(yearCols) - set(purposeGrownDF.columns))
        if len(missingCols) > 0:
            purposeGrownDF = pd.concat([purposeGrownDF, pd.DataFrame(columns=missingCols)])

        purposeGrownDF.fillna(0, inplace=True)
        purposeGrownUSA  = purposeGrownDF.query(US_REGION_QUERY)[yearCols]

        xml = U.generateConstraintXML('regional-biomass-constraint', biomassConstraint, biomassPolicyType,
                                      summary='Regional biomass constraint.')

        U.saveConstraintFile(xml, xmlOutputDir, 'regional-biomass', biomassPolicyType, policy,
                             subdir=subdir, fromMCS=fromMCS)

        constraint = purposeGrownUSA.iloc[0] + deltaCellulose.iloc[0]

        xml = U.generateConstraintXML('purpose-grown-constraint', constraint, purposeGrownPolicyType,
                                      summary='Purpose-grown biomass constraint.')

        U.saveConstraintFile(xml, xmlOutputDir, 'purpose-grown', purposeGrownPolicyType, policy,
                             subdir=subdir, fromMCS=fromMCS)


def deltaMain(program, version):
    args = parseDeltaArgs(program, version)
    genDeltaConstraints(**vars(args))
