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

  
