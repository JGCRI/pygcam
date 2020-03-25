from pygcam.log import getLogger

_logger = getLogger(__name__)

# Templates
Policy_year_template = """
      <policy-portfolio-standard name="{policy}">
        <market>{market}</market>
        <policyType>RES</policyType>
        <constraint year="{year}">1</constraint>
      </policy-portfolio-standard>"""

# stub-tech wrapped in <supplysector name="x"><subsector name="y"><stub-technology...
Supply_year_template = """
            <period year="{year}">
              <minicam-energy-input name="{policy}">
                <coefficient>{coefficient}</coefficient>
                <market-name>{market}</market-name>
              </minicam-energy-input>{secondaryInput}
            </period>"""

SecondaryInput_template = """
              <res-secondary-output name="{policy}">
                <output-ratio>1</output-ratio>
                <pMultiplier>1</pMultiplier>
              </res-secondary-output>"""

Subsector_template = """
        <subsector name="{subsector}">{technologyElts}
        </subsector>"""
        
Technology_template = """
          <stub-technology name="{technology}">{periodElts}
          </stub-technology>"""

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

def emit_supply_year(market, year, policy, coefficient, secondaryInput):
    return Supply_year_template.format(market=market, year=year, policy=policy,
                                       coefficient=coefficient,
                                       secondaryInput=secondaryInput)

def emit_subsector(subsector, technologyEltList):
    technologyElts = ''.join(technologyEltList)
    return Subsector_template.format(subsector=subsector, technologyElts=technologyElts)

def emit_technology(technology,periodEltList):
    periodElts = ''.join(periodEltList)
    return Technology_template.format(technology=technology,
                                     periodElts=periodElts)

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

def generate_building_elec_xml(csv_path, xml_path):
    import pandas as pd
    from collections import OrderedDict

    _logger.debug("Reading '%s'", csv_path)
    df = pd.read_csv(csv_path, index_col=None, skiprows=0)

    year_cols = [col for col in df.columns if col.isdigit()]
    sort_cols = ['region', 'sector', 'subsector','technology']
    df.sort_values(by=sort_cols, inplace=True)

    region_dict = {}
    market_dict = {}    # market name by region

    def subdict(d, key):
        if key not in d:
            d[key] = {}
        return d[key]

    # create hierarchical dict struct from dataframe
    for (idx, row) in df.iterrows():
        market_dict[row.region] = row.region
        sector_dict    = subdict(region_dict, row.region)
        subsector_dict = subdict(sector_dict, row.sector)
        technology_dict = subdict(subsector_dict, row.subsector)
        period_dict    = subdict(technology_dict, row.technology)
        for col in year_cols:
            period_dict[col] = row[col]

    _logger.info("Writing '%s'", xml_path)
    with open(xml_path, 'w') as f:

        policy_elts = OrderedDict()
        region_elts = []
        for (region, sector_dict) in region_dict.items():
            market = market_dict[region]

            supplysector_elts = []
            for (sector, subsector_dict) in sector_dict.items():

                subsector_elts = []
                for (subsector, technology_dict) in subsector_dict.items():
                    
                    technology_elts=[]
                    for (technology, period_dict) in technology_dict.items():
                        
                        period_elts = []
                        for (year, coefficient) in period_dict.items():
                            policy = "BuildingElec-{}-{}-{}".format(market, technology, year)
                            secondaryInput = SecondaryInput_template.format(policy=policy) if subsector == 'electricity' else ''
                            period_elts.append(emit_supply_year(market, year, policy, coefficient, secondaryInput))    

                            policy_elts[policy] = emit_policy_year(market, year, policy)   # avoids duplicates since policy name is reused
                            
                        technology_elts.append(emit_technology(technology,period_elts))

                    subsector_elts.append(emit_subsector(subsector, technology_elts))

                supplysector_elts.append(emit_supply(sector, subsector_elts))

            region_elts.append(emit_region(region, policy_elts.values(), supplysector_elts))

        f.write(emit_policy_file(region_elts))

if __name__ == '__main__':
    dir_path = '/tmp/'
    csv_path = dir_path + 'building-elec-template.csv'
    xml_path = dir_path + 'building-elec-policy.xml'

    generate_building_elec_xml(csv_path, xml_path)
