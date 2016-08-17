#
# UNIT CONVERSIONS
#
# Pythonized from gcam-data-system/_common/assumptions/unit_conversions.R
#

# basic SI unit relationships
k_to_ones = 1e3
ones_to_k = 1e-3

M_to_ones = 1e6
ones_to_M = 1e-6

M_to_k = 1e3
k_to_M = 1e-3

G_to_ones = 1e9
ones_to_G = 1e-9

G_to_k = 1e6
k_to_G = 1e-6

G_to_M = 1e3
M_to_G = 1e-3

P_to_M = 1e9
M_to_P = 1e-9

P_to_G = 1e6
G_to_P = 1e-6

P_to_T = 1e3
T_to_P = 1e-3

E_to_G = 1e9
G_to_E = 1e-9

# Carbon <--> CO2
C_to_CO2 = 44./12
CO2_to_C = 12./44

# mass conversions
kg_to_g = k_to_ones
g_to_kg = ones_to_k

Mg_to_kg = M_to_k
kg_to_Mg = k_to_M

Mg_to_ton = 1000./908
ton_to_Mg = 0.908

Mt_to_ton = Mg_to_ton   # aliases
ton_to_Mt = ton_to_Mg

Pg_to_Tg = P_to_T
Tg_to_Pg = T_to_P

# calorie conversions
Pcal_to_Mcal = P_to_M
Mcal_to_Pcal = M_to_P

Pcal_to_Gcal = P_to_G
Gcal_to_Pcal = G_to_P

# volume conversions
m3_to_Gm3 = 1e-9
m3_to_bm3 = m3_to_Gm3

km3_to_Mm3 = 1e3
Mm3_to_km3 = 1e-3

# area conversions
bm2_to_ha = 1e5
ha_to_bm2 = 1e-5

ha_to_m2 = 1e4
m2_to_ha = 1e-4

acre_to_m2 = 4046.85
m2_to_acre = 1/acre_to_m2

Gm2_to_km2 = G_to_k
bm2_to_km2 = G_to_k
km2_to_Gm2 = k_to_G
km2_to_bm2 = k_to_G

bm2_to_m2 = G_to_ones
Gm2_to_m2 = G_to_ones

ft2_to_m2 = 0.0929
Mft2_to_m2 = ft2_to_m2 * M_to_ones

Mft2_to_Gm2 = ft2_to_m2 * M_to_G    # million square feet to billion square meters
Mft2_to_bm2 = Mft2_to_Gm2

ft2_to_Gm2 = ft2_to_m2 * ones_to_G  # square feet to billion square meters
ft2_to_bm2 = ft2_to_Gm2

# yield conversions
Mg_per_ha_to_kg_per_m2 = M_to_k / ha_to_m2

# time
year_to_day = 365.25
day_to_year = 1 / year_to_day

day_to_hour = 24
hour_to_day = 1. / day_to_hour
year_to_hour = year_to_day * day_to_hour

# energy unit conversions
kbbl_to_bbl = k_to_ones
bbl_to_tonne_RFO = 1 / 6.66
bbl_to_tonne_distillate = 1 / 7.46

tonne_to_GJ_RFO = 40.87
tonne_to_GJ_distillate = 42.91

GJ_to_EJ = G_to_E
EJ_to_GJ = E_to_G

kWh_to_MJ = 3.6
MWh_to_GJ = kWh_to_MJ

kWh_to_GJ = 0.0036
kWh_to_GJ = kWh_to_MJ * M_to_G

MWh_to_EJ = 3.6e-9
GWh_to_EJ = 3.6e-6
TWh_to_EJ = 3.6e-3

btu_to_kJ = 1.0551
kJ_to_btu = 1 / btu_to_kJ

MJ_to_btu = kJ_to_btu * M_to_k
btu_to_MJ = 1 / MJ_to_btu

MMbtu_to_MJ = M_to_ones * btu_to_MJ
MJ_to_MMbtu = 1 / MMbtu_to_MJ

MJ_to_MMBtu = MJ_to_MMbtu   # alternate spelling
MMBtu_to_MJ = MMbtu_to_MJ

quad_to_EJ = btu_to_kJ
EJ_to_quad = 1 / quad_to_EJ

Tbtu_to_EJ = 0.0010551         # trillion btu to EJ
kbtu_to_EJ = 1.0551e-12        # thousand btu to EJ

# from billion barrels a day to EJ per year (comment on original was wrong: bbl = barrel, not billion bbl)
# bbl_per_day_to_EJ_per_yr = 6.119 * 365.25 * 1e-3

# dollar inflation/deflation
USD_1990_to_2005 = 1.383
USD_1990_to_2007 = 1.470
USD_1990_to_2010 = 1.510
USD_1990_to_1975 = 0.4649
USD_1996_to_1975 = 0.4049
USD_1997_to_1975 = 0.3983
USD_1998_to_1975 = 0.3939
USD_1999_to_1975 = 0.3883
USD_2000_to_1975 = 0.380
USD_2001_to_1975 = 0.3711
USD_2002_to_1975 = 0.3647
USD_2003_to_1975 = 0.3571
USD_2004_to_1975 = 0.3472
USD_2005_to_1975 = 0.3362
USD_2006_to_1975 = 0.3257
USD_2007_to_1975 = 0.317
USD_2008_to_1975 = 0.3104
USD_2009_to_1975 = 0.3104
