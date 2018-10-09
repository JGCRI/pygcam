#
# UNIT CONVERSIONS
#
# Pythonized from gcam-data-system/_common/assumptions/unit_conversions.R
#

'''
This module includes a large number of pre-defined symbolic constants to
support unit conversion. Values can be accessed, and additional values added,
programmatically via this API.

Use ``getUnits()`` to get the singleton instance of the ``UnitNamespace``
class, and set values prior to use in, say, the API to the :doc:`pygcam.chart`
module. For example,

  .. code-block:: python

     from pygcam.units import getUnits

     u = getUnits()
     u.NewConstant = 123.456
'''

from .error import PygcamException
from .log import getLogger
from .utils import coercible

_logger = getLogger(__name__)

def getUnits(other=None):
    """
    Returns a singleton instance of a private namespace-like class
    that can set and get unit conversions.

    :param other: (dict-like) an object supporting the items() method
        that returns pairs of (name, value) that are added to the built-in
        unit conversion look-up table. Note that elements in `other` will
        overwrite existing entries of the same name.
    :return: (UnitNamespace) returns a singleton instance, i.e., subsequent
        calls will return the same object, though additional names can be
        passed on each call.
    """
    units = UnitNamespace.getUnits()

    if other:
        for name, value in other.items():
            units.set(name, value)

    return units

