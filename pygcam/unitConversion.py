#
# UNIT CONVERSIONS
#
# Pythonized from gcam-data-system/_common/assumptions/unit_conversions.R
#
ones_mil = 1e-6
ones_thous = 1e-3
thous_mil = 1e-3
mil_bil = 1e-3
bil_mil = 1e3
mil_thous = 1e3
bil_thous = 1e6
thous_bil = 1e-6
C_CO2 = 44/12
CO2_C = 12/44

# dollar conversions
USD_1990_2005 = 1.383
USD_1990_2007 = 1.470
USD_1990_2010 = 1.510
USD_1990_1975 = 0.4649
USD_1996_1975 = 0.4049
USD_1997_1975 = 0.3983
USD_1998_1975 = 0.3939
USD_1999_1975 = 0.3883
USD_2000_1975 = 0.380
USD_2001_1975 = 0.3711
USD_2002_1975 = 0.3647
USD_2003_1975 = 0.3571
USD_2004_1975 = 0.3472
USD_2005_1975 = 0.3362
USD_2006_1975 = 0.3257
USD_2007_1975 = 0.317
USD_2008_1975 = 0.3104
USD_2009_1975 = 0.3104

# mass conversions
kg_Mt = 1e-9
t_Mt = 1e-6
kt_Mt = 1e-3
Pg_Tg = 1000
t_kg = 1e3
kg_t = 1e-3
g_kg = 1e-3
t_metric_short = 1000/908

# calorie conversions
Mcal_Pcal = 1e-9
Pcal_Gcal = 1e6
Pcal_Mcal = 1e9

# volume conversions
m3_bm3 = 1e-9
Mm3_km3 = 1e-3

# area conversions
Ha_bm2 = 1e-5
Ha_m2 = 1e4
m2_acre = 1/4046.85
km2_bm2 = 1e-3
bm2_m2 = 1e9
milft2_bm2 = 0.0929/1e3     # million square feet to billion square meters
milft2_m2 = 0.0929 * 1e6
ft2_bm2 = 0.0929/1e9        # square feet to billion square meters
ft2_m2 = 0.0929

# yield conversions
tha_kgm2 = 0.1

# cotton seed and lint conversion
cotton_lint = 0.4

# energy unit conversions
kbbl_bbl = 1000
bbl_tonne_RFO = 1 / 6.66
bbl_tonne_distillate = 1 / 7.46
days_year = 1 / 365.25
year_hours = 8766
tonne_GJ_RFO = 40.87
tonne_GJ_distillate = 42.91
GJ_EJ = 1e-9
kwh_GJ = 0.0036
TWh_EJ = 3.6e-3
GWh_EJ = 3.6e-6
MWh_EJ = 3.6e-9
MWh_GJ = 3.6
MJ_btu = 947.777
EJ_GJ = 1e9
btu_kJ = 1.0551

# from billion barrels a day to EJ per year
bbld_EJyr = 6.119 * 365.25 * 1e-3

Tbtu_EJ = 0.0010551         # trillion btu to EJ
kbtu_EJ = 1.0551e-12        # thousand btu to EJ
