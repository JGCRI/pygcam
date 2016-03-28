from os.path import join as pathjoin
from .setup import _echo, ConfigEditor, xmlEdit, extractStubTechnology, expandYearRanges

REFINING_SECTOR = 'refining'
BIOMASS_LIQUIDS = 'biomass liquids'

class RefiningEditor(ConfigEditor):
    """
    RefiningEditor add methods that deal with the refinery sector.
    """
    def __init__(self, name, parent, xmlOutputRoot, xmlSourceDir, workspaceDir, subdir=""):
        super(RefiningEditor, self).__init__(name, parent, xmlOutputRoot, xmlSourceDir, workspaceDir, subdir=subdir)

    # TBD: redefine this as follows, or just call setGlobalTechShutdownRate directly?
    def _setRefinedFuelShutdownRate(self, fuel, year, rate):
        self.setGlobalTechShutdownRate(self, REFINING_SECTOR, BIOMASS_LIQUIDS, fuel, year, rate)

    def setRefinedFuelShutdownRate(self, fuel, year, rate):
        _echo("Set %s shutdown rate to %s for %s in %s" % (fuel, rate, self.name, year))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))

        prefix = "//global-technology-database/location-info[@sector-name='%s' and @subsector-name='%s']/technology[@name='%s']" % \
                 (REFINING_SECTOR, BIOMASS_LIQUIDS, fuel)

        xmlEdit(enTransFileAbs,
                '-u', prefix + "/period[@year='%s']/phased-shutdown-decider/shutdown-rate" % year,
                '-v', rate)

        self.updateScenarioComponent("energy_transformation", enTransFileRel)

    # Deprecated
    # def setRefiningNonEnergyCostByYear(self, fuel, pairs):
    #     '''
    #     Set the non-energy cost of a refining technology, give a list of pairs of (year, price),
    #     where year can be a single year (as string or int), or a string specifying a range of years,
    #     of the form "xxxx-yyyy", which implies 5 year timestep, or "xxxx-yyyy:s", which provides
    #     an alternative timestep. The price is applied to all years indicated by the range.
    #     '''
    #     _echo("Set non-energy-cost of %s for %s to %s" % (fuel, self.name, pairs))
    #
    #     enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))
    #
    #     prefix = "//global-technology-database/location-info[@sector-name='%s']/technology[@name='%s']" % \
    #              (REFINING_SECTOR, fuel)
    #     suffix = "/minicam-non-energy-input[@name='non-energy']/input-cost"
    #
    #     args = [enTransFileAbs]
    #     for year, price in expandYearRanges(pairs):
    #         args += ['-u',
    #                  prefix + ("/period[@year='%s']" % year) + suffix,
    #                  '-v', str(price)]
    #
    #     xmlEdit(*args)
    #
    #     self.updateScenarioComponent("energy_transformation", enTransFileRel)

    # Deprecated
    # def setRefinedLiquidShareWeight(self, fuel, values):
    #     """
    #     Create modified version of en_transformation.xml with the given share-weight
    #     for the given refined liquid fuel in the given year.
    #
    #     :param fuel: (str) the name of a fuel in the 'refining' sector
    #     :param values: (dict-like) keys are string versions of years; values are share-weights,
    #         which must be coercabel to float.
    #     :return: none
    #     """
    #     self.setGlobalTechShareWeight(REFINING_SECTOR, fuel, values)


