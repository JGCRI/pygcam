'''
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from .config import pathjoin
from .log import getLogger
from .xmlEditor import XMLEditor, xmlEdit, extractStubTechnology, callableMethod, ENERGY_TRANSFORMATION_TAG

_logger = getLogger(__name__)

# TBD: move to constants.py?
REFINING_SECTOR = 'refining'
BIOMASS_LIQUIDS = 'biomass liquids'

# Technology names
TECH_CORN_ETHANOL       = 'corn ethanol'
TECH_SUGARCANE_ETHANOL  = 'sugar cane ethanol'
TECH_CELLULOSIC_ETHANOL = 'cellulosic ethanol'
TECH_FT_BIOFUELS        = 'FT biofuels'
TECH_BIODIESEL          = 'biodiesel'
TECH_GTL                = 'gas to liquids'
TECH_CTL                = 'coal to liquids'
TECH_OIL_REFINING       = 'oil refining'

ENERGY_SUPPLY_TAG = "energy_supply"
RESBIO_INPUT_TAG  = "residue_bio"
RESOURCES_TAG     = "resources"
AG_BASE_TAG       = "ag_base"
LAND_INPUT3_TAG   = "land3"

class BioenergyEditor(XMLEditor):
    """
    BioenergyEditor adds knowledge of biomass and biofuels.
    """
    def __init__(self, baseline, scenario, xmlOutputRoot, xmlSourceDir, workspaceDir,
                 groupDir, srcGroupDir, subdir, parent=None, mcsMode=None, cleanXML=True):
        super(BioenergyEditor, self).__init__(baseline, scenario, xmlOutputRoot, xmlSourceDir,
                                              workspaceDir, groupDir, srcGroupDir, subdir,
                                              parent=parent, mcsMode=mcsMode, cleanXML=cleanXML)

        # TBD: unclear whether this is useful or general
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

    @callableMethod
    def adjustResidueSupply(self, loTarget, loPrice, loFract, hiTarget, hiPrice, hiFract, target):
        """
        Change supply curves for residues, as per arguments. loTarget and hiTarget identify
        the price to match in the XML file; loPrice and hiPrice are the new prices to set;
        loFract and hiFract are the new fractions to assign to these prices.
        Target must be one of {all, us-crops, us-corn, global-corn}
        Note that the standard reference supply curve for residue is:
        0% at 1975$0; 25% at $1.2; 65% at $1.5; 100% at $10.
        """
        _logger.info("Adjust residue supply curves for %s (%s, %s:%s@%s, %s:%s@%s)" % \
             (self.name, target, loTarget, loFract, loPrice, hiTarget, hiFract, hiPrice))

        # Create modified version of resbio_input.xml and modify config to use it
        resbioFileRel, resbioFileAbs = self.getLocalCopy(RESBIO_INPUT_TAG)

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

        pairs = [(fractHarvested + "[@price='%s']" % loTarget, loFract),
                 (fractHarvested + "[@price='%s']" % hiTarget, hiFract),
                 (fractHarvested + "[@price='%s']/@price" % loTarget, loPrice),
                 (fractHarvested + "[@price='%s']/@price" % hiTarget, hiPrice)]

        xmlEdit(resbioFileAbs, pairs)
        self.updateScenarioComponent("residue_bio", resbioFileRel)

    @callableMethod
    def setMswParameter(self, region, parameter, value):
        resourcesFileRel, resourcesFileAbs = self.getLocalCopy(RESOURCES_TAG)

        xpath = "//region[@name='%s']/renewresource/smooth-renewable-subresource[@name='generic waste biomass']/%s" % (region, parameter)

        xmlEdit(resourcesFileAbs, [(xpath, value)])

        self.updateScenarioComponent("resources", resourcesFileRel)

    @callableMethod
    def regionalizeBiomassMarket(self, region):
        _logger.info("Regionalize %s biomass market for %s" % (region, self.name))

        resourcesFileRel, resourcesFileAbs = self.getLocalCopy(RESOURCES_TAG)

        xmlEdit(resourcesFileAbs, [("//region[@name='%s']/renewresource[@name='biomass']/market" % region, region)])
        self.updateScenarioComponent("resources", resourcesFileRel)

        agForPastBioFileRel, agForPastBioFileAbs = self.getLocalCopy(AG_BASE_TAG)

        xmlEdit(agForPastBioFileAbs, [("//region[@name='%s']/AgSupplySector[@name='biomass']/market" % region, region)])
        self.updateScenarioComponent("ag_base", agForPastBioFileRel)

    # TBD: generalize this as setInputCoefficients(self, (('wholesale gas', x), ('elect_td_ind', y)))
    @callableMethod
    def setCornEthanolCoefficients(self, cornCoef, gasCoef=None, elecCoef=None):
        '''
        Set corn ethanol performance coefficients, i.e., the (regional) corn, gas, and
        electricity required per GJ of ethanol. These appear in two files, so we edit
        them both.
        '''
        _logger.info("Set global corn ethanol coefficients: corn=%s, gas=%s, elec=%s" % \
             (cornCoef, gasCoef, elecCoef))

        # XPath applies to file energy-xml/en_supply.xml
        cornCoefXpath = '//technology[@name="regional corn for ethanol"]/period[@year>=2015]/minicam-energy-input[@name="Corn"]/coefficient'

        enSupplyFileRel, enSupplyFileAbs = self.getLocalCopy(ENERGY_SUPPLY_TAG)

        xmlEdit(enSupplyFileAbs, [(cornCoefXpath, cornCoef)])

        self.updateScenarioComponent(ENERGY_SUPPLY_TAG, enSupplyFileRel)

        if gasCoef or elecCoef:
            enTransFileRel, enTransFileAbs = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)
            pairs = []
            xpath = '//technology[@name="corn ethanol"]/period[@year>=2015]/minicam-energy-input[@name="%s"]/coefficient'

            if gasCoef:
                gasCoefXpath  = xpath % 'wholesale gas'
                pairs.append((gasCoefXpath, gasCoef))

            if elecCoef:
                elecCoefXpath = xpath % 'elect_td_ind'
                pairs.append((elecCoefXpath, elecCoef))

            xmlEdit(enTransFileAbs, pairs)
            self.updateScenarioComponent("energy_transformation", enTransFileRel)

    # deprecated?
    @callableMethod
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
        self.setEnergyTechnologyCoefficients(self, BIOMASS_LIQUIDS, fuelName, 'regional biomass', pairs)

    # TBD: generalize as setIsNewTechnology() ?
    @callableMethod
    def purposeGrownOffInRegion(self, region):
        '''
        Turn off the "isNewTechnology" flag for all land-leaf nodes to turn off
        purpose-grown biomass. The line(s) we need to edit in land_input_3.xml is:
        <isNewTechnology fillout="1" year="2020">1</isNewTechnology>
        '''
        _logger.info("Turn off purpose-grown biomass technology in %s for %s" % (region, self.name))

        landInput3Rel, landInput3Abs = self.getLocalCopy(LAND_INPUT3_TAG)

        if region == 'global':
             region='*'

        xmlEdit(landInput3Abs, [("//region[@name='%s']//isNewTechnology[@year='2020']" % region, 0)])
        self.updateScenarioComponent(LAND_INPUT3_TAG, landInput3Rel)

    #
    # Various methods that operate on the USA specifically
    #
    # TBD: make region an optional parameter in these; fix callers
    #
    @callableMethod
    def adjustForestResidueSupply(self, region, loPrice, loFract, hiPrice, hiFract):
        '''
        Change supply curves for forest residues in the USA only. loPrice and hiPrice
        are the new prices to set; loFract and hiFract are the new fractions to assign
        to these prices.
        '''
        _logger.info("Adjust forest residue supply curves for %s" % self.name)

        # Create modified version of resbio_input.xml and modify config to use it
        resbioFileRel, resbioFileAbs = self.getLocalCopy(RESBIO_INPUT_TAG)

        # Forest residue appears in two places. First, operate on AgSupplySector "Forest"
        xPrefix = "//region[@name='%s']/AgSupplySector[@name='Forest']/AgSupplySubsector" % region
        fractHarvested = xPrefix + "/AgProductionTechnology/period[@year>=2015]/residue-biomass-production/fract-harvested"

        pairs = [(fractHarvested + "[@price='1.2']/@price", loPrice),
                 (fractHarvested + "[@price='1.5']/@price", hiPrice),
                 (fractHarvested + "[@price='1.2']", loFract),
                 (fractHarvested + "[@price='1.5']", hiFract)]
        xmlEdit(resbioFileAbs, pairs)

        # Do the same for supplysector="NonFoodDemand_Forest"
        xPrefix = "//region[@name='%s']/supplysector[@name='NonFoodDemand_Forest']/subsector[@name='Forest']/stub-technology[@name='Forest']" % region
        fractHarvested = xPrefix + "/period[@year>=2015]/residue-biomass-production/fract-harvested"

        pairs = [("%s[@price='1.2']/@price" % fractHarvested, loPrice),
                 ("%s[@price='1.5']/@price" % fractHarvested, hiPrice),
                 ("%s[@price='1.2']" % fractHarvested, loFract),
                 ("%s[@price='1.5']" % fractHarvested, hiFract)]
        xmlEdit(resbioFileAbs, pairs)

        self.updateScenarioComponent("residue_bio", resbioFileRel)

    #
    # Methods to operate in USA only on technologies extracted from global-technology-database
    #
    # TBD: generalize this?
    @callableMethod
    def setCellEthanolShareWeightUSA(self, year, shareweight):
        '''
        Create modified version of cellEthanolUSA.xml with the given share-weight
        for the given fuel in the given year.
        '''
        _logger.info("Set US share-weight to %s for cellulosic ethanol in %s for %s" % (shareweight, year, self.name))

        yearConstraint = ">= 2015" if year == 'all' else ("=" + year)

        xmlEdit(self.cellEthanolUsaAbs,
                [("//stub-technology[@name='cellulosic ethanol']/period[@year%s]/share-weight" % yearConstraint,
                  shareweight)])

        self.updateScenarioComponent("cell-etoh-USA", self.cellEthanolUsaRel)

    @callableMethod
    def localizeCornEthanolTechnologyUSA(self):
        '''
        Copy the stub-technology for corn ethanol to CornEthanolUSA.xml and CornEthanolUSA2.xml
        so they can be manipulated in the US only.
        '''
        _logger.info("Add corn ethanol stub technology in USA")

        enTransFileRel, enTransFileAbs = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)
        extractStubTechnology('USA', enTransFileAbs, self.cornEthanolUsaAbs,  REFINING_SECTOR, BIOMASS_LIQUIDS, 'corn ethanol')
        extractStubTechnology('USA', enTransFileAbs, self.cornEthanolUsaAbs2, REFINING_SECTOR, BIOMASS_LIQUIDS, 'corn ethanol', fromRegion=True)

        # Insert "2" right after energy_transformation, then "1" right after energy_transformation,
        # so they end up in order "1" then "2".
        self.insertScenarioComponent('corn-etoh-USA2', self.cornEthanolUsaRel2, 'energy_transformation')
        self.insertScenarioComponent('corn-etoh-USA1', self.cornEthanolUsaRel,  'energy_transformation')

    @callableMethod
    def localizeCellEthanolTechnologyUSA(self):
        '''
        Same as corn ethanol above, but for cellulosic ethanol
        '''
        _logger.info("Add cellulosic ethanol stub-technology in USA")

        enTransFileRel, enTransFileAbs = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)
        extractStubTechnology('USA', enTransFileAbs, self.cellEthanolUsaAbs,  REFINING_SECTOR, BIOMASS_LIQUIDS, 'cellulosic ethanol')

        self.insertScenarioComponent('cell-etoh-USA', self.cellEthanolUsaRel, 'energy_transformation')

    @callableMethod
    def localizeFtBiofuelsTechnologyUSA(self):
        '''
        Same as cellulosic ethanol above
        '''
        _logger.info("Add FT biofuels stub-technology in USA")

        enTransFileRel, enTransFileAbs = self.getLocalCopy(ENERGY_TRANSFORMATION_TAG)
        extractStubTechnology('USA', enTransFileAbs, self.ftBiofuelsUsaAbs,  REFINING_SECTOR, BIOMASS_LIQUIDS, 'FT biofuels')

        self.insertScenarioComponent('FT-biofuels-USA', self.ftBiofuelsUsaRel, 'energy_transformation')

    # TBD: translate pairs to allow ranges to be specified
    @callableMethod
    def setBiofuelRefiningNonEnergyCostUSA(self, fuel, pairs):
        if not pairs:
            return

        pathMap = {'corn ethanol'       : self.cornEthanolUsaAbs,
                   'cellulosic ethanol' : self.cellEthanolUsaAbs,
                   'FT biofuels'        : self.ftBiofuelsUsaAbs}

        fuels = pathMap.keys()

        assert fuel in fuels, 'setBiofuelRefiningNonEnergyCostUSA: Fuel must be one of %s' % fuels

        _logger.info("Set US %s non-energy-cost to %s" % (fuel, pairs))

        prefix = "//stub-technology[@name='%s']" % fuel
        suffix = "/minicam-non-energy-input[@name='non-energy']/input-cost"

        pairs = []
        for year, price in pairs:
           pairs.append((prefix + ("/period[@year='%s']" % year) + suffix, price))

        abspath = pathMap[fuel]
        xmlEdit(abspath, pairs)

    @callableMethod
    def setCornEthanolCoefficientsUSA(self, cornCoef, gasCoef=None, elecCoef=None):
        '''
        Set corn ethanol performance coefficients: (regional) corn, gas, and electricity
        required per GJ of ethanol. Modified from superclass version to operate on
        biofuelTechUSA.xml.
        '''
        _logger.info("Set US corn ethanol coefficients for %s (corn=%s, gas=%s, elec=%s)" % \
             (self.name, cornCoef, gasCoef, elecCoef))

        # Corn input is in elements extracted from global-technology-database in energy-xml/en_supply.xml
        cornCoefXpath = '//stub-technology[@name="regional corn for ethanol"]/period[@year>=2015]/minicam-energy-input[@name="Corn"]/coefficient'

        pairs = [(cornCoefXpath, cornCoef)]

        xpath = '//stub-technology[@name="corn ethanol"]/period[@year>=2015]/minicam-energy-input[@name="%s"]/coefficient'
        if gasCoef:
            gasCoefXpath  = xpath % 'wholesale gas'
            pairs.append((gasCoefXpath,  gasCoef))

        if elecCoef:
            elecCoefXpath = xpath % 'elect_td_ind'
            pairs.append((elecCoefXpath,  elecCoef))

        xmlEdit(self.cornEthanolUsaAbs, pairs)
        # config update handled in localize...()

    @callableMethod
    def setCellEthanolBiomassCoefficientsUSA(self, tuples):

        _logger.info("Set US cellulosic ethanol biomass coefficients for %s" % self.name)

        prefix = "//stub-technology[@name='cellulosic ethanol']"
        suffix = "minicam-energy-input[@name='regional biomass']/coefficient"

        pairs = []
        for year, coef in tuples:
            pairs.append(("%s/period[@year='%s']/%s" % (prefix, year, suffix), coef))

        xmlEdit(self.cellEthanolUsaAbs, pairs)
        # config update handled in localize...()
