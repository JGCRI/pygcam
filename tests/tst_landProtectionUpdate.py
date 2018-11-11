from lxml import etree as ET
from pygcam.config import getParam
from pygcam.utils import pathjoin
from pygcam.landProtection import _protect_land

def main():
    import pandas as pd

    ref_ws = getParam('GCAM.RefWorkspace')
    data_sys = pathjoin(ref_ws, 'input', 'gcam-data-system')
    aglu_xml = pathjoin(data_sys, 'xml', 'aglu-xml')

    protected_land_2_xml = pathjoin(aglu_xml, 'protected_land_input_2.xml')
    protected_land_3_xml = pathjoin(aglu_xml, 'protected_land_input_3.xml')

    parser = ET.XMLParser(remove_blank_text=True, remove_comments=True)

    prot2 = ET.parse(protected_land_2_xml, parser)
    prot3 = ET.parse(protected_land_3_xml, parser)

    regionMap = pd.read_csv(pathjoin(data_sys, '_common', 'mappings', 'GCAM_region_names_32reg.csv'), skiprows=3)
    regionMap.set_index('GCAM_region_ID', inplace=True)
    region = regionMap.region

    # Read the CSV defining the region-wide land protection levels for OTAQ project and
    # apply this anew, verifying that the only differences are way into the decimal places
    otaq_prot_file = pathjoin(ref_ws, 'input', 'otaq-modifications', 'aglu', 'OTAQ_land_protection.csv')
    otaq_prot_df = pd.read_csv(otaq_prot_file)

    otaq_prot_df['region'] = otaq_prot_df['GCAM_region_ID'].map(region)
    otaq_prot_df.drop('GCAM_region_ID', axis=1, inplace=True)
    otaq_prot_df.set_index('region', inplace=True)
    fracs = otaq_prot_df.protect_land_fract

    # protected_land_2 has only UnmanagedPasture
    prot2_dict = {reg: [('UnmanagedPasture', fracs[reg])] for reg in fracs.index}
    _protect_land(prot2, prot2_dict)

    outfile = "/Users/rjp/Downloads/land_prot2_modified.xml"
    print("Writing", outfile)
    prot2.write(outfile, xml_declaration=True, pretty_print=True)

    # protected_land_3 has all the other unmanaged types
    landtypes = ['UnmanagedForest', 'Grassland', 'Shrubland']
    prot3_dict = {reg: [(landtype, fracs[reg]) for landtype in landtypes] for reg in fracs.index}
    _protect_land(prot3, prot3_dict)

    outfile = "/Users/rjp/Downloads/land_prot3_modified.xml"
    print("Writing", outfile)
    prot3.write(outfile, xml_declaration=True, pretty_print=True)

if __name__ == '__main__':
    main()
