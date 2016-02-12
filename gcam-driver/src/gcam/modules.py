"""Definitions for the modules for GCAM and associated downstream models.

We use the word "module" here in a bit of a nonstandard way.  A GCAM
"module" is a functional unit that performs a specific step in the
GCAM processing pipeline.  These modules are distinct from python
modules; a GCAM module may be implemented in one or several python
modules of its own (as in the water disaggregation module), or it may
be completely contained in this module.

Classes:

GcamModuleBase    - Base class for all GCAM modules.  Provides the 
                    interface, as well as services like managing
                    threads, locks, and condition variables.

GlobalParamsModule - Store parameters common to all modules.

GcamModule        - Run the GCAM core model.

HydroModule       - Run the future hydrology calculation.

HistoricalHydroModule - Run the historical hydrology calculation.

WaterDisaggregationModule - Run the water disaggregation calculation.

NetcdfDemoModule  - Package outputs into a netCDF file for the 
                    Decision Theater Demo.

"""

## TODO: many of these classes have gotten a bit long.  It would be
## better to refactor them so that the main functionality is
## implemented in a separate python module for each GCAM module, with
## the GCAM module subclass providing a thin wrapper that grabs inputs
## needed from other modules and passes them to a main function in the
## relevant python module.

import os
import os.path
import re
import subprocess
import threading
import tempfile
from sys import stdout
from sys import stderr
from gcam import util


class GcamModuleBase(object):
    """Common base class for all of the GCAM modules (i.e., functional units).  
    
    We can put any utility functions that are common to all modules
    here, but its main purpose is to provide all the multithreading
    functionality so that the individual modules can focus
    exclusively on doing their particular tasks.
    
    Methods that shouldn't be overridden:
    
    run(): start the module running.  The params argument should
           be a dictionary containing the parameters the module
           needs (probably parsed from the initial config).  Each
           subclass should provide a method called runmod() that
           performs the module's work; that method will be called
           from run().  The runmod() method should return 0 on
           successful completion.  Note that we don't make any
           effort to limit the number of concurrent threads beyond
           the inherent limitations imposed by data dependencies
           between the modules.  This method returns the thread
           object, mainly so that the driver can call join() on
           all of the module threads. 
           TODO: implement an active thread counter.

    runmod_wrapper(): used internally by run().  Don't monkey around
                      with this function.

    fetch(): retrieve the module's results.  If the module hasn't
             completed yet, wait to be notified of completion.  This
             mechanism implicitly enforces correct ordering between
             modules.  Note that we don't make any checks for
             deadlock caused by circular dependencies.

    addparam(): Add a key and value to the params array.  Generally
                this should only be done in the config file parser.
                
    Methods that can be extended (but not overridden; you must be sure
         to call the base method):

    __init__(): initialization, obviously, but each init method must
                take an extra argument that is a dictionary of module
                capabilities, and it must add its own capabilities to
                this dictionary (see modules below for examples).
                The base class init stores a reference to the
                capability table for future lookup.

    finalize_parsing(): When parsing is complete, what you have is a
                bunch of key-value pairs.  This function is the place
                to do any processing that needs to be done (e.g.,
                converting strings to other types).  The base class
                version of the method does this for parameters that
                are applicable to all modules, so it must always be
                called if the method is overridden.

    Methods that can be overridden freely

    runmod(): function that does the module's work.  It should only be
              called from the runmod_wrapper() method via the run()
              method.  Together, these methods perform the additional
              bookkeeping required to ensure that modules don't try to
              use results before they are ready.

    Attributes:

    params: dictionary of parameters parsed from the config file.
            Generally this array should be altered only by calling the
            addparam method.

    """
     
    def __init__(self, cap_tbl):
        """Initialize the GCAM module base.
        
        Every subclass __init__ method should call this method as its
        first action.  The cap_tbl argument is a dictionary linking
        capabilities (i.e., tags for identifying functional units)
        with the modules that provide those capabilities.  Subclasses
        should extend this method by adding their self reference to
        the table under an appropriate tag.  E.g.:
         
        cap_tbl['gcam_core'] = self
         
        The capability table will be available as self.cap_tbl for use
        in a subclass's methods.  Since gcam_driver passes the same
        capacity table to each subclass instance initialization, by
        the time a module starts running the table will contain an
        index of all the active modules in the calculation.

        """
        self.status = 0         # status indicator: 0- not yet run, 1- complete, 2- error
        self.results = {}
        self.params  = {}
        self.results["changed"] = 1
        self.cap_tbl = cap_tbl # store a reference to the capability lookup table
        self.condition = threading.Condition()

    def run(self):
        """Execute the module's runmod() method in a separate thread."""
        thread = threading.Thread(target=lambda: self.runmod_wrapper())
        thread.start()
        ## returns immediately
        return thread

    def runmod_wrapper(self):
        """Lock the condition variable, execute runmod(), and unlock when it returns.
        
        At the conclusion of the runmod() method, self.status will be
        set to 1 if the run was successful, to 2 otherwise.  This
        variable will be used by the fetch() method to notify clients
        if a run failed.  Either way, threads waiting on the condition
        variable will be released when the run completes.

        At the end of this function the following will be true:

        1. Either self.status==1 or self.status==2

        2. If self.status==1, the self.results has a full set of
        results in it.

        This function should be called *only* by the run() method
        above.

        """

        ## This block holds the lock on the condition variable for the
        ## entire time the runmod() method is running.  That's ok for
        ## now, but it's not ideal, and it will cause problems when we
        ## eventually try to implement co-simulations.
        with self.condition:
            try:
                rv = self.runmod()
                if not rv==0:
                    ## possibly add some other error handling here.
                    raise RuntimeError("%s:  runmod returned error code %s" % (self.__class__, str(rv)))
                else:
                    stdout.write("%s: finished successfully.\n"%(self.__class__))

                self.status = 1                  # set success condition
            except:
                self.status = 2                  # set error condition
                raise
            finally:
                self.condition.notify_all()      # release any waiting threads
        ## end of with block:  lock on condition var released.
        
    def fetch(self):
        """Return the results of the calculation as a dictionary.

        The results aren't returned from run() because it will run
        asynchronously.  This method waits if necessary and returns
        the results, checks whether the run was successful (indicated
        by self.status), and if so returns the results dictionary.  If
        the runmod() method failed, the variable will so indicate, and
        an exception will be raised.

        """

        ## If the module is currently running, then the condition
        ## variable will be locked, and we will block when the 'with'
        ## statement tries to obtain the lock.
        with self.condition: 
            if self.status == 0:                  # module hasn't run yet.  Wait on it
                print "\twaiting on %s\n" % self.__class__
                self.condition.wait()
        ## end of with block:  lock is released

        ## By this point, the module should have run.  If status is not success, then
        ## there has been an error.
        if self.status != 1:
            raise RuntimeError("%s: wait() returned with non-success status!"%self.__class__)

        return self.results

    def finalize_parsing(self):
        """Process parameters that are common to all modules (e.g. clobber).  

        The modules will be responsible for processing their own
        special parameters.  If a module needs to override this
        method, it should be sure to call the base version too.

        """
        
        self.clobber = True          # default to overwriting outputs
        if "clobber" in self.params: 
            self.clobber = util.parseTFstring(self.params["clobber"])

        ## processing for additional common parameters go here
        return

    def addparam(self, key, value):
        """Add a parameter key and value parsed from the config file.

        In the current design, this should be called only by the
        config file parser.

        """
        
        self.params[key] = value

    def runmod(self):
        """Subclasses of GcamModuleBase are required to override this method."""

        raise NotImplementedError("GcamModuleBase is not a runnable class.") 


