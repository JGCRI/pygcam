pygcam
=======

``pygcam`` is a Python package
that provides classes, functions, and scripts for working with GCAM.

Core functionality
------------------

* Project workflow management framework that lets you define steps to run and
  run them all or run steps selectively.

* The main ``gt`` (think "gcamtool") script, which provides numerous
  sub-commands, and can be extended by writing plug-ins.

* The ``gt`` sub-commands facilitate key steps in working with GCAM, including:

  * Setting up experiments by modifying XML input files and configuration.xml
  * Running GCAM, locally or by queueing jobs on a Linux cluster
  * Querying the GCAM database to extract results to CSV files
  * Interpolating between time-steps and computing differences between baseline and policy cases
  * Plotting results

* The scripts are based on the pygcam API, which is fully documented on readthedocs.org.
  Use the scripts or API to develop your own custom applications or plug-ins for use with
  gt.

* Scripts that provide flexible command-line interfaces to the functionality provided by
  the library.

* Customization through an extensive configuration system

How do I get set up?
----------------------

* Users on OS X and Windows platforms can download a zip file with an all-in-one
  directory that has everything you need to run the "gt" (gcamtool) command.

* Linux users and anyone wishing to use ``pygcam`` for Python development should
  install it as a normal Python package. The easiest way to to install directly from
  PyPi:

    ``pip install pygcam``

  Alternatively, clone the repository or download the tarball and run this command
  on the included setup.py file:

    ``python setup.py install``

  or, if you want to edit the code or stay abreast of code changes, you might install
  it in "developer" mode:

    ``python setup.py develop``

Contribution guidelines
------------------------

* TBD

Who do I talk to?
------------------

* Richard Plevin (rich@plevin.com)

Release Notes
==============

Version 1.0b2
--------------
* If you were stymied by the installation process, you can try the new zipped all-in-one directory 
  that bundles everything needed to run gcamtool (the "gt" command) without any additional downloads 
  or installation steps other than setting your PATH variable. This works only for Mac and Windows. 
  See http://pygcam.readthedocs.io/en/latest/install.html for details.

* A new feature of the "run" sub-command lets your run a scenario group on a cluster with one 
  command. The baseline is queued and all policy scenarios are queued with a dependency on completion
  of the baseline job. Just specify the -D option to the run sub-command.

  You can run all scenarios for all scenario groups of a project this way by specifying the -D (or 
  --distribute) and -a (or --allGroups) flags together. All baselines will start immediately with all
  policy scenarios queued as dependent on the corresponding baseline.

* The requirement to install xmlstarlet has been eliminated: all XML manipulation is now coded
  in Python, but it's still fast since it uses the same libxml2 library that xmlstartlet is based on.

* All configuration variables have been updated with defaults appropriate for GCAM 4.3.

* The "group" attribute of project <step> elements now is treated as a regular expression of an exact
  match is not found. So if you have, say, groups FuelShock-0.9 and FuelShock-1.0, you can declare a 
  step like the following that applies to both groups:

	``<step name="plotCI" runFor="policy" group="FuelShock"> ... some command ... </step>``

* Updated carbon tax generator. This can be called from a scenarios.xml file as follows (default 
  values are shown):

	``<function name="taxCarbon">initialValue, startYear=2020, endYear=2100, timestep=5, rate=0.05, regions=GCAM_32_REGIONS, market='global'</function>``

  * The regions argument must be a list of regions in Python syntax, e.g., ["USA"] or ["USA", "EU27"]. 
  * It creates the carbon tax policy in a file called carbon-tax-{market-name}.xml, which is added
    automatically to the current configuration file.