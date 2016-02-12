"""Extract certain coefficients from GCAM db files.

Usage:  coefficients.py <dbfile>

This is not, strictly speaking, a test code, but it is also not
needed for production runs, so it wound up in the test suite.
"""

import sys

## set dbfile to use for testing
try:
    dbfile = sys.argv[1]
except IndexError:
    sys.exit('Error: no dbfile specified.\nUsage:  %s <dbfile>\n'%sys.argv[0])


## enable this code to run from the gcam/test/ directory
sys.path.append('../..')

from gcam import *
from gcam.modules import GlobalParamsModule
from gcam.water import waterdisag

## Set up the global parameters module (which is used by some of the
## utility functions).
## XXX these paths are specific to the configuration on PIC.
genparams = {"ModelInterface" : "/pic/projects/GCAM/ModelInterface-baseX/ModelInterface.jar",
             "DBXMLlib" : "/pic/projects/GCAM/GCAM-libraries/lib"}
global_params = GlobalParamsModule({})
for key in genparams.keys():
    global_params.addparam(key, genparams[key])
global_params.run()
water.waterdisag.init_rgn_tables('../../../input-data/rgn32')

queryfiles = ['batch-land-alloc.xml', 'batch-water-ag.xml']

## add the directory path to the query files
querydir   = '../../../input-data/'
queryfiles = map(lambda file: querydir + file, queryfiles)

outfiles = ['output/batch-land-alloc.csv', 'output/batch-water-ag.csv']



util.gcam_query(queryfiles, dbfile, querydir, outfiles)

ag_area_file = outfiles[0]
ag_area = water.waterdisag.read_gcam_ag_area(ag_area_file)

## compute area fraction
irr_shr = {}
for (rgn,aez,crop,irr) in ag_area:
    if irr=='TOT':
        raise RuntimeError("Can't compute irrigation share with total area data.\n")

    if irr=='IRR':
        irrigated = ag_area[(rgn,aez,crop,'IRR')]
        rainfed   = ag_area[(rgn,aez,crop,'RFD')]

        irr_shr[(rgn,aez,crop)]   = map(lambda x,y:x/(x+y+1e-12), irrigated, rainfed)

with open('output/irrigation-frac.csv','w') as outfile:
    for (rgnidx, rgn) in enumerate(water.waterdisag.regions_ordered):
        rgnno = rgnidx + 1      # output needs unit-indexed addressing
        for aez in range(1,19):
            for (cropidx, crop) in enumerate(water.waterdisag.croplist):
                cropno = cropidx + 1 # unit indexing
                try:
                    data = irr_shr[(rgnno, aez, cropno)]

                    data.insert(0,cropno)
                    data.insert(0,aez)
                    data.insert(0,rgnno)
                    
                    data.append(rgn)
                    data.append(crop)
                    
                    outfile.write(','.join(map(str,data)))
                    outfile.write('\n')
                except KeyError: # skip combinations that don't occur
                    pass
#end                
