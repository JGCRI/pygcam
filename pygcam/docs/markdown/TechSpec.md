#Thoughts on pyGCAM

## Configuration
Try to keep config vars to a minimum by allowing them to be set in XML files used by the various tools. 

  * Config vars should be used to store relatively unchanging paths to various resources. These are mostly "set and forget".

  * Parameters that affect the behavior of the tools should all be settable on the command-line, too. This allows them to be set in runProject.xml and have it all in one place.

## Relationship between command-line scripts and library

The scripts should all define a main(args) so that a calling script can create an arg dictionary and 
call module.main(args). The calling script should be only:

   * an argument parsing function
   * a call to main(args) in a try/except wrapper 

## Modules

  * **gcam.py** -- API to the gcam executable and ModelInterface, including the database. 
    * function wrapper around calling gcam.exe
    * wrapper around calling ModelInterface in batch mode
    * error classes, as required

  * **csv.py**
    * read/write GCAM query-result CSV format files
    * interpolate annual values in results
    * compute differences from two query-result files
    * (separated to use gcam.py without importing pandas)

  * **Xvfb.py** -- create virtual X11 frame-buffer
    * Fine as is, though at only 80 lines, might add it to gcam.py

  * **config.py** -- interface to the pygcam configuration file. 
    * Use hierarchical var naming, e.g., "GCAM.Query.Path", "GCAM.Query.Dir"
    * Make it generic enough to use with gcammcs, too, even if with a different config file.
      
  * **xml.py** -- low-level API to XML files
      * file read with optional validation, and write
      * access to parsed file structure
        * look at lxml's "objectify" API: might be better for this purpose than etree
      * file editing primitives (used by setup system)
        * these currently use the xmlstarlet executable, but coding these directly using lxml package would be more flexible (and obviate need to install xmlstarlet)

  * **setup.py** -- API to gcam-data-system/{xml,solution} files
    * implements "setup" system with local-xml and dyn-xml directories with project and policy subdirectories
    * create copy of "parent" configuration XML file; modify copy only
    * generate modified configuration.xml
      * Control user-configurable options (files, strings, ints, doubles, bools)
      * Add / modify / delete scenario components 
      * set solution-related parameters (e.g., tolerance) 
    
  * **query.py** -- query GCAM to extract results
    * currently based on ModelInterface, but write it to use alternate, lighter-weight method if one is provided
    * create and run batch query
    * read query result
    * run a query and return result in DataFrame
	* add anything for aggregation, given DataFrame API?
	  * add or drop columns?
	  * find first/all records with field X = Y
	  * something that "knows" about time step data
	  
  * **bioenergy.py** -- functions specific to bioenergy-related XML files
    * liquid fuel and biomass related stuff
    
  * **other sectors?**
  	* if there's adequate time/budget, develop APIs to some of the other sectors that users are commonly manipulating.
  	* otherwise, provide as high-level a sector-agnostic API as possible 
  
  * **plot.py** -- API to generating plots
    * stacked and unstacked barcharts
    * line plot for time-series (with optional confidence interval, for use by gcammcs)
    * pie charts of shares in some dimension (sector, region, etc.)

  
## Parallelization

The runProject script serializes all steps, which is fine for running on a desktop computer,
but for use on a cluster, it would be much more time-efficient to parallelize mutually
independent tasks.
 
One way to do this would be using the Jug package. A Jug script is a Python script that uses
the decorator @TaskGenerator and is run by the jug command-line script. It's mostly normal
Python code; the dependencies among tasks are determined from usage in the code.
 
 To use this, we'd want to call functions in pygcam.project or perhaps extract the jug stuff
 into pycam.parallel so it's optional.
 
 To create dependencies, each <step> would be called as a Jug task:
 
     from jug import TaskGenerator

     @TaskGenerator
     def runStep(name, seq):
        status = 0
        # run the step
        key = "%s-%s" % (seq, name)
        return "%s:success" % (key, 'OK' if status == 0 else 'failed') 
     
     @TaskGenerator
     def runScenario(name, steps=None):
        stepStatus = [runStep(*step) for step in steps] 
        
     @TaskGenerator
     def runProject(name, scenarios=None, steps=None):
        """
        Have a function, say, project.getStepList(name, scenarios, steps)
        that is like listSteps, only it produces a list of tuples of
        (scenario, step, seq) that refers back to the list of tasks read
        from project.xml, e.g., [('setup', 1, 
        """
        pass

Jug does nothing itself as far as clusters are concerned. You have to launch the jugfile
multiple times on a processor to get parallelism.

So do this: (?)

  * Process the user's command-line request to build the dependency graph
  * Queue multiple jobs (if needed) using multiple cores (one per parallelizable task)
  * Maybe need to rethink cleanup of XML database since it's not all in one task
    (though it might work if it's all called by one job script...)
    
Example: 3 scenarios, each with a baseline and 4 policies.

  * the baselines can run in parallel, on one node, with 4 cores
  
    * Could use the feature of queueGCAM that calls a batch script directly,
      since these are always serial tasks.
    * After all queries are done, the DB can be deleted.
    
  * once each baseline completes, all the policy scenarios can be run
    in parallel for that scenario. How to get this to happen on other cores?
    
  * Maybe all that's needed is to queue a job per scenario, where the baseline
    runs, queries are performed, and then each scenario is run on a separate core.
    
    * Call queue() once for each scenario.
    