class UnitNamespace(object):
    """
    UnitNamespace is a namespace-like class that stores the names of
    unit conversions, allowing these names to be used in the GCAM tool
    "chart" sub-command to specify values to multiply or divide by to
    convert units for plotting. Names can be set and accessed using
    '.' notation. That is, after calling ``u = getUnits()``, you
    can access a conversion named, for example, 'MJ_to_EJ' as
    ``u.MJ_to_EJ``, or set a new value for, say, 'foo' simply by
    setting ``u.foo = value``.

    Note that the getUnits() method should generally be used rather
    than calling UnitNamespace() directly to ensure that the single
    instance of the class is returned.
    """
    instance = None
    conversions = {}        # not an ivar since we hijack __getattr__

    @classmethod
    def getUnits(cls):
        if not cls.instance:
            cls.instance = cls()

        return cls.instance

    def __getattr__(self, name):
        return self.get(name, raiseError=True)

    def __setattr__(self, name, value):
        self.conversions[name] = value

    def get(self, name, raiseError=True):
        """
        Get the value of a variable defined in the unitConversion module.
        Basically an "eval" operation.

        :param name: (str) the name of a variable to look up.
        :param raiseError: (bool) if True, raise an error if converter is not found.
        :return: (float or None) the value of the named variable, or None if not found.
        """
        try:
            return self.conversions[name]

        except KeyError:
            if raiseError:
                raise PygcamException('Unknown unit conversion string "%s"' % name)
            return None

    def set(self, name, value):
        self.conversions[name] = value

    def convert(self, string, raiseError=True):
        """
        Convert the given `string` to its numerical value, either by
        direct type conversion, or if this fails, by look-up as the
        name of a defined unit conversion.

        :param string: (str) a string representing a float or the
            name of a defined unit conversion.
        :param raiseError: (bool) if True, an error is raised if the
            string is neither a number nor a defined unit conversion.
        :return: (float or None) returns the converted value, or if raiseError
            is False and the string is not a recognized unit conversion,
            None is returned.
        """
        value = coercible(string, float, raiseError=False)
        if value is not None:
            return value

        value = self.get(string, raiseError=raiseError)
        if value is not None:
            return value

        return None

    def __init__(self):
        """
        Initialize the unit conversion look-up table.
        """
        s = self    # just to make the following more readable

        # basic SI units and relationships
        s.k = 1e3
        s.M = 1e6
        s.G = 1e9
        s.T = 1e12
        s.P = 1e15
        s.E = 1e18
        s.k_to_ones = 1e3
        s.ones_to_k = 1e-3
        s.M_to_ones = 1e6
        s.ones_to_M = 1e-6
        s.M_to_k = 1e3
        s.k_to_M = 1e-3
        s.G_to_ones = 1e9
        s.ones_to_G = 1e-9
        s.G_to_k = 1e6
        s.k_to_G = 1e-6
        s.G_to_M = 1e3
        s.M_to_G = 1e-3
        s.P_to_M = 1e9
        s.M_to_P = 1e-9
        s.P_to_G = 1e6
        s.G_to_P = 1e-6
        s.P_to_T = 1e3
        s.T_to_P = 1e-3
        s.E_to_G = 1e9
        s.G_to_E = 1e-9

        s.E_to_M = s.E / s.M
        s.M_to_E = s.M / s.E

        # Carbon <--> CO2
        s.C_to_CO2 = 44./12
        s.CO2_to_C = 12./44

        # mass conversions
        s.kg_to_g =   s.k_to_ones
        s.g_to_kg =   s.ones_to_k
        s.Mg_to_kg =  s.M_to_k
        s.kg_to_Mg =  s.k_to_M
        s.Mg_to_ton = 1000./908
        s.ton_to_Mg = 0.908
        s.Mt_to_ton = s.Mg_to_ton
        s.ton_to_Mt = s.ton_to_Mg
        s.Pg_to_Tg =  s.P_to_T
        s.Tg_to_Pg =  s.T_to_P

        # calorie conversions
        s.Pcal_to_Mcal = s.P_to_M
        s.Mcal_to_Pcal = s.M_to_P
        s.Pcal_to_Gcal = s.P_to_G
        s.Gcal_to_Pcal = s.G_to_P

        # volume conversions
        s.m3_to_Gm3 =  1e-9
        s.m3_to_bm3 =  s.m3_to_Gm3
        s.km3_to_Mm3 = 1e3
        s.Mm3_to_km3 = 1e-3

        # area conversions
        s.km2_to_m2 = s.k * s.k
        s.ha_to_m2 = 1e4
        s.m2_to_ha = 1e-4
        s.km2_to_ha = s.km2_to_m2 / s.ha_to_m2
        s.ha_to_km2 = 1.0 / s.km2_to_ha
        s.kkm2_to_ha = 1000 * s.km2_to_ha
        s.thous_km2_to_ha = s.kkm2_to_ha    # alias,
        s.kkm2_to_Mha = s.kkm2_to_ha / s.M
        s.bm2_to_ha =  1e5
        s.ha_to_bm2 =  1e-5
        s.ha_to_m2 =   1e4
        s.m2_to_ha =   1e-4
        s.acre_to_m2 = 4046.85
        s.m2_to_acre = 1.0 / s.acre_to_m2
        s.Gm2_to_km2 = s.G_to_k
        s.bm2_to_km2 = s.G_to_k
        s.km2_to_Gm2 = s.k_to_G
        s.km2_to_bm2 = s.k_to_G
        s.bm2_to_m2 =  s.G_to_ones
        s.Gm2_to_m2 =  s.G_to_ones
        s.ft2_to_m2 =  0.0929
        s.Mft2_to_m2 = s.ft2_to_m2 * s.M_to_ones
        # million square feet to billion square meters
        s.Mft2_to_Gm2 = s.ft2_to_m2 * s.M_to_G
        s.Mft2_to_bm2 = s.Mft2_to_Gm2
        # square feet to billion square meters
        s.ft2_to_Gm2 = s.ft2_to_m2 * s.ones_to_G
        s.ft2_to_bm2 = s.ft2_to_Gm2

        # yield conversions
        s.Mg_per_ha_to_kg_per_m2 = s.M_to_k / s.ha_to_m2

        # time
        s.year_to_day = 365.25
        s.day_to_year = 1.0 / s.year_to_day
        s.day_to_hour = 24
        s.hour_to_day = 1.0 / s.day_to_hour
        s.year_to_hour = s.year_to_day * s.day_to_hour

        # energy unit conversions
        s.kbbl_to_bbl = s.k_to_ones
        s.bbl_to_tonne_RFO = 1.0 / 6.66
        s.bbl_to_tonne_distillate = 1.0 / 7.46
        s.tonne_to_GJ_distillate = 42.91
        s.tonne_to_GJ_RFO = 40.87

        s.MJ_to_EJ = s.M_to_E
        s.EJ_to_MJ = s.E_to_M
        s.GJ_to_EJ = s.G_to_E
        s.EJ_to_GJ = s.E_to_G
        s.kWh_to_MJ = 3.6
        s.MWh_to_GJ = s.kWh_to_MJ
        s.kWh_to_GJ = 0.0036
        s.kWh_to_GJ = s.kWh_to_MJ * s.M_to_G
        s.MWh_to_EJ = 3.6e-9
        s.GWh_to_EJ = 3.6e-6
        s.TWh_to_EJ = 3.6e-3
        s.btu_to_kJ = 1.0551
        s.kJ_to_btu = 1.0 / s.btu_to_kJ
        s.MJ_to_btu = s.kJ_to_btu * s.M_to_k
        s.btu_to_MJ = 1.0 / s.MJ_to_btu
        s.MMbtu_to_MJ = s.M_to_ones * s.btu_to_MJ
        s.MJ_to_MMbtu = 1.0 / s.MMbtu_to_MJ
        s.MJ_to_MMBtu = s.MJ_to_MMbtu
        s.MMBtu_to_MJ = s.MMbtu_to_MJ
        s.quad_to_EJ = s.btu_to_kJ
        s.EJ_to_quad = 1.0 / s.quad_to_EJ

        s.TOE_to_MJ = 41868
        s.MTOE_to_EJ = s.M * s.TOE_to_MJ * s.MJ_to_EJ
        s.EJ_to_MTOE = 1.0 / s.MTOE_to_EJ

        # trillion and thousand btu to EJ
        s.Tbtu_to_EJ = 0.0010551
        s.kbtu_to_EJ = 1.0551e-12

        # dollar inflation/deflation
        s.USD_1990_to_2005 = 1.383
        s.USD_1990_to_2007 = 1.470
        s.USD_1990_to_2010 = 1.510
        s.USD_1990_to_1975 = 0.4649
        s.USD_1996_to_1975 = 0.4049
        s.USD_1997_to_1975 = 0.3983
        s.USD_1998_to_1975 = 0.3939
        s.USD_1999_to_1975 = 0.3883
        s.USD_2000_to_1975 = 0.380
        s.USD_2001_to_1975 = 0.3711
        s.USD_2002_to_1975 = 0.3647
        s.USD_2003_to_1975 = 0.3571
        s.USD_2004_to_1975 = 0.3472
        s.USD_2005_to_1975 = 0.3362
        s.USD_2006_to_1975 = 0.3257
        s.USD_2007_to_1975 = 0.317
        s.USD_2008_to_1975 = 0.3104
        s.USD_2009_to_1975 = 0.3104
