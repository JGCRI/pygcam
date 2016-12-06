'''
.. Created on: 12/1/16
   Map-generation API

.. Copyright (c) 2016 Richard Plevin and University of California
   See the https://opensource.org/licenses/MIT for license details.
'''

from pygcam.diff import readCsv
from pygcam.map import drawMap

filename = '../tests/data/ws/corn-0/queryResults/Purpose-grown_biomass_production-corn-0.csv'
df = readCsv(filename)
imagefile = '/tmp/testmap.png'

regionMap = {
    'United States' : ['USA'],
    'Brazil' : ['Brazil'],
    'Canada' : ['Canada'],
    'Rest of Latin America' : ['Central America and Caribbean',
                               'Mexico', 'Argentina', 'Colombia',
                               'South America_Southern',
                               'South America_Northern']
}

drawMap(df, imagefile, years=(2020, 2050), interpolate=True, sumByYear=True,
        regions=regionMap.keys(), regionMap=regionMap,
        rewriteSet=None, byAEZ=False,
        title='Random Title', palette=None, animate=False)
