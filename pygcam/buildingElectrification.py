from pygcam.log import getLogger

_logger = getLogger(__name__)

# Templates
Policy_year_template = """
      <policy-portfolio-standard name="{year} {policy}">
        <market>{market}</market>
        <policyType>RES</policyType>
        <constraint year="{year}">1</constraint>
      </policy-portfolio-standard>"""

# stub-tech wrapped in <supplysector name="x"><subsector name="y"><stub-technology...
Supply_year_template = """
            <period year="{year}">
              <minicam-energy-input name="{year} {policy}">
                <coefficient>{coefficient}</coefficient>
                <market-name>{market}</market-name>
              </minicam-energy-input>
              <res-secondary-output name="{year} {policy}">
                <output-ratio>{outputRatio}</output-ratio>
                <pMultiplier>1</pMultiplier>
              </res-secondary-output>
            </period>"""

Technology_template = """
          <stub-technology name="{technology}">{periodElts}
          </stub-technology>"""

Subsector_template = """
        <subsector name="{subsector}">{technologyElts}
        </subsector>"""

Supply_template = """
      <supplysector name="{sector}">{subsectorElts}
      </supplysector>"""

Region_template = """
    <region name="{region}">{policyElts}
      {supplysectorElts}
    </region>"""

Policy_file_template = """<?xml version="1.0" encoding="UTF-8"?>
<scenario>
  <world>{regionElts}
  </world>
</scenario>
"""

def emit_policy_year(market, year, policy):
    return Policy_year_template.format(market=market, year=year, policy=policy)

def emit_supply_year(market, year, policy, coefficient, outputRatio=1):
    return Supply_year_template.format(market=market, year=year, policy=policy,
                                       coefficient=coefficient, outputRatio=outputRatio)

def emit_technology(technology, periodEltList):
    periodElts = ''.join(periodEltList)
    return Technology_template.format(technology=technology, periodElts=periodElts)

def emit_subsector(subsector, techEltList):
    technologyElts = ''.join(techEltList)
    return Subsector_template.format(subsector=subsector, technologyElts=technologyElts)

def emit_supply(sector, subsectorEltList):
    subsectorElts = ''.join(subsectorEltList)
    return Supply_template.format(sector=sector, subsectorElts=subsectorElts)

def emit_region(region, policyEltList, supplysectorEltList):
    policyElts = ''.join(policyEltList)
    supplysectorElts = ''.join(supplysectorEltList)
    return Region_template.format(region=region, policyElts=policyElts,
                                  supplysectorElts=supplysectorElts)

def emit_policy_file(regionEltList):
    regionElts = ''.join(regionEltList)
    return Policy_file_template.format(regionElts=regionElts)

def csv_to_xml(csv_path, xml_path):
    import pandas as pd
    from collections import OrderedDict

    _logger.debug("Reading '%s'", csv_path)
    df = pd.read_csv(csv_path, index_col=None, skiprows=0)

    sort_cols = ['region', 'market', 'policy', 'supplysector', 'subsector',
                 'technology', 'year', 'coefficient']
    df.sort_values(by=sort_cols, inplace=True)

    top_dict = {}

    def subdict(d, key):
        if key not in d:
            d[key] = {}
        return d[key]

    # create hierarchical dict struct from dataframe
    for (idx, row) in df.iterrows():
        region_dict  = subdict(top_dict, row.region)
        market_dict  = subdict(region_dict, row.market)
        policy_dict  = subdict(market_dict, row.policy)
        supply_dict  = subdict(policy_dict, row.supplysector)
        subsect_dict = subdict(supply_dict, row.subsector)
        technol_dict = subdict(subsect_dict, row.technology)
        technol_dict[row.year] = row.coefficient

    _logger.info("Writing '%s'", xml_path)
    with open(xml_path, 'w') as f:

        policy_elts = OrderedDict()
        region_elts = []
        for (region, market_dict) in top_dict.items():

            for (market, policy_dict) in market_dict.items():

                supplysector_elts = []
                for (policy, supply_dict) in policy_dict.items():
                    for (supplysector, subsect_dict) in supply_dict.items():

                        subsector_elts = []
                        for (subsector, technology_dict) in subsect_dict.items():

                            technology_elts = []
                            for (technology, period_dict) in technology_dict.items():

                                period_elts = []
                                for (year, coefficient) in period_dict.items():
                                    period_elts.append(emit_supply_year(market, year, policy, coefficient))

                                    policy_name = "{} {}".format(policy, year)
                                    policy_elts[policy_name] = emit_policy_year(market, year, policy)   # avoids duplicates

                                technology_elts.append(emit_technology(technology, period_elts))

                            subsector_elts.append(emit_subsector(subsector, technology_elts))

                        supplysector_elts.append(emit_supply(supplysector, subsector_elts))

            region_elts.append(emit_region(region, policy_elts.values(), supplysector_elts))

        f.write(emit_policy_file(region_elts))

if __name__ == '__main__':
    dir_path = '/Users/rjp/Downloads/'
    csv_path = dir_path + 'building-elec-sample.csv'
    xml_path = dir_path + 'building-elec-sample.xml'

    csv_to_xml(csv_path, xml_path)