class BioenergyEditor(RefiningEditor):
    """
    BioenergyEditor adds knowledge of biomass and biofuels.
    """
    def __init__(self, name, parent, xmlOutputRoot, xmlSourceDir, workspaceDir, subdir=""):
        super(BioenergyEditor, self).__init__(name, parent, xmlOutputRoot, xmlSourceDir, workspaceDir, subdir=subdir)

        cornEthanolUsaFile = 'cornEthanolUSA.xml'
        self.cornEthanolUsaAbs = pathjoin(self.scenario_dir_abs, cornEthanolUsaFile)
        self.cornEthanolUsaRel = pathjoin(self.scenario_dir_rel, cornEthanolUsaFile)

        cornEthanolUsaFile2 = 'cornEthanolUSA2.xml'
        self.cornEthanolUsaAbs2 = pathjoin(self.scenario_dir_abs, cornEthanolUsaFile2)
        self.cornEthanolUsaRel2 = pathjoin(self.scenario_dir_rel, cornEthanolUsaFile2)

        cellEthanolUsaFile = 'cellEthanolUSA.xml'
        self.cellEthanolUsaAbs = pathjoin(self.scenario_dir_abs, cellEthanolUsaFile)
        self.cellEthanolUsaRel = pathjoin(self.scenario_dir_rel, cellEthanolUsaFile)

        ftBiofuelsUsaFile = 'ftBiofuelsUSA.xml'
        self.ftBiofuelsUsaAbs = pathjoin(self.scenario_dir_abs, ftBiofuelsUsaFile)
        self.ftBiofuelsUsaRel = pathjoin(self.scenario_dir_rel, ftBiofuelsUsaFile)

        # A US subsidy works without having to change prices, so no need to extract this
        biodieselUsaFile = 'biodieselUSA.xml'
        self.biodieselUsaAbs = pathjoin(self.scenario_dir_abs, biodieselUsaFile)
        self.biodieselUsaRel = pathjoin(self.scenario_dir_rel, biodieselUsaFile)

        biodieselUsaFile2 = 'biodieselUSA2.xml'
        self.biodieselUsaAbs2 = pathjoin(self.scenario_dir_abs, biodieselUsaFile2)
        self.biodieselUsaRel2 = pathjoin(self.scenario_dir_rel, biodieselUsaFile2)


    def adjustResidueSupply(self, loTarget, loPrice, loFract, hiTarget, hiPrice, hiFract, target):
        """
        Change supply curves for residues, as per arguments. loTarget and hiTarget identify
        the price to match in the XML file; loPrice and hiPrice are the new prices to set;
        loFract and hiFract are the new fractions to assign to these prices.
        Target must be one of {all, us-crops, us-corn, global-corn}
        Note that the standard reference supply curve for residue is:
        0% at 1975$0; 25% at $1.2; 65% at $1.5; 100% at $10.
        """
        _echo("Adjust residue supply curves for %s (%s, %s:%s@%s, %s:%s@%s)" % \
             (self.name, target, loTarget, loFract, loPrice, hiTarget, hiFract, hiPrice))

        # Create modified version of resbio_input.xml and modify config to use it
        resbioFileRel, resbioFileAbs = self.getLocalCopy(pathjoin(self.aglu_dir_rel, "resbio_input.xml"))

        # Change all non-forest residue, all non-forest residue in the US, only corn residue in US, or corn residue everywhere.
        if target == 'all-crops':
            xPrefix = "//region/AgSupplySector[@name!='Forest']/AgSupplySubsector"

        elif target == 'us-crops':
            xPrefix = "//region[@name='USA']/AgSupplySector[@name!='Forest']/AgSupplySubsector"

        elif target == 'us-corn':
            xPrefix = "//region[@name='USA']/AgSupplySector[@name='Corn']/AgSupplySubsector"

        elif target == 'global-corn':
            xPrefix = "//region/AgSupplySector[@name='Corn']/AgSupplySubsector"

        fractHarvested = xPrefix + "/AgProductionTechnology/period[@year>2010]/residue-biomass-production/fract-harvested"

        xmlEdit(resbioFileAbs,
            '-u', fractHarvested + "[@price='%s']" % loTarget,
            '-v', loFract,
            '-u', fractHarvested + "[@price='%s']" % hiTarget,
            '-v', hiFract,
            '-u', fractHarvested + "[@price='%s']/@price" % loTarget,
            '-v', loPrice,
            '-u', fractHarvested + "[@price='%s']/@price" % hiTarget,
            '-v', hiPrice)

        self.updateScenarioComponent("residue_bio", resbioFileRel)

    def setMswParameterUSA(self, parameter, value):
        resourcesFileRel, resourcesFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "resources.xml"))

        xpath = "//region[@name='USA']/renewresource/smooth-renewable-subresource[@name='generic waste biomass']/%s" % parameter

        xmlEdit(resourcesFileAbs, '-u', xpath, '-v', value)

        self.updateScenarioComponent("resources", resourcesFileRel)

    def regionalizeBiomassMarket(self, region):
        _echo("Regionalize %s biomass market for %s" % (region, self.name))

        resourcesFileRel, resourcesFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "resources.xml"))

        xmlEdit(resourcesFileAbs,
                '-u', "//region[@name='%s']/renewresource[@name='biomass']/market" % region,
                '-v', "USA")

        self.updateScenarioComponent("resources", resourcesFileRel)

        agForPastBioFileRel, agForPastBioFileAbs = self.getLocalCopy(pathjoin(self.aglu_dir_rel, "ag_For_Past_bio_base.xml"))

        xmlEdit(agForPastBioFileAbs,
                '-u', "//region[@name='%s']/AgSupplySector[@name='biomass']/market" % region,
                '-v', region)

        self.updateScenarioComponent("ag_base", agForPastBioFileRel)

    def setCornEthanolCoefficients(self, cornCoef, gasCoef=None, elecCoef=None):
        '''
        Set corn ethanol performance coefficients, i.e., the (regional) corn, gas, and
        electricity required per GJ of ethanol. These appear in two files, so we edit
        them both.
        '''
        _echo("Set global corn ethanol coefficients: corn=%s, gas=%s, elec=%s" % \
             (cornCoef, gasCoef, elecCoef))

        # XPath applies to file energy-xml/en_supply.xml
        cornCoefXpath = '//technology[@name="regional corn for ethanol"]/period[@year>=2015]/minicam-energy-input[@name="Corn"]/coefficient'

        enSupplyFileRel, enSupplyFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_supply.xml"))

        xmlEdit(enSupplyFileAbs, '-u', cornCoefXpath, '-v', cornCoef)

        self.updateScenarioComponent("energy_supply", enSupplyFileRel)

        if gasCoef or elecCoef:
            enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))
            args = [enTransFileAbs]
            xpath = '//technology[@name="corn ethanol"]/period[@year>=2015]/minicam-energy-input[@name="%s"]/coefficient'

            if gasCoef:
                gasCoefXpath  = xpath % 'wholesale gas'
                args.extend(['-u', gasCoefXpath,  '-v', gasCoef])

            if elecCoef:
                elecCoefXpath = xpath % 'elect_td_ind'
                args.extend(['-u', elecCoefXpath,  '-v', elecCoef])

            xmlEdit(*args)
            self.updateScenarioComponent("energy_transformation", enTransFileRel)

    def setBiofuelBiomassCoefficients(self, fuelName, pairs):
        '''
        Set new coefficients for biomass conversion for the given fuel

        :param fuelName:
            The name of the liquid fuel, e.g., 'cellulosic ethanol', 'FT biofuel', etc.
        :param pairs:
            A sequence of tuples of the form (year, coefficient). For example, to set
            the coefficients for cellulosic ethanol for years 2020 and 2025 to 1.234,
            the pairs would be ((2020, 1.234), (2025, 1.234)).
        :return:
            nothing
        '''
        _echo("Set global biomass coefficients for %s: %s" % (fuelName, pairs))

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))

        prefix = "//global-technology-database/location-info[@subsector-name='%s']/technology[@name='%s']" % \
                 (BIOMASS_LIQUIDS, fuelName)
        suffix = "minicam-energy-input[@name='regional biomass']/coefficient"

        args = [enTransFileAbs]

        for year, coef in pairs:
            args += ['-u', "%s/period[@year='%s']/%s" % (prefix, year, suffix),
                     '-v', str(coef)]

        xmlEdit(*args)

        self.updateScenarioComponent("energy_transformation", enTransFileRel)

    def purposeGrownOffRegional(self, region):
        '''
        Turn off the "isNewTechnology" flag for all land-leaf nodes to turn off
        purpose-grown biomass. The line(s) we need to edit in land_input_3.xml is:
        <isNewTechnology fillout="1" year="2020">1</isNewTechnology>
        '''
        _echo("Turn off purpose-grown biomass technology in %s for %s" % (region, self.name))

        landInput3Rel, landInput3Abs = self.getLocalCopy(pathjoin(self.aglu_dir_rel, "land_input_3.xml"))

        if region == 'global':
             region='*'

        xmlEdit(landInput3Abs,
                '-u', "//region[@name='%s']//isNewTechnology[@year='2020']" % region,
                '-v', "0")

        self.updateScenarioComponent("land_3", landInput3Rel)

    #
    # Various methods that operate on the USA specifically
    #
    def adjustForestResidueSupplyUSA(self, loPrice, loFract, hiPrice, hiFract):
        '''
        Change supply curves for forest residues in the USA only. loPrice and hiPrice
        are the new prices to set; loFract and hiFract are the new fractions to assign
        to these prices.
        '''
        _echo("Adjust forest residue supply curves for %s" % self.name)

        # Create modified version of resbio_input.xml and modify config to use it
        resbioFileRel, resbioFileAbs = self.getLocalCopy(pathjoin(self.aglu_dir_rel, "resbio_input.xml"))

        # Forest residue appears in two places. First, operate on AgSupplySector "Forest"
        xPrefix = "//region[@name='USA']/AgSupplySector[@name='Forest']/AgSupplySubsector"
        fractHarvested = xPrefix + "/AgProductionTechnology/period[@year>=2015]/residue-biomass-production/fract-harvested"

        xmlEdit(resbioFileAbs,
            '-u', fractHarvested + "[@price='1.2']/@price",
            '-v', loPrice,
            '-u', fractHarvested + "[@price='1.5']/@price",
            '-v', hiPrice,
            '-u', fractHarvested + "[@price='1.2']",
            '-v', loFract,
            '-u', fractHarvested + "[@price='1.5']",
            '-v', hiFract)

        # Do the same for supplysector="NonFoodDemand_Forest"
        xPrefix = "//region[@name='USA']/supplysector[@name='NonFoodDemand_Forest']/subsector[@name='Forest']/stub-technology[@name='Forest']"
        fractHarvested = xPrefix + "/period[@year>=2015]/residue-biomass-production/fract-harvested"

        xmlEdit(resbioFileAbs,
            '-u', "%s[@price='1.2']/@price" % fractHarvested,
                '-v', loPrice,
            '-u', "%s[@price='1.5']/@price" % fractHarvested,
                '-v', hiPrice,
            '-u', "%s[@price='1.2']" % fractHarvested,
                '-v', loFract,
            '-u', "%s[@price='1.5']" % fractHarvested,
                '-v', hiFract)

        self.updateScenarioComponent("residue_bio", resbioFileRel)

    #
    # Methods to operate in USA only on technologies extracted from global-technology-database
    #
    def setCellEthanolShareWeightUSA(self, year, shareweight):
        '''
        Create modified version of cellEthanolUSA.xml with the given share-weight
        for the given fuel in the given year.
        '''
        _echo("Set US share-weight to %s for cellulosic ethanol in %s for %s" % (shareweight, year, self.name))

        yearConstraint = ">= 2015" if year == 'all' else ("=" + year)

        xmlEdit(self.cellEthanolUsaAbs,
                '-u', "//stub-technology[@name='cellulosic ethanol']/period[@year%s]/share-weight" % yearConstraint,
                '-v', shareweight)

        self.updateScenarioComponent("cell-etoh-USA", self.cellEthanolUsaRel)

    def localizeCornEthanolTechnologyUSA(self):
        '''
        Copy the stub-technology for corn ethanol to CornEthanolUSA.xml and CornEthanolUSA2.xml
        so they can be manipulated in the US only.
        '''
        _echo("Add corn ethanol stub technology in USA")

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))
        extractStubTechnology('USA', enTransFileAbs, self.cornEthanolUsaAbs,  REFINING_SECTOR, BIOMASS_LIQUIDS, 'corn ethanol')
        extractStubTechnology('USA', enTransFileAbs, self.cornEthanolUsaAbs2, REFINING_SECTOR, BIOMASS_LIQUIDS, 'corn ethanol', fromRegion=True)

        # Insert "2" right after energy_transformation, then "1" right after energy_transformation,
        # so they end up in order "1" then "2".
        self.insertScenarioComponent('corn-etoh-USA2', self.cornEthanolUsaRel2, 'energy_transformation')
        self.insertScenarioComponent('corn-etoh-USA1', self.cornEthanolUsaRel,  'energy_transformation')

    def localizeCellEthanolTechnologyUSA(self):
        '''
        Same as corn ethanol above, but for cellulosic ethanol
        '''
        _echo("Add cellulosic ethanol stub-technology in USA")

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))
        extractStubTechnology('USA', enTransFileAbs, self.cellEthanolUsaAbs,  REFINING_SECTOR, BIOMASS_LIQUIDS, 'cellulosic ethanol')

        self.insertScenarioComponent('cell-etoh-USA', self.cellEthanolUsaRel, 'energy_transformation')

    def localizeFtBiofuelsTechnologyUSA(self):
        '''
        Same as cellulosic ethanol above
        '''
        _echo("Add FT biofuels stub-technology in USA")

        enTransFileRel, enTransFileAbs = self.getLocalCopy(pathjoin(self.energy_dir_rel, "en_transformation.xml"))
        extractStubTechnology('USA', enTransFileAbs, self.ftBiofuelsUsaAbs,  REFINING_SECTOR, BIOMASS_LIQUIDS, 'FT biofuels')

        self.insertScenarioComponent('FT-biofuels-USA', self.ftBiofuelsUsaRel, 'energy_transformation')

    def setBiofuelRefiningNonEnergyCostUSA(self, fuel, pairs):
        if not pairs:
            return

        pathMap = {'corn ethanol'       : self.cornEthanolUsaAbs,
                   'cellulosic ethanol' : self.cellEthanolUsaAbs,
                   'FT biofuels'        : self.ftBiofuelsUsaAbs}

        fuels = pathMap.keys()

        assert fuel in fuels, 'setBiofuelRefiningNonEnergyCostUSA: Fuel must be one of %s' % fuels

        _echo("Set US %s non-energy-cost to %s" % (fuel, pairs))

        prefix = "//stub-technology[@name='%s']" % fuel
        suffix = "/minicam-non-energy-input[@name='non-energy']/input-cost"

        abspath = pathMap[fuel]
        args = [abspath]
        for year, price in pairs:
            args += ['-u',
                     prefix + ("/period[@year='%s']" % year) + suffix,
                     '-v', price]
        xmlEdit(*args)

    def setCornEthanolCoefficientsUSA(self, cornCoef, gasCoef=None, elecCoef=None):
        '''
        Set corn ethanol performance coefficients: (regional) corn, gas, and electricity
        required per GJ of ethanol. Modified from superclass version to operate on
        biofuelTechUSA.xml.
        '''
        _echo("Set US corn ethanol coefficients for %s (corn=%s, gas=%s, elec=%s)" % \
             (self.name, cornCoef, gasCoef, elecCoef))

        # Corn input is in elements extracted from global-technology-database in energy-xml/en_supply.xml
        cornCoefXpath = '//stub-technology[@name="regional corn for ethanol"]/period[@year>=2015]/minicam-energy-input[@name="Corn"]/coefficient'

        args = [self.cornEthanolUsaAbs, '-u', cornCoefXpath, '-v', cornCoef]

        xpath = '//stub-technology[@name="corn ethanol"]/period[@year>=2015]/minicam-energy-input[@name="%s"]/coefficient'

        if gasCoef:
            gasCoefXpath  = xpath % 'wholesale gas'
            args.extend(['-u', gasCoefXpath,  '-v', gasCoef])

        if elecCoef:
            elecCoefXpath = xpath % 'elect_td_ind'
            args.extend(['-u', elecCoefXpath,  '-v', elecCoef])

        xmlEdit(*args)
        # config update handled in localize...()

    def setCellEthanolBiomassCoefficientsUSA(self, tuples):

        _echo("Set US cellulosic ethanol biomass coefficients for %s" % self.name)

        prefix = "//stub-technology[@name='cellulosic ethanol']"
        suffix = "minicam-energy-input[@name='regional biomass']/coefficient"

        args = [self.cellEthanolUsaAbs]

        for year, coef in tuples:
            args += ['-u', "%s/period[@year='%s']/%s" % (prefix, year, suffix),
                     '-v', str(coef)]

        xmlEdit(*args)
        # config update handled in localize...()
