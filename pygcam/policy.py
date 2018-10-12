from .log import getLogger

_logger = getLogger(__name__)

_yearMarketTemplate = '''            <period year="{year}">
              <{marketType} name="{policyName}"/>
            </period>'''

_technologiesTemplate = '''          <technology name="{technology}">
{markets}
          </technology>'''

_policyMarketTemplate = '''<?xml version="1.0" encoding="UTF-8"?>

<!-- This is a generated constraint file. Edits will be overwritten! -->

<scenario>
  <world>
    <region name="{region}">
      <supplysector name="{sector}">
        <subsector name="{subsector}">
{technologies}
        </subsector>
      </supplysector>
    </region>
  </world>
</scenario>
'''

_yearConstraintTemplate = '''        <constraint year="{year}">{level}</constraint>'''

_policyConstraintTemplate = '''<?xml version="1.0" encoding="UTF-8"?>

<!-- This is a generated constraint file. Edits will be overwritten! -->

<scenario>
  <world>
    <region name="{region}">
      <{policyElement} name="{policyName}">
        <policyType>{policyType}</policyType>
        <market>{market}</market>
        {minPrice}
{constraints}
      </{policyElement}>
    </region>
  </world>
</scenario>
'''

DEFAULT_POLICY_ELT  = 'policy-portfolio-standard'
DEFAULT_POLICY_TYPE = 'subsidy'
DEFAULT_MARKET_TYPE = 'input-subsidy'

def policyMarketXml(policyName, region, sector, subsector, technology, years,
                    marketType=DEFAULT_MARKET_TYPE, pathname=None):
    xmlArgs = {}
    xmlArgs['policyName'] = policyName
    xmlArgs['region']     = region
    xmlArgs['sector']     = sector
    xmlArgs['subsector']  = subsector
    xmlArgs['marketType'] = marketType

    techList = technology if isinstance(technology, (list, tuple)) else [technology]
    techNodes = []

    for tech in techList:
        marketList = [_yearMarketTemplate.format(year=year, marketType=marketType, policyName=policyName) for year in years]
        markets = '\n'.join(marketList)
        techNode = _technologiesTemplate.format(markets=markets, technology=tech)
        techNodes.append(techNode)

    xmlArgs['technologies'] = '\n'.join(techNodes)

    xml = _policyMarketTemplate.format(**xmlArgs)
    if pathname:
        _logger.debug("Writing policy market file: {}".format(pathname))
        with open(pathname, 'w') as f:
            f.write(xml)
    else:
        return xml


def policyConstraintsXml(policyName, region, targets, market=None, minPrice=None,
                         policyElement=DEFAULT_POLICY_ELT, policyType=DEFAULT_POLICY_TYPE,
                         pathname=None):
    xmlArgs = {}
    xmlArgs['policyElement'] = policyElement
    xmlArgs['policyType']    = policyType
    xmlArgs['policyName']    = policyName
    xmlArgs['region']        = region
    xmlArgs['market']        = market or region
    xmlArgs['minPrice']      = '<min-price year="1975" fillout="1">{}</min-price>'.format(minPrice) if minPrice != None else ''

    # Generate annual XML for <constraint year="{year}">{level}</constraint>
    constraints = [_yearConstraintTemplate.format(year=year, level=level) for year, level in targets]
    xmlArgs['constraints'] = '\n'.join(constraints)

    xml = _policyConstraintTemplate.format(**xmlArgs)
    if pathname:
        _logger.debug("Writing policy constraint file: {}".format(pathname))
        with open(pathname, 'w') as f:
            f.write(xml)
    else:
        return xml



# Example:
# policyMarketXml('Corn-Etoh-Floor', 'USA', 'ethanol', 'corn ethanol', 'corn ethanol', list(range(2010, 2051, 10)), pathname="/tmp/mkt.xml")
# policyConstraintsXml('Corn-Etoh-Floor', [(2015, 1.6), (2020, 2.0)], 'USA', minPrice=-100, pathname="/tmp/con.xml")