## class to hold the general parameters.  
class GlobalParamsModule(GcamModuleBase):
    """Class to hold the general parameters for the calculation.

    Technically this isn't a module as such; it doesn't run anything,
    but treating it as a module allows us to parse it using the same
    code we use for all the real modules, and having it in the
    capability table makes it easy for any module that needs one of
    the global parameters to look them up.

    Parameters:

    ModelInterface - Location of the jar file for the ModelInterface
                     code, used to query GCAM outputs.

       DBXMLlib - Location of the DBXML libraries used by older
                  versions of the ModelInterface code.

       inputdir - Directory containing general input files.  (OPTIONAL
                  - default is './input-data').  Relative paths will
                  be interpreted relative to the working directory
                  (even if they don't begin with './')

      rgnconfig - Directory containing region configuration files.
                  Any data that changes with the the region mapping
                  should be in this directory.  The directory will be
                  converted to an absolute path if it does not start
                  with '/'.  If it starts with './' the path will be
                  relative to the directory the driver code is running
                  in; otherwise, it will be relative to inputdir.
                  (OPTIONAL - default is 'rgn14')

    """
    
    def __init__(self, cap_tbl):
        """Copy parameters into results dictionary.

        This function also sets the genparams attribute of the util
        module, since it can't get them from this class directly.

        """
        super(GlobalParamsModule, self).__init__(cap_tbl)

        self.results = self.params # this is a reference copy, so any entries added to
                                   # params will also appear in results. 

        print 'General parameters as input:'
        print self.results
        cap_tbl["general"] = self

        ## We need to allow gcamutil access to these parameters, since it doesn't otherwise know how to find the
        ## global params module.  
        util.global_params = self
        
    def runmod(self):
        """Set the default value for the optional parameters, and convert filenames to absolute paths."""
        self.results['ModelInterface'] = util.abspath(self.results['ModelInterface'])
        self.results['DBXMLlib'] = util.abspath(self.results['DBXMLlib'])

        if 'inputdir' in self.results:
            inputdir = self.results['inputdir']
        else:
            inputdir = './input-data'
        self.results['inputdir'] = util.abspath(inputdir,os.getcwd())
        
        if 'rgnconfig' in self.results:
            rgnconfig = self.results['rgnconfig']
        else:
            stdout.write('[GlobalParamsModule]: Using default region mapping (14 region)')
            rgnconfig = 'rgn14'
        self.results['rgnconfig'] = util.abspath(rgnconfig,self.results['inputdir'])

        return 0                # nothing to do here.

    
