import os

hist_runid = 'r1i1p1_195001_200512'
fut_runid  = 'r1i1p1_200601_210012'

#gcms = ['GFDL_CM3', 'HadGEM2_ES', 'IPSL_CM5A_LR']
# gcms = ['GFDL_CM3', 'IPSL_CM5A_LR'] # HadGEM2 needs special treatment
# scenarios = ['rcp45','rcp85']
gcms = ['CCSM4', 'CESM1_CAM5', 'CSIRO_Mk3_6_0', 'FIO_ESM', 'GFDL_CM3',
        'GFDL_ESM2G', 'GFDL_ESM2M', 'GISS_E2_R','ACCESS1_0', 'bcc_csm1_1_m',
        'bcc_csm1_1', 'BNU_ESM', 'CanESM2', 'CESM1_BGC', 'CMCC_CM', 'CNRM_CM5',
        'EC_EARTH', 'FGOALS_g2', 'IPSL_CM5A_LR']
scenarios = ['rcp45', 'rcp60', 'rcp85', 'rcp26']

for gcm in gcms:
    cfgfiles = []
    for scen in scenarios:
        runname = '%s-%s'%(gcm,scen)

        cfgfile = 'lamp-inputs/%s.cfg' % runname
        print 'cfgfile = %s' % cfgfile
        cfgfiles.append(cfgfile)

        with open(cfgfile, 'w') as cfg:
            ## write global section (same for all runs)
            cfg.write('[Global]\nModelInterface = /people/link593/wrk/ModelInterface/ModelInterface.jar\n' +
                      'DBXMLlib = /people/link593/lib\n'+
                      'inputdir = ./input-data\n' +
                      'rgnconfig = rgn32\n\n')

            ## write historical hydro section
            cfg.write('[HistoricalHydroModule]\nworkdir = ../gcam-hydro\n' +
                      'inputdir = /pic/scratch/rpl/CMIP5_preprocessed\n' +
                      'outputdir = output/cmip5\n'+
                      'clobber = False\n')
            logfilestr = 'logfile = ../gcam-hydro/logs/%s-historical-hydro.txt\n' % gcm
            cfg.write(logfilestr)
            gcmstr = 'gcm = %s\n' % gcm
            cfg.write(gcmstr)
            runidstr = 'runid = %s\n' % hist_runid
            cfg.write(runidstr)

            ## write future hydro section
            cfg.write('\n[HydroModule]\nworkdir = ../gcam-hydro\n' +
                      'inputdir = /pic/scratch/rpl/CMIP5_preprocessed\n' +
                      'outputdir = output/cmip5\n' +
                      'clobber = False\n')
            logfilestr = 'logfile = ../gcam-hydro/logs/%s-%s-future-hydro.txt\n' % (gcm, scen)
            cfg.write(logfilestr)
            cfg.write(gcmstr)   # same as the historical
            scenstr = 'scenario = %s\n' % scen
            cfg.write(scenstr)
            runidstr = 'runid = %s\n' % fut_runid
            cfg.write(runidstr)

    batchfile = 'lamp-inputs/{0}.zsh'.format(gcm)
    with open(batchfile, 'w') as bat:
        bat.write("""#!/bin/zsh
#SBATCH -t 2-0
#SBATCH -n 1
#SBATCH -N 1
#SBATCH -J hydro-{gcmname}
#SBATCH -A GCAM

source /etc/profile.d/modules.sh
module load gcc
module load matlab/2013a
module load python/2.7.8

which python
which matlab

ulimit
date

""".format(gcmname=gcm))

        for cfgfile in cfgfiles:
            bat.write('time ./gcam-driver ./%s\n' % cfgfile)
            bat.write('date\n')
            
