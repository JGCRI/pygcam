'''
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from pygcam.constants import GCAM_32_REGIONS

fixedTaxTemplate = '                <fixedTax year="{year}">{tax}</fixedTax>'

regionTemplate = '''        <region name="{region}">
            <ghgpolicy name="CO2">
                <market>{market}</market>
            </ghgpolicy>
        </region>'''

ctaxTemplate = '''
<?xml version="1.0" encoding="UTF-8"?>
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

def genCarbonTax(value, years, rate, regions=GCAM_32_REGIONS, market='global'):
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

def genCarbonTaxFile(filename, value, years, rate, regions=GCAM_32_REGIONS, market='global'):
   '''
   Generate an XML file defining a global carbon tax starting
   at `value` and increasing by `rate` annually. Generate values
   for the give `years`. The first year in `years` is assumed to be
   the year at which the tax starts at `value`.

   :param filename: (str) the path of the XML file to create
   :param value: (float) the initial value of the tax ($/tonne)
   :param years: (list(int)) years to set carbon taxes
   :param rate: (float) annual rate of increase.
   :return: none
   '''
   with open(filename, 'w') as f:
      text = genCarbonTax(value, years, rate, regions=regions, market=market)
      f.write(text)


if __name__ == "__main__":
   genCarbonTaxFile('/tmp/ctax.xml',  10, range(2020, 2110, 10), 0.05)
   genCarbonTaxFile('/tmp/ctax2.xml', 15, range(2020, 2110, 10), 0.05, regions=['Canada', 'USA', 'EU-15', 'China'], market='region1')