class GcamModule(GcamModuleBase):
    """Provide the 'gcam-core' capability.

    This module runs the GCAM core model, making the location of the
    output database available under the 'gcam-core' capability.

    Parameters:
      exe        = full path to gcam.exe
      config     = full path to gcam configuration file
      logconfig  = full path to gcam log configuration file
      clobber    = flag: True = clobber old outputs, False = preserve old outputs
    
    Results:
      dbxml      = gcam dbxml output file.  We get this from the gcam config.xml file.

    Module dependences: none

    """
    
    def __init__(self, cap_tbl):
        """Add self to the capability table."""
        super(GcamModule,self).__init__(cap_tbl)
        cap_tbl["gcam-core"] = self

    def runmod(self):
        """Run the GCAM core model.
        
        We start by checking to see that all the input files needed
        for GCAM to run are actually available.  If any of them are
        missing, we raise an IOError execption.  Next we parse the
        config.xml file to find out what outputs we expect, and we
        check to see if they are already present.  If they are, and if
        'clobber' is not set to True, then we skip the run and return
        the location of the existing dbxml.  Otherwise, we do the GCAM
        run and then return the dbxml location.

        """
        
        ### Process the parameters
        exe    = self.params["exe"]
        cfg    = self.params["config"]
        logcfg = self.params["logconfig"]
        try:
            logfile = self.params['logfile'] # file for redirecting gcam's copious stdout
        except KeyError:
            ## logfile is optional
            logfile = None

        ## usually the exe, cfg, and logcfg files will be in the same
        ## directory, but in case of difference, take the location of
        ## the config file as controlling.
        self.workdir = os.path.dirname(exe)

        msgpfx = "GcamModule: "    # prefix for messages coming out of this module
        ## Do some basic checks:  do these files exist, etc.
        if not os.path.exists(exe):
            raise IOError(msgpfx + "File " + exe + " does not exist!")
        if not os.path.exists(cfg):
            raise IOError(msgpfx + "File " + cfg + " does not exist!")
        if not os.path.exists(logcfg):
            raise IOError(msgpfx + "File " + logcfg + " does not exist!")

        ## we also need to get the location of the dbxml output file.
        ## It's in the gcam.config file (we don't repeat it in the
        ## config for this module because then we would have no way to
        ## ensure consistency).
        dbxmlfpat = re.compile(r'<Value name="xmldb-location">(.*)</Value>')
        dbenabledpat = re.compile(r'<Value name="write-xml-db">(.*)</Value>')
        with open(cfg, "r") as cfgfile:
            ## we don't need to parse the whole config file; all we
            ## want is to locate the name of the output file make sure
            ## the dbxml output is turned on.
            dbxmlfile = None
            for line in cfgfile:
                ## the dbxml file name will come early in the file
                match = dbxmlfpat.match(line.lstrip())
                if match:
                    dbxmlfile = match.group(1)
                    break

            print "%s:  dbxmlfile = %s" % (self.__class__, dbxmlfile)
            ## The file spec is a relative path, starting from the
            ## directory that contains the config file.
            dbxmlfile = os.path.join(self.workdir,dbxmlfile) 
            self.results["dbxml"] = dbxmlfile # This is our eventual output
            if os.path.exists(dbxmlfile):
                if not self.clobber:
                    ## This is not an error; it just means we can leave
                    ## the existing output in place and return it.
                    print "GcamModule:  results exist and no clobber.  Skipping."
                    self.results["changed"] = 0 # mark the cached results as clean
                    return 0
                else:
                    ## have to remove the dbxml, or we will merely append to it
                    os.unlink(dbxmlfile)

            ## now make sure that the dbxml output is turned on
            for line in cfgfile:
                match = dbenabledpat.match(line.lstrip())
                if match:
                    if match.group(1) != "1":
                        raise RuntimeError(msgpfx + "Config file has dbxml input turned off.  Running GCAM would be futile.")
                    else:
                        break

        ## now we're ready to actually do the run.  We don't check the return code; we let the run() method do that.
        print "Running:  %s -C%s -L%s" % (exe, cfg, logcfg)

        if logfile is None:
            return subprocess.call([exe, '-C'+cfg, '-L'+logcfg], cwd=self.workdir)
        else:
            with open(logfile,"w") as lf:
                return subprocess.call([exe, '-C'+cfg, '-L'+logcfg], stdout=lf, cwd=self.workdir)

## class for the hydrology code

