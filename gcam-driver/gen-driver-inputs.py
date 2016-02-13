import os

runid = 'r1i1p1_200601_210012' # seems to be the one runid that is common to all models

gcms = ['CCSM4', 'CESM1_CAM5', 'CSIRO_Mk3_6_0', 'FIO_ESM', 'GFDL_CM3',
        'GFDL_ESM2G', 'GFDL_ESM2M', 'GISS_E2_R']  #  , 'HadGEM2_AO']   <- HadGEM seems to be missing some data
scenarios = ['rcp45', 'rcp60']

pops = ['p80','p85','p90','p95','p10']


gcam_scen_str = {'rcp45' : 'c45', 'rcp60' : 'c60'}
wt_str        = {'True' : 'wT', 'False' : 'wF'}
gcm_codes     = {'FIO_ESM' : 'g0', 'CCSM4' : 'g1', 'GISS_E2_R' : 'g2'}

clobber_hydro = 'False'
clobber_disag = 'False'

water_transfer = 'False'
transfer_file  = '../gcam-hydro/inputs/water-transfer.csv'
for gcm in gcms:
    cfgbatch = []
    for scen in scenarios:
        for pop in pops:
            runname = '%s-%s-%s-%s' % (gcm, scen, pop, wt_str[water_transfer])

            cfgfile = 'runconfig/pplant-%s.cfg' % runname

            print 'cfgfile = %s' % cfgfile
            
            with open(cfgfile, 'w') as cfg:
                ## write global section (same for all runs)
                cfg.write("""[Global]
ModelInterface = /people/link593/wrk/ModelInterface/ModelInterface.jar
DBXMLlib = /people/link593/lib
inputdir = ./input-data
rgnconfig = rgnchn

""")

                ## write hydro section
                cfg.write('[HydroModule]\nworkdir = ../gcam-hydro\n' +
                          'inputdir = /pic/scratch/rpl/CMIP5_preprocessed\n' +
                          'outputdir = output/cmip5\n' +
                          'init-storage-file = ../gcam-hydro/inputs/initstorage.mat\n' +
                          'clobber = %s\n'% clobber_hydro) 
                logname = runname + '-hydro-log.txt'
                cfg.write('logfile = ../gcam-hydro/logs/%s\n'%logname)
                cfg.write('gcm = %s\n' % gcm)
                cfg.write('scenario = %s\n' % scen)
                cfg.write('runid = %s\n' % runid)

                ## write historical hydro section
                cfg.write("""
[HistoricalHydroModule]
workdir = ../gcam-hydro
inputdir = /pic/scratch/rpl/CMIP5_preprocessed
outputdir = output/cmip5
clobber = False
runid = r1i1p1_195001_200512 
""")
                cfg.write('gcm = %s\n' % gcm)
                hlogname = '%s-hist-log.txt' % gcm
                cfg.write('logfile = ../gcam-hydro/logs/%s\n' % hlogname)

                ## write GCAM section
                cfg.write('\n[GcamModule]\nexe = /people/link593/wrk/china-water-all/GCAM_4.0_r5465_User_Package_with_code_Unix/Main_User_Workspace/exe/gcam.exe\n' +
                          'logconfig = /people/link593/wrk/china-water-all/GCAM_4.0_r5465_User_Package_with_code_Unix/Main_User_Workspace/exe/log_conf.xml\n' +
                          'clobber = False\n')
                gcam_scen = gcam_scen_str[scen]
                gcam_config = '/people/link593/wrk/china-water-all/configuration-%s%s.xml' % (gcam_scen,pop)
                cfg.write('config = %s\n' % gcam_config)
                gcam_stdout = '/people/link593/wrk/china-water-all/GCAM_4.0_r5465_User_Package_with_code_Unix/Main_User_Workspace/exe/logs/%s-sdout-log.txt' % runname
                cfg.write('logfile = %s\n' % gcam_stdout)

                ## write water disaggregation section.  Most of this is boilerplate, since the module
                ## figures out many of its own filenames
                cfg.write('\n[WaterDisaggregationModule]\n' +
                          'workdir = ../gcam-hydro\n' +
                          'inputdir = ./input-data\n' +
                          'clobber = %s\n'% clobber_disag) 
                logfile  = '../gcam-hydro/logs/%s-disag-pplant-log.txt' % runname
                cfg.write('logfile = %s\n' % logfile)
                tempdir  = 'output/waterdisag/wdtmp-pplant-%s'% runname
                try:
                    os.makedirs(tempdir)
                except OSError:
                    pass # os error is normal if the dir already exists.
                outputdir = 'output/demo-data-pplant/%s'  % runname
                try:
                    os.makedirs(outputdir)
                except OSError:
                    pass # see above.

                cfg.write('tempdir = %s\n' % tempdir)
                cfg.write('outputdir = %s\n' % outputdir)
                cfg.write('scenario = %s\n' % scen)
                cfg.write('water-transfer = %s\n' % water_transfer)
                cfg.write('transfer-file = %s\n' % transfer_file)
                cfg.write('power-plant-data = ./input-data/power-plants.geojson\n')

                ## write the netcdf production section.
                cfg.write('\n[NetcdfDemoModule]\nmat2nc = ./src/C/mat2nc\n')
                ## figure out the metadata descriptors
                rcpval = float(scen[-2:])/10.0
                popval = float(pop[-2:])
                if popval > 15.0:
                    ## 10.0 is encoded as '10'.  Others are encoded as pop*10
                    popval = popval/10.0
                gdpval = 10.0       # not used, but a placeholder is required

                cfg.write('rcp = %f\npop = %f\ngdp = %f\n' % (rcpval, popval, gdpval))

                ## the output file uses the gcam-version of the scenario
                ## designator.  Eventually it will also use a code for the
                ## GCM.
                if gcm in gcm_codes:
                    gcm_str = gcm_codes[gcm]
                else:
                    gcm_str = gcm+'-'
                outfilename = './output/demo-data-pplant/netcdf/%s%s%s%s-pplant.nc' % (gcm_str, gcam_scen_str[scen], pop, wt_str[water_transfer])
                try:
                    os.makedirs('./output/demo-data-pplant/netcdf')
                except OSError:
                    pass        # see note above
                cfg.write('outfile = %s\n' % outfilename)
            ## end of cfg file write
            cfgbatch.append(cfgfile)



    batchfile = 'batchfiles/pplant-%s-%s.zsh' % (gcm, wt_str[water_transfer])
    with open(batchfile, 'w') as bat:
        bat.write("""#!/bin/zsh
#SBATCH -t 4-0
#SBATCH -n 1
#SBATCH -N 1
#SBATCH -J %s
#SBATCH -A GCAM

source /etc/profile.d/modules.sh 

module load gcc
module load matlab/2013a
module load python/2.7.8

which python
which matlab

ulimit

date

""" % gcm)
        for cfgfile in cfgbatch:
            bat.write('srun time ./gcam-driver ./%s\n' % cfgfile)
            bat.write('date\n')
    ## end of batch file


