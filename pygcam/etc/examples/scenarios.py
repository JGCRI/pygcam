import pandas as pd
from pygcam.config import pathjoin
from pygcam.log import getLogger
from pygcam.xmlEditor import XMLEditor, callableMethod

_logger = getLogger(__name__)

class MyCustomClass(XMLEditor):
    '''
    XML editing subclass to extend XML setup functionality
    '''
    @callableMethod
    def updateEnergyCosts(self, startYear, endYear, techs=None):
        """
        Use updated non-energy-costs provided by Matteo.
        """
        techs = techs or ('oil refining', 'coal to liquids', 'gas to liquids',
                          'corn ethanol', 'biodiesel', 'sugar cane ethanol',
                          'cellulosic ethanol', 'FT biofuels')

        _logger.debug('Updating energy costs for %s, %s-%s', techs, startYear, endYear)

        def getCost(df, tech):
            query = f'technology=="{tech}" and year >= {startYear} and year <= {endYear}'
            df = df.query(query)
            df.set_index('year', inplace=True)
            costs = df['input.cost']
            return costs

        filename = pathjoin(self.xmlSourceDir, 'baseline', 'L222.GlobalTechCost_en-Modified.csv')
        df = pd.read_csv(filename, skiprows=4)

        for tech in techs:
            # The three fossil technologies are in their own subsectors of the
            # same name. The rest are biomass liquids.
            subSector = tech if tech in ['oil refining', 'coal to liquids', 'gas to liquids'] else 'biomass liquids'
            costs = getCost(df, tech)
            self.setGlobalTechNonEnergyCost('refining', subSector, tech, costs)