### This is how you run the hydrology code from the command line:
### matlab -nodisplay -nosplash -nodesktop -r "run_future_hydro('<gcm>','<scenario>');exit" > & outputs/pcm-a1-out.txt < /dev/null
class HydroModule(GcamModuleBase):
    """Provide the 'gcam-hydro' capability.

    This is the future hydrology calculation.  For the historical
    hydrology calculation, see HistoricalHydroModule.

     params:
       workdir - working directory
      inputdir - input directory
     outputdir - output directory 
           gcm - GCM outputs to use
      scenario - tag indicating the scenario to use.
         runid - tag indicating which ensemble member to use.
       logfile - file to direct the matlab code's output to
     startmonth- month of year for first month in dataset. 1=Jan, 2=Feb, etc.  (OPTIONAL) 
    init-storage-file - Location of the file containing initial channel storage. Not
                        required (and ignored) if HistoricalHydroModule is present
    
     results: 
       qoutfile - runoff grid (matlab format)
       foutfile - stream flow grid (matlab)
         cqfile - runoff grid (c format)
       cflxfile - stream flow grid (c format)
     basinqfile - basin level runoff (matlab format)
    cbasinqfile - basin level runoff (c format)
      basinqtbl - basin level output (csv format)
       rgnqfile - region level runoff (matlab format)
      crgnqfile - region level runoff (c format)
        rgnqtbl - region level runoff (csv format)
     petoutfile - PET grid (matlab format)

    Module dependences: HistoricalHydroModule (optional)

    """
    def __init__(self, cap_tbl):
        """Add self to the capability table."""
        super(HydroModule, self).__init__(cap_tbl)
        cap_tbl["gcam-hydro"] = self

    def runmod(self):
        """Run the future hydrology module.

        This module identifies the correct input files using the gcm,
        scenario, and runid tags and checks to see if those files are
        present.  If not, then it throws an IOError exception.  If the
        inputs are present, then it calculates the expected outputs
        and checks to see if they are present.  If they are, then
        uless the 'clobber' parameter is set, the calculation is
        skipped.  Otherwise the hydrology calculation is run on the
        future dataset.  The return value is 0 for successful
        completion, 1 otherwise.

        The future hydrology calculation expects an input file with
        the initial channel water storage.  If the historical
        hydrology model is in use, then the initial channel storage
        will be taken from those results.  Otherwise, the initial
        channel flow values must be taken from the file supplied as
        the 'init-storage-file' parameter.

        """
        
        workdir  = util.abspath(self.params["workdir"])
        inputdir = util.abspath(self.params["inputdir"]) # input data from GCM
        outputdir = util.abspath(self.params["outputdir"]) # destination for output files
        gcm      = self.params["gcm"]
        scenario = self.params["scenario"]
        runid    = self.params["runid"] # identifier for the GCM ensemble member
        logfile  = util.abspath(self.params["logfile"])
        try:
            startmonth = int(self.params['startmonth'])
        except KeyError:
            startmonth = 1      # Default is to start at the beginning of the year
        print '[HydroModule]: start month = %d' % startmonth

        ## ensure that output directory exists
        util.mkdir_if_noexist(outputdir)

        ## get initial channel storage from historical hydrology
        ## module if available, or from self-parameters if not
        if 'historical-hydro' in self.cap_tbl:
            hist_rslts = self.cap_tbl['historical-hydro'].fetch()
            initstorage = hist_rslts['chstorfile']
            self.results['hist-fout'] = hist_rslts['foutfile']
            self.results['hist-qout'] = hist_rslts['qoutfile']
        else:
            ## matlab data file containing initial storage -- used
            ## only if no historical hydro module.
            initstorage = util.abspath(self.params["init-storage-file"]) 
            self.results['hist-fout'] = '/dev/null'
            self.results['hist-qout'] = '/dev/null'

        
        if inputdir[-1] != '/':
            inputdir = inputdir + '/'
        if outputdir[-1] != '/':
            outputdir = outputdir + '/'
        
        ## we need to check existence of input and output files
        prefile  = inputdir + 'pr_Amon_' + gcm + '_' + scenario + '_' + runid + '.mat'
        tempfile = inputdir + 'tas_Amon_' + gcm + '_' + scenario + '_' + runid + '.mat'
        dtrfile  = inputdir + 'dtr_Amon_' + gcm + '_' + scenario + '_' + runid + '.mat'

        print "input files:\n\t%s\n\t%s\n\t%s" % (prefile, tempfile, dtrfile)
    
        msgpfx = "HydroModule:  "
        if not os.path.exists(prefile):
            raise IOError(msgpfx + "missing input file: " + prefile)
        if not os.path.exists(tempfile):
            raise IOError(msgpfx + "missing input file: " + tempfile)
        if not os.path.exists(dtrfile):
            raise IOError(msgpfx + "missing input file: " + dtrfile)

        ## filename bases
        qoutbase = outputdir + 'Avg_Runoff_235_' + gcm + '_' + scenario + '_' + runid
        foutbase = outputdir + 'Avg_ChFlow_235_' + gcm + '_' + scenario + '_' + runid
        boutbase = outputdir + 'basin_runoff_235_' + gcm + '_' + scenario + '_' + runid
        routbase = outputdir + 'rgn_runoff_235_'+gcm+'_' + scenario + '_' + runid
        petoutbase = outputdir + 'Avg_PET_235_' + gcm + '_' + scenario + '_' + runid
        
        ## matlab files for future processing steps 
        qoutfile   = qoutbase + '.mat'
        foutfile   = foutbase + '.mat'
        basinqfile = boutbase + '.mat'
        rgnqfile   = routbase + '.mat'
        petoutfile = petoutbase + '.mat'
        ## c-data files for final output
        cqfile     = qoutbase + '.dat'
        cflxfile   = foutbase + '.dat'
        cbasinqfile = boutbase + '.dat'
        crgnqfile  = routbase + '.dat'
        ## csv tables for diagnostics
        basinqtblfile  = boutbase + '.csv'
        rgnqtblfile    = routbase + '.csv'
        
        ## Our result is the location of these output files.  Set that
        ## now, even though the files won't be created until we're
        ## done running.
        self.results['qoutfile']   = qoutfile
        self.results['foutfile']   = foutfile
        self.results['cqfile']     = cqfile 
        self.results['cflxfile']   = cflxfile
        self.results['basinqfile'] = basinqfile
        self.results['cbasinqfile'] = cbasinqfile
        self.results['rgnqfile']   = rgnqfile
        self.results['crgnqfile']  = crgnqfile
        self.results['basinqtbl']  = basinqtblfile
        self.results['rgnqtbl']    = rgnqtblfile
        self.results['petoutfile'] = petoutfile
        
        ## We need to report the runid so that other modules that use
        ## this output can name their files correctly.
        self.results['runid']      = runid

        alloutfiles = [qoutfile, foutfile, cqfile, cflxfile, basinqfile, cbasinqfile,
                       rgnqfile, crgnqfile, basinqtblfile, rgnqtblfile, petoutfile]
        if not self.clobber and util.allexist(alloutfiles):
            ## all files exist, and we don't want to clobber them
            print "[HydroModule]:  results exist and no clobber.  Skipping."
            self.results["changed"] = 0 # mark cached results as clean
            return 0        # success code

        ## Get the location of the region mapping file.
        genparams = self.cap_tbl['general'].fetch()
        gridrgn   = util.abspath('grid2rgn_nonag.csv',genparams['rgnconfig'])
        
        ## Run the matlab code.
        ## TODO: eventually we need to move away from matlab, as it is not a
        ##       suitable batch language.  Notably, if it encounters an error
        ##       it will stop at a command prompt instead of exiting with an
        ##       error code.  Yuck.

        ## Note that unlike the historical version, we don't have to
        ## pass the names of the basin and region table files, since
        ## the code can infer them from the basinqfile and rgnqfile
        ## parameters. 
        ## TODO: prune the number of filenames passed by inferring all
        ## of the cfoofile filenames the same way.
        print 'Running the matlab hydrology code'
        with open(logfile,"w") as logdata, open("/dev/null", "r") as null:
            arglist = ['matlab', '-nodisplay', '-nosplash', '-nodesktop', '-singleCompThread','-r', 
                       "run_future_hydro('%s','%s','%s','%s','%s', %d, '%s','%s','%s', '%s','%s', '/dev/null');exit" %
                       (prefile,tempfile,dtrfile,initstorage,gridrgn, startmonth, qoutfile,foutfile,petoutfile, basinqfile,rgnqfile)]
            sp = subprocess.Popen(arglist, stdin=null, stdout=logdata, stderr=subprocess.STDOUT,
                                  cwd=workdir)
            rc = sp.wait()
        ## matlab often won't return an error code when it fails, so check to see that all files were created
        if util.allexist(alloutfiles):
            return rc
        else:
            stderr.write('[HydroModule]: Some output files missing.  Check logfile (%s) for more information\n'%logfile)
            return 1            # nonzero return code indicates failure
    ## end of runmod()


