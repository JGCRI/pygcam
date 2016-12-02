'''
.. Created on: 12/1/16
   Map-generation API

.. Copyright (c) 2016 Richard Plevin and University of California
   See the https://opensource.org/licenses/MIT for license details.
'''

from .query import interpolateYears
from .queryFile import RewriteSetParser, RewriteSet
from .utils import coercible

def choropleth(df, imagefile, years=None, interpolate=False, sumByYear=False,
               regions=None, regionMap=None, rewriteSet=None, byAEZ=False,
               animate=False, title=None, palette=None):
    """
    Draw a choropleth map representing the data in "GCAM dataframe" `df`,
    optionally interpolating annual values between time-steps, for the
    given `regions`, and if `byAEZ` is True, by AEZ. If `animate` is True,
    figures are rendered for each year in `years` as an animated GIF,
    otherwise, values for `years` are summed and the result represented
    in the figure. If `years` is None, all years provided in `df` are used.

    :param df: (pandas.DataFrame) a "GCAM" dataframe, with various attributes
      describing region, sector, subsector, etc., plus values for a number of
      time-steps (possibly interpolated), and a column indicating units.
    :param imagefile: (str) pathname of the image file to create. Format is
      determined by filename extension.
    :param years: (int or iterable of 2 values coercible to int) the range of
       years to include in results. A single int N is treated as [N, N].
    :param interpolate: (bool) if True, linearly-interpolate annual values
       between 5-year time-steps.
    :param sumByYear: (bool) if True, values are summed across years and the
       results are plotted. Implies `interpolate` = True.
    :param regions: (list of str) The regions to draw. If None, all regions
       referenced in `df` are plotted. These may be standard GCAM regions or
       aggregate regions defined by `regionMap`.
    :param regionMap: (dict) a dictionary keyed  by aggregate region names,
       with values being a list of standard GCAM region names.
    :param rewriteSet: (str or pygcam.queryFile.RewriteSet) the name of a
       RewriteSet that is read from the file given by config var
       GCAM.RewriteSetsFile, or a RewriteSet instance.
    :param byAEZ: (bool) if True, and `regions` is not None, data are plotted
       by region and AEZ. If True and `regions` is None, data are plotted by
       AEZ only. If False, AEZs are not plotted.
    :param animate: (bool) If True, generate an animated gif with a frame for
       each year.
    :param title: (str) A title for the figure. None or "" => no title.
    :param palette: (??) ??
    :return: none
    """

    if rewriteSet:
        regionMap = rewriteSet.asRegionMap() if isinstance(rewriteSet, RewriteSet) \
            else RewriteSetParser.getRegionMap(rewriteSet)

    y = coercible(years, int, raiseError=False)
    if y is None:
        startYear, endYear = years
    else:
        startYear = endYear = y

    if interpolate:
        df  = interpolateYears(df, startYear=startYear, inplace=False)
