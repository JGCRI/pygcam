'''
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from pygcam.utils import getRegionList

fixedTaxTemplate = '                <fixedTax year="{year}">{tax}</fixedTax>'

regionTemplate = '''        <region name="{region}">
            <ghgpolicy name="CO2">
                <market>{market}</market>
            </ghgpolicy>
        </region>'''

ctaxTemplate = '''<?xml version="1.0" encoding="UTF-8"?>
<scenario name="ctax">
    <world>
        <region name="{region}">
            <ghgpolicy name="CO2">
                <market>{market}</market>
                <isFixedTax>1</isFixedTax>
{taxes}
            </ghgpolicy>
        </region>
{regions}
    </world>
</scenario>
'''

def _futureValue(value, years, rate):
     return value * (1+rate)**years

def _futureValuePairs(value, years, rate):
    start = years[0]
    pairs = [(start, value)]
    for y in years[1:]:
        pairs.append((y, _futureValue(value, y - start, rate)))

    return pairs

def genCarbonTax(value, years, rate, regions=None, market='global'):
    '''
    Generate the text of an XML file defining a global carbon tax starting
    at `value` and increasing by `rate` annually. Generate values
    for the give `years`. The first year in `years` is assumed to be
    the year at which the tax starts at `value`.

    :param value: (float) the initial value of the tax ($/tonne)
    :param years: (list(int)) years to set carbon taxes
    :param rate: (float) annual rate of increase.
    :return: (str) the contents of the XML file
    '''
    regionList = []
    regions = regions or getRegionList()

    firstRegion = regions[0]
    for region in regions[1:]:
        regionList.append(regionTemplate.format(region=region, market=market))

    regionsText = "\n".join(regionList)

    pairs = _futureValuePairs(value, years, rate)
    taxesList = []
    for year, value in pairs:
        taxesList.append(fixedTaxTemplate.format(year=year, tax="%.2f" % value))

    taxes = "\n".join(taxesList)
    fileText = ctaxTemplate.format(taxes=taxes, region=firstRegion, market=market, regions=regionsText)
    return fileText

def genCarbonTaxFile(filename, value, startYear=2020, endYear=2100, timestep=5, rate=0.05,
                     regions=None, market='global'):
    '''
    Generate an XML file defining a global carbon tax starting
    at `value` and increasing by `rate` annually. Generate values
    for the years `startYear` to `endYear`, inclusive, and set a new
    tax level every `timestep` years. By default, the tax is applied
    from 2020 to 2100, at 5 year timesteps with an annual increase of 5%.

    :param filename: (str) the path of the XML file to create
    :param value: (float) the initial value of the tax ($/tonne)
    :param startYear: (int) the year in which to establish the carbon tax
    :param endYear: (int) the final year of the carbon tax.
    :param timestep: (int) the number of years after which to update the tax level
    :param rate: (float) annual rate of increase
    :return: none
    '''
    regions = regions or getRegionList()
    years = list(range(startYear, endYear + timestep, timestep))
    text = genCarbonTax(value, years, rate, regions=regions, market=market)
    with open(filename, 'w') as f:
        f.write(text)


header = """<?xml version="1.0" encoding="UTF-8"?>
<scenario>
    <world>"""

footer = """
    </world>
</scenario>
"""

ghgPolicyTemplate = """
            <!-- Linked policies must be read in after the policy to which it links
                 This may be difficult to do in some cases so create an empty CO2
                 policy that ensure there is something to link to. The actual policy
                 can be filled in later.
            -->
            <ghgpolicy name="CO2">
                <market>{market}</market>
            </ghgpolicy>"""

firstRegionTemplate = """
                <price-adjust year="1975" fillout="1">{priceAdjust}</price-adjust>
                <demand-adjust year="1975" fillout="1">{demandAdjust}</demand-adjust>
                <price-unit>1990$/tC</price-unit>
                <output-unit>MTC</output-unit>"""

regionTemplate2 = """
        <region name="{region}">{ghgPolicy}
            <linked-ghg-policy name="CO2_LUC">
                <market>{market}</market>
                <linked-policy>CO2</linked-policy>{firstRegionStuff}
            </linked-ghg-policy>
        </region>"""

#
# Function to generate UCT/FFICT linked tax files
#
# (The following note is from Page Kyle of JGCRI)
#
# The price-adjust is defaulted to 0, meaning that no land carbon
# pricing is used (FFICT). To run with land carbon pricing (UCT), it can
# be set to 1, or really any number, and that number will be multiplied
# by the carbon price in order to determine the magnitude of the land
# carbon subsidy. The demand-adjust is also defaulted to 0, and that
# applies in the case of a CO2 emissions cap, or constraint. The
# question here is whether land use change emissions are added to the
# energy and industrial emissions in meeting the constraint. If 0, the
# constraint only applies to the energy and industrial emissions; if set
# to 1, the policy will also consider the LUC emissions. As with the
# price-adjust, it can also be set to any other numerical value.
#
def genLinkedBioCarbonPolicyFile(filename, market='global', regions=None, forTax=True, forCap=False):
    """
    Create the XML for a linked policy to include LUC CO2 in a CO2 cap or tax policy (or both).
    This function generates the equivalent of any of the 4 files in input/policy/:
    global_ffict.xml               (forTax=False, forCap=False)
    global_ffict_in_constraint.xml (forTax=False, forCap=True)
    global_uct.xml                 (forTax=True,  forCap=False)
    global_uct_in_constraint.xml   (forTax=True,  forCap=True)

    However, unlike those files, the market need not be global, and the set of regions to
    which to apply the policy can be specified.

    :param filename: (str) the pathname of the XML file to create
    :param market: (str) the name of the market for which to create the linked policy
    :param regions: (list of str or None) the regions to apply the policy to, or None
      to indicate all regions.
    :param forTax: (bool) True if the linked policy should apply to a CO2 tax
    :param forCap: (bool) True if the linked policy should apply to a CO2 cap
    :return: none
    """
    regions = regions or getRegionList()

    first = True
    parts = [header]

    priceAdjust  = 1.0 if forTax else 0.0
    demandAdjust = 1.0 if forCap else 0.0
    firstRegionStuff = firstRegionTemplate.format(priceAdjust=priceAdjust, demandAdjust=demandAdjust)
    ghgPolicy = ghgPolicyTemplate.format(market=market)

    for region in regions:
        regionElement = regionTemplate2.format(region=region, market=market,
                                               ghgPolicy=ghgPolicy if first else '',
                                               firstRegionStuff=firstRegionStuff if first else '')
        first = False
        parts.append(regionElement)

    parts.append(footer)
    xml = ''.join(parts)

    with open(filename, 'w') as f:
        f.write(xml)


if __name__ == "__main__":
   genCarbonTaxFile('/tmp/ctax.xml',  10, timestep=10, rate=0.07)
   genCarbonTaxFile('/tmp/ctax2.xml', 15, timestep=5,  rate=0.05, regions=['Canada', 'USA', 'EU-15', 'China'], market='region1')