class HistoricalHydroModule(GcamModuleBase):
    """Class for historical hydrology run.  

    This is similar to, but not quite the same as, the main hydro module.
    params:
       workdir  - working directory for the matlab runs
       inputdir - location of the input files    
        gcm     - Which GCM to use (each has its own historical data)
       runid    - Tag indicating the run-id (e.g.  r1i1p1_195001_200512 )
       outputdir- Destination directory for output    
       logfile  - file to redirect matlab output to
      startmonth- month of year for first month in dataset (OPTIONAL)
    
    results:
         qoutfile - runoff grid (matlab format)
         foutfile - stream flow grid (matlab format)
       chstorfile - channel storage grid (matlab format)
        basinqtbl - file for basin level runoff (csv format)
          rgnqtbl - file for region level runoff (csv format)
       petoutfile - file for PET output (matlab format)

    module dependences:  none

    """
    def __init__(self, cap_tbl):
        """Add 'historical-hydro' capability to cap_tbl"""
        super(HistoricalHydroModule, self).__init__(cap_tbl)
        cap_tbl['historical-hydro'] = self

    def runmod(self):
        """Run the historical hydrology code.
        
        Before running, the module tests for the existence of the
        input files, and throws an exception (IOError) if any are
        missing.  It also tests for the expected output files, and if
        they are all present and 'clobber' is not set, it skips the
        run.  Either way, the results dictionary contains the names of
        the output files.  Return value is 0 for success, 1 for
        failure.

        """
        workdir   = util.abspath(self.params['workdir'])
        inputdir  = util.abspath(self.params['inputdir'])
        outputdir = util.abspath(self.params['outputdir'])
        gcm       = self.params['gcm']
        scenario  = 'historical'
        runid     = self.params['runid']
        logfile   = util.abspath(self.params['logfile'])
        try:
            startmonth = int(self.params['startmonth'])
        except KeyError:
            startmonth = 1      # Default is January
        print '[HistoricalHydroModule]: start month = %d' % startmonth

        ## ensure output directory exists
        util.mkdir_if_noexist(outputdir)

        if inputdir[-1] != '/':
            inputdir = inputdir + '/'
        if outputdir[-1] != '/':
            outputdir = outputdir + '/'
        
        ## we need to check existence of input and output files
        prefile  = inputdir + 'pr_Amon_' + gcm + '_' + scenario + '_' + runid + '.mat'
        tempfile = inputdir + 'tas_Amon_' + gcm + '_' + scenario + '_' + runid + '.mat'
        dtrfile  = inputdir + 'dtr_Amon_' + gcm + '_' + scenario + '_' + runid + '.mat'

        print "input files:\n\t%s\n\t%s\n\t%s" % (prefile, tempfile, dtrfile)

        msgpfx = "HistoricalHydroModule:  "
        if not os.path.exists(prefile):
            raise IOError(msgpfx + "missing input file: " + prefile)
        if not os.path.exists(tempfile):
            raise IOError(msgpfx + "missing input file: " + tempfile)
        if not os.path.exists(dtrfile):
            raise IOError(msgpfx + "missing input file: " + dtrfile)

        ## output filenames
        qoutfile      = outputdir + 'Avg_Runoff_235_' + gcm + '_' + scenario + '_' + runid + '.mat'
        petoutfile    = outputdir + 'Avg_PET_235_' + gcm + '_' + scenario + '_' + runid + '.mat'
        basinqtblfile = outputdir + 'basin_runoff_235_' + gcm + '_' + scenario + '_' + runid + '.csv'
        rgnqtblfile   = outputdir + 'rgn_runoff_235_' + gcm + '_' + scenario + '_' + runid + '.csv'        
        foutfile      = outputdir + 'Avg_ChFlow_235_' + gcm + '_' + scenario + '_' + runid + '.mat'
        chstorfile    = outputdir + 'InitChStor_' + gcm + '_' + scenario + '_' + runid + '.mat'

        ## Results will be these file names.  Set up the results
        ## entries now, even though the files won't be ready yet.
        self.results['qoutfile'] = qoutfile
        self.results['foutfile'] = foutfile
        self.results['chstorfile'] = chstorfile
        self.results['basinqtbl']  = basinqtblfile
        self.results['rgnqtbl']    = rgnqtblfile
        self.results['petoutfile'] = petoutfile

        ## Test to see if the outputs already exist.  If so, then we can skip these calcs.
        alloutfiles = [qoutfile, foutfile, petoutfile, chstorfile, basinqtblfile, rgnqtblfile]
        if not self.clobber and util.allexist(alloutfiles):
            print "[HistoricalHydroModule]: results exist and no clobber set.  Skipping."
            self.results['changed'] = 0
            return 0        # success code


        ## Get the location of the region mapping file.
        genparams = self.cap_tbl['general'].fetch()
        gridrgn   = util.abspath('grid2rgn_nonag.csv',genparams['rgnconfig'],'HistoricalHydroModule')
        print '[HistoricalHydroModule]: gridrgn = %s ' % gridrgn
        print '[HistoricalHydroModule]: rgnconfig = %s ' % genparams['rgnconfig']
        
        ## If we get here, then we need to run the historical
        ## hydrology.  Same comments apply as to the regular hydrology
        ## module.
        print 'Running historical hydrology for gcm= %s   runid= %s' % (gcm, runid)
        with open(logfile,'w') as logdata, open('/dev/null','r') as null:
            arglist = ['matlab', '-nodisplay', '-nosplash', '-nodesktop', '-singleCompThread','-r',
                       "run_historical_hydro('%s', '%s', '%s', '%s', %d, '%s', '%s','%s', '%s', '%s', '%s', '/dev/null');exit" %
                       (prefile, tempfile, dtrfile, gridrgn, 1, chstorfile, qoutfile, foutfile,petoutfile, basinqtblfile, rgnqtblfile)]
            sp = subprocess.Popen(arglist, stdin=null, stdout=logdata, stderr=subprocess.STDOUT,
                                  cwd=workdir)
            rc = sp.wait()
        ## check to see if the outputs were actually created; matlab will sometimes fail silently
        if util.allexist(alloutfiles):
            return rc
        else:
            stderr.write('[HistoricalHydroModule]: Some output files were not created.  Check logfile (%s) for details.\n'%logfile)
            return 1            # nonzero indicates failure
    
### This is how you run the disaggregation code
### matlab -nodisplay -nosplash -nodesktop -r "run_disaggregation('<runoff-file>', '<chflow-file>', '<gcam-filestem>');exit" >& <logfile> < /dev/null
class WaterDisaggregationModule(GcamModuleBase):
    """Class for the water demand disaggregation calculation

    This module makes use of the GCAMhydro code (which currently
    includes the water disaggregation code). That code lives in its
    own repository and must be installed independently.  Some input
    files for this module will live in the GCAMhydro input directory,
    while others will live in the gcam-driver inputs.  Mostly, things
    that GCAMhydro knows about go in the GCAMhydro directories, while
    other stuff goes in our directories.  One major exception is all
    of the region-related data (including the grid-to-region mapping.
    That data is in the driver repository (by default - it can be
    changed) so that we can keep the region mapping consistent between
    modules.

    params:
       workdir  - working directory (location of GCAMhydro code)

     outputdir  - directory for outputs

       tempdir  - directory for intermediate files (results of GCAM queries)

       logfile  - File to redirect matlab output into.

      scenario  - scenario tag

          inputdir - directory for static inputs.  (OPTIONAL - default =
                     inputdir from GlobalParamsModule)

    water-transfer - Flag indicating whether water transfer projects
                     should be added in post processing (OPTIONAL -
                     default = False)

    transfer-file - Location of the file describing the water
                     transfers.  Required if water-transfer == True,
                     ignored otherwise.  Location for relative paths
                     is workdir (so 'inputs/water-transfer.csv' will
                     put it in the inputs directory for GCAMhydro)
    
    results: c-style binary files for each of the following variables
              (the key is the variable name; the value is the
              filename): "wdtotal", "wddom", "wdelec", "wdirr",
              "wdliv", "wdmanuf", "wdmining", "wsi"

    Module dependences:  GcamModule, HydroModule

    TODO: Allow config to specify a GCAM dbxml file directly, instead
          of having to go through the GcamModule, even when we know
          the result is precalculated.

    """
    
    def __init__(self, cap_tbl):
        super(WaterDisaggregationModule, self).__init__(cap_tbl)
        cap_tbl["water-disaggregation"] = self

    def runmod(self):
        """Run the water demand disaggregation calculation.
        
        Does some simple consistency checking on the input parameters,
        and returns a failure code if errors are found.  Then checks
        to see if expected outputs already exist.  If so, the
        calculation is skipped (unless 'clobber' is set), and the
        existing results are added to the results dictionary.
        Otherwise, the disaggregation calculation is run, and the new
        results are added to the results dictionary.

        """
        
        import gcam.water.waterdisag as waterdisag

        workdir  = self.params["workdir"]

        hydro_rslts = self.cap_tbl["gcam-hydro"].fetch() # hydrology module
        genparams   = self.cap_tbl['general'].fetch()   # general parameters

        if 'dbxml' in self.params:
            if 'gcam-core' in self.cap_tbl:
                stdout.write('[WaterDisaggregationModule]: WARNING - gcam module included and dbfile specified.  Using dbfile and ignoring module.\n')
            gcam_rslts = {'dbxml' : self.params['dbxml'],
                          'changed' : False} 
        else:
            gcam_rslts = self.cap_tbl["gcam-core"].fetch() # gcam core module

        
        runoff_file   = hydro_rslts["qoutfile"]
        chflow_file   = hydro_rslts["foutfile"]
        basinqfile    = hydro_rslts["basinqfile"]
        rgnqfile      = hydro_rslts["rgnqfile"]
        runid         = hydro_rslts["runid"]
        dbxmlfile     = util.abspath(gcam_rslts["dbxml"])
        outputdir     = util.abspath(self.params["outputdir"])
        tempdir       = util.abspath(self.params["tempdir"])  # location for intermediate files produced by dbxml queries
        scenariotag   = self.params["scenario"]
        hist_chflow_file = hydro_rslts['hist-fout']
        hist_runoff_file = hydro_rslts['hist-qout']

        rgnconfig = genparams['rgnconfig']

        ## ensure that output and temp directories exist
        util.mkdir_if_noexist(outputdir)
        util.mkdir_if_noexist(tempdir)

        if 'inputdir' in self.params:
            inputdir = self.params['inputdir'] # static inputs, such as irrigation share and query files.
        else:
            inputdir = genparams['inputdir']
        print '[WaterDisaggregationModule]: inputdir = %s' % inputdir

        ## Parse the water transfer parameters.
        if 'water-transfer' in self.params:
            transfer      = util.parseTFstring(self.params['water-transfer'])
            try:
                transfer_file = util.abspath(self.params['transfer-file'], workdir)
            except KeyError:
                stderr.write('Water transfer set, but no transfer data file specified.\n')
                return 5
        else:
            transfer = False
            transfer_file = '/dev/null' # won't be used by the matlab program, but we still need a placeholder

        if 'power-plant-data' in self.params:
            ppinfile = self.params['power-plant-data']
            wfcoal = self.params.get('waterfac-coal') # get() suplies None as a default value
            wfgas = self.params.get('waterfac-gas')
            wfnuc = self.params.get('waterfac-nuc')
                
            ppgrid_data = waterdisag.pplant_proc(ppinfile,tempdir, wfcoal, wfgas, wfnuc)
            ppflag = 1
        else:
            ppgrid_data = '/dev/null' # matlab prog will detect and use fallback.
            ppflag = 0
            
        self.results['water-transfer'] = transfer
        ## append the transfer status to the scenario tag
        if transfer:
            scenariotag = scenariotag + 'wT'
        else:
            scenariotag = scenariotag + 'wF' 
        print 'scenariotag = %s' % scenariotag

        ## Initialize the waterdisag module
        waterdisag.init_rgn_tables(rgnconfig)

        ## Helper function generator
        def get_dir_prepender(dir):
            if dir[-1]=='/':
                return lambda file: dir+file
            else:
                return lambda file: dir+'/'+file

        inputdirprep  = get_dir_prepender(inputdir)
        tempdirprep = get_dir_prepender(tempdir)
        outdirprep  = get_dir_prepender(outputdir)
        rgndirprep  = get_dir_prepender(rgnconfig)
        
        vars = ["wdtotal", "wddom", "wdelec", "wdirr", "wdliv", "wdmfg", "wdmin", "wsi",
                "basin-supply", "basin-wdtot", "basin-wddom", "basin-wdelec", "basin-wdirr", "basin-wdliv", "basin-wdmfg", "basin-wdmin", "basin-wsi",
                "rgn-supply", "rgn-wdtot", "rgn-wddom", "rgn-wdelec", "rgn-wdirr", "rgn-wdliv", "rgn-wdmfg", "rgn-wdmin", "rgn-wsi"]
        allfiles = 1
        for var in vars:
            filename = "%s/%s-%s-%s.dat" % (outputdir, var, scenariotag, runid)
            self.results[var] = filename
            if not os.path.exists(filename):
                print 'File %s does not exist.  Running WaterDisaggregationModule.\n' % filename
                allfiles = 0

        
        pop_demo_file = outdirprep("pop-demo.csv") # changed this to use the same region ordering in the water data.
        self.results['pop-demo'] = pop_demo_file

        if allfiles and not self.clobber and not (gcam_rslts["changed"] or hydro_rslts["changed"]):
            print "WaterDisaggregationModule: results exist and no clobber.  Skipping."
            self.results["changed"] = 0
            return 0


        print 'disaggregation results:\n%s' % str(self.results)
        
        queryfiles = ['batch-land-alloc.xml', 'batch-population.xml', 'batch-water-ag.xml',
                      'batch-water-dom.xml', 'batch-water-elec.xml', 'batch-water-livestock.xml',
                      'batch-water-mfg.xml', 'batch-water-mining-alt.xml']
        outfiles   = ['batch-land-alloc.csv', 'batch-population.csv', 'batch-water-ag.csv',
                      'batch-water-dom.csv', 'batch-water-elec.csv', 'batch-water-livestock.csv',
                      'batch-water-mfg.csv', 'batch-water-mining.csv']
        queryfiles = map(inputdirprep, queryfiles)
        outfiles = map(tempdirprep, outfiles)
        util.gcam_query(queryfiles, dbxmlfile, inputdir, outfiles)

        ### reformat the GCAM outputs into the files the matlab code needs 
        ### note all the csv files referred to here are temporary
        ### files.  On the input side the names need to match the ones
        ### used in the configuration of the gcam model interface
        ### queries, and on the output side they must match the ones
        ### used in the matlab disaggregation code.

        ## non-ag demands (sadly, I didn't think to put the lists
        ## above in the order we were planning to use them.)
        wddom   = waterdisag.proc_wdnonag(outfiles[3], tempdirprep("withd_dom.csv"))
        wdelec  = waterdisag.proc_wdnonag(outfiles[4], tempdirprep("withd_elec.csv"))
        wdman   = waterdisag.proc_wdnonag(outfiles[6], tempdirprep("withd_mfg.csv"))
        wdmin   = waterdisag.proc_wdnonag(outfiles[7], tempdirprep("withd_min.csv"))

        ## population data
        waterdisag.proc_pop(outfiles[1], tempdirprep("pop_fac.csv"), tempdirprep("pop_tot.csv"), pop_demo_file)

        ## livestock demands
        wdliv  = waterdisag.proc_wdlivestock(outfiles[5], tempdirprep("withd_liv.csv"), tempdirprep('rgn_tot_withd_liv.csv'))

        ## agricultural demands and auxiliary quantities
        gcam_irr = waterdisag.proc_ag_area(outfiles[0], tempdirprep("irrA.csv"))
        waterdisag.proc_ag_vol(outfiles[2], tempdirprep("withd_irrV.csv"))

        if not gcam_irr:
            ## If GCAM didn't produce endogeneous irrigated and
            ## rain-fed land allocations, then we need to read in some
            ## precalculated irrigation shares.
            waterdisag.proc_irr_share(rgndirprep('irrigation-frac.csv'), tempdirprep("irrS.csv"))
            read_irrS = 1       # argument to matlab code
        else:
            read_irrS = 0

        ## Run the disaggregation model
        if transfer:
            tflag = 1
        else:
            tflag = 0

        matlabdata = {'runoff':runoff_file, 'chflow':chflow_file,
                      'histrunoff':hist_runoff_file,
                      'histchflow':hist_chflow_file, 'basinqfile':basinqfile,
                      'rgnqfile':rgnqfile, 'rgnconfig':rgnconfig, 'tempdir':tempdir,
                      'ppgrid':ppgrid_data, 'ppflg':ppflag,
                      'outputdir':outputdir, 'scenario':scenariotag,
                      'runid':runid, 'trnflag':tflag, 'trnfile':transfer_file,
                      'rdirrS':read_irrS}
        matlabfn = "run_disaggregation('{runoff}', '{chflow}', '{histrunoff}', '{histchflow}', '{basinqfile}', '{rgnqfile}', '{rgnconfig}', '{tempdir}', {ppflg:d}, '{ppgrid}', '{outputdir}', '{scenario}', '{runid}', {trnflag:d}, '{trnfile}', {rdirrS:d}); exit".format(**matlabdata)
        print 'current dir: %s ' % os.getcwd()
        print 'matlab fn:  %s' % matlabfn
        with open(self.params["logfile"],"w") as logdata, open("/dev/null","r") as null:
            arglist = ["matlab", "-nodisplay", "-nosplash", "-nodesktop", '-singleCompThread',"-r", 
                        matlabfn]

            sp = subprocess.Popen(arglist, stdin=null, stdout=logdata, stderr=subprocess.STDOUT,
                                  cwd=workdir) 
            return sp.wait()
        
    ## end of runmod
        
## class for the netcdf-demo builder
class NetcdfDemoModule(GcamModuleBase):
    """Module to build NetCDF output for the February 2015 demo.

    params:
      mat2nc  - location of the netcdf converter executable
        dsid  - dataset id
     forcing  - forcing value (written into the output data as metadata)
    globalpop - 2050 global population (written into output data as metadata)
       pcGDP  - 2050 per-capita GDP (written into output data as metadata -- currently not used anyhow)
    outfile - output file

    Module dependences:  HydroModule, WaterDisaggregationModule

    """
    def __init__(self, cap_tbl):
        super(NetcdfDemoModule, self).__init__(cap_tbl)
        cap_tbl['netcdf-demo'] = self

    def runmod(self):
        """Create NetCDF file from HydroModule and WaterDisaggregationModule results."""
        hydro_rslts = self.cap_tbl['gcam-hydro'].fetch()
        water_rslts = self.cap_tbl['water-disaggregation'].fetch()

        print 'water_rslts:\n%s' % str(water_rslts)

        chflow_file  = hydro_rslts['cflxfile']
        transfer     = water_rslts['water-transfer']

        rcp = self.params['rcp']
        pop = self.params['pop']
        gdp = 10.0              # Dummy value; we didn't implement the GDP scenarios.
        outfile = util.abspath(self.params['outfile'])
        mat2nc  = util.abspath(self.params['mat2nc'],os.getcwd())
        
        self.results['outfile'] = outfile

        ## ensure that the directory the output file is being written to exists
        util.mkdir_if_noexist(os.path.dirname(outfile))
        
        try:
            ## create a temporary file to hold the config
            (fd, tempfilename) = tempfile.mkstemp()
            cfgfile = os.fdopen(fd,"w")

            cfgfile.write('%s\n%s\n%s\n' % (rcp, pop, gdp))
            cfgfile.write('%s\n' % outfile)
            if transfer:
                cfgfile.write('no-data\n')
            else:
                cfgfile.write('%s\n' % chflow_file)
            for var in ['wdirr', 'wdliv', 'wdelec', 'wdmfg', 'wdtotal', 'wddom', 'wsi']:
                if transfer:
                    ## for water transfer cases, we don't have any gridded data, so substitute a grid full of NaN.
                    cfgfile.write('no-data\n')
                else:
                    cfgfile.write('%s\n' % water_rslts[var])
            cfgfile.write('%s\n' % water_rslts['pop-demo'])
            for var in ['basin-supply', 'basin-wdirr', 'basin-wdliv', 'basin-wdelec', 'basin-wdmfg', 'basin-wdtot', 'basin-wddom', 'basin-wsi',
                        'rgn-supply', 'rgn-wdirr', 'rgn-wdliv', 'rgn-wdelec', 'rgn-wdmfg', 'rgn-wdtot', 'rgn-wddom', 'rgn-wsi']:
                cfgfile.write('%s\n' % water_rslts[var])

            cfgfile.close()

            return subprocess.call([mat2nc, tempfilename])
        finally:
            os.unlink(tempfilename)
