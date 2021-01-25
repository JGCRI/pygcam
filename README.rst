pygcam
=======

``pygcam`` is a Python package that provides classes, functions, and scripts for working with GCAM.

Core functionality
------------------

* Project workflow management framework that lets you define steps to run and
  run them all or run steps selectively.

* The main ``gt`` (GCAM tool) script, which provides numerous
  sub-commands, and can be extended by writing plug-ins.

* The ``gt`` sub-commands facilitate key steps in working with GCAM, including:

  * Setting up experiments by modifying XML input files and configuration.xml
  * Running GCAM, locally or by queueing jobs on a Linux cluster
  * Querying the GCAM database to extract results to CSV files
  * Interpolating between time-steps and computing differences between baseline and policy cases
  * Plotting results

How do I get set up?
----------------------

* See http://pygcam.readthedocs.io/en/latest/install.html

Who do I talk to?
------------------

* Richard Plevin (rich@plevin.com)


Release Notes
==============

Version 1.10.2 (25 Jan 2021)
----------------------------
* Updated default files in system.cfg for GCAM 5.3

Version 1.10.1 (22 Jan 2021)
----------------------------
* Fixed bug in query.runBatchQuery() reported by user huanglin6385. (Thanks!)

Version 1.10.0 (20 Dec 2020)
----------------------------
* Fixed long-standing bug in "init" sub-command. Note that this also fixed a problem with the generated
  documentation at pygcam.readthedocs.org that prevented the sub-command docs from generating correctly.
* Numerous internal improvements to Monte Carlo / cluster management subsystem
* The XML <query> element now takes an optional "states" parameter to set the default scope of queries.
  The old default behavior is unchanged: the query is run on the 32 global GCAM regions.

  The full set of options is:
    'withGlobal'   # return states and global regions in one list
    'withUSA'      # return states and USA region only
    'only'         # return states only, excluding the 32 global regions
    'none'         # return only global regions, i.e., no states

* New "region discovery" feature looks to the XML files in use to see if you're running GCAM-USA.
  This hasn't been tested on all recent versions of GCAM. To disable it, set the config variable:

    GCAM.RegionDiscovery = False

* User can now set location of JAVA home directory using config variable "GCAM.JavaHome"

* Updated version of Dash and modified code as necessary for compatibility

Version 1.9.0 (16 Mar 2020)
---------------------------
* "transport" command and function "transportTechEfficiency"
* new "buildingElec" command for creating building electrification policies
* updates to "building" command
* numerous updates to callable functions setRegionalShareWeights and setInterpolationFunction
* modified setup step to remove stale local-xml files when setting up a scenario
* numerous updates to MCS subsystem
* improved support for using "restart" files

Many thanks to Robbie Orvis of Energy Innovation for funding the development
of the three new policy-oriented features: "res", "building", and "transport".

Version 1.8.0 (6 Nov 2019)
---------------------------
* Updated "res" sub-command to generate Renewable Energy Standards for 32 regions and for GCAM-USA.
* Update "init" sub-command to recognize recent GCAM versions, updated default version to 5.1.3.
  (This will be updated to GCAM 5.2 after testing with that version is completed.)
* Added support for making incremental improvements to building energy efficiencies, including
  - A new sub-command, "building" which creates a CSV template that can be modified to set the percentage
  improvement in building energy use by sector, subsector, technology, energy input, and year.
  - A new callable method, "buildingTechEfficiency" that converts the CSV file to the required XML and
    adds an entry to the configuration.xml to load the generated file.

Version 1.7.0 (29 Jul 2019)
---------------------------
* GCAM regions are now read from the data system, if present. This supports use of other regionalizations.
* Added "callable" functions (callable from scenarios.xml) to:
  * Freeze population at any given year
  * Modify non-CO2 emission coefficients
  * Perform string replacement in generated config files (e.g., to change which "xml" dir to read from)
* Adjusted which files to copy/link on Windows
* Added "exe/restart" to list of files to copy
* MCS: xlabel on distribution plots is now set from units column in database "output" table
* Improved RF subplots

Version 1.6.2 (20 Feb 2019)
---------------------------
* Added ability to specify RES policy in a simple CSV file.

Version 1.6.1 (20 Feb 2019)
---------------------------
* Fix documentation build problems

Version 1.6.0 (19 Feb 2019)
---------------------------
* Added "res" sub-command, which reads a new XML file describing a set of renewable energy
  standards that can vary by region, year, and technology, and writes a GCAM XML input file
  that implements the policies.

Version 1.5.4 (13 Nov 2018)
---------------------------
* Added option to `gt analyze` to limit the number of variables displayed in tornado plots.


Version 1.5.3 (12 Nov 2018)
---------------------------
* Fixed another bug in `gt init` in setting Java home directory.
* Fixed error in new land-protection code.

Version 1.5.2 (8 Nov 2018)
---------------------------
* Version number is taken from gcam directory name (if possible) if executable doesn't accept `--versionID` flag.
* Corrected version number of tornado package in macOS YML file.

Version 1.5.1 (7 Nov 2018)
---------------------------
* Fixed bug preventing `gt init` from working properly in interactive mode.
* Updated YML files for creating pygcam-ready Anaconda environments for Python 2 and 3.
* Updated installation instructions to correspond with new YML files.
* Added string match functions to Constraint: startswith, endswith, contains are now supported.

Version 1.4.3 (29 Oct 2018)
---------------------------
* Fixed pathname bug that prevented multiple function calls on the same file
  (specified in scenarios.xml) to work correctly.


Version 1.4.2 (29 Oct 2018)
---------------------------
* Fixed detection of symbolic links on Windows
* Added support for suppressing "restart" files in v5.1.2 and later.
  (Set config variable `GCAM.WriteRestartFiles = False`)


Version 1.4.1 (24 Oct 2018)
---------------------------
* Fix for GCAM v5.1.2: create required 'restart' directory in sandbox 'exe' folder


Version 1.4 (12 Oct 2018)
---------------------------

* Pygcam now runs under Python versions 2.7 and 3.7.

* Updated example/tutorial project files to use GCAM 5.x query names

Version 1.3.0 (5 Oct 2018)
----------------------------
* Bug fixes in support of 5.1.1 on Windows

* Added option (``-P/--asPercentChange``) to ``diff`` sub-command to compute percent-change.

* Several revisions to Monte Carlo Simulation processing:

  * Made policy scenarios dependent on completion of baseline scenarios so that for
    any trial number, the baseline runs first, after which any policies can run. This
    affects only uses of ``gt runsim`` for which both a baseline and at least one
    policy scenario are specified.
  * Updated ipyparallel requirement to version 6.2.2 on MacOS and Linux (not used on Windows).
  * Added new option (``-E`` *filename*) to ``analyze`` sub-command to write all
    inputs and outputs to a single CSV file.
  * The default is now to shutdown idle engines when there are no unallocated tasks.
    This can be disabled with the new ``-I/--dontShutdownIdle`` flag
  * Added new distribution for logfactor Triangle: ``logfactor=3`` means a triangle
    with min, mode, max = (1/3, 1, 3)
  * Added symlink from "output" to temporary directory if ``MCS.TempOutputDir`` is defined,
    allowing output to be placed, e.g., on an SSD drive local to a node.
  * The number of engines to run is now computed from the indicated trials, though
    you can still force a value using ``gt runsim -n XXX``. The limit set by
    ``IPP.MaxEngines`` is respected in either case.
  * Created new pseudo-distribution that returns values from a discrete list, in order.
    is used to produce a repeating array of values in the order given. Use this to run
    an explicit set of parameter values. Example: ``<Sequence values="4, 6, 43.2"\>``
  * Converted various dicts to OrderedDicts, allowing user to place write funcs in
    parameters.xml in an order that ensures needed files are saved before read by
    other writeFuncs.
  * Added two keywords to the ``<Result>`` element in ``results.xml``:

    * ``percentage`` divides the difference between (scenario - baseline) by baseline
      to convert result into a percent change. (Use only with "diff" type results.)
    * ``cumulative`` sums values over the full time horizon.

Version 1.2.2 (16 Aug 2018)
----------------------------
* Corrected reading of GCAM's reported version number to use only the first 2 digits.
  That is, version "5.1.1" is now correctly recognized as "5.1".

Version 1.2.1 (4 Aug 2018)
----------------------------

* Support for GCAM v5.1

* Corrected bug in Windows defaults that had set ``GCAM.Temp = C:/tmp``, which is not writable
  by non-admin users. The default is now ``%(Home)s/tmp``.

* Updated approach to land protection to support new geographical land units

* Support for change in the location of model interface in 5.1

* Monte Carlo Simulation improvements:

  * Added units to database and results.xml schema
  * Added support for setting land protection based on reg and basin
  * Added support for ``lowbound`` and ``highbound`` attributes in ``<Distribution>`` element. Bounds
    are applied to values produced by add/multiply/replace. This can be used to ensure that the
    resulting values are, say, between 0 and 1.

Version 1.1.3 (11 Jul 2018)
----------------------------
* Numerous tweaks to Monte Carlo simulation subsystem to allow placement
  of output and temporary files in chosen directories. The model's memory
  footprint has grown substantially in v5.0, creating challenges for earlier
  approaches to running many GCAM instances on a cluster. These changes
  allow the XML database to be placed on a local tmp or SSD drive on a
  compute node while query output can be written to persistent storage.

* Preliminary support for GCAM v5.1 -- note that pygcam v1.1.3 does not
  yet work completely with GCAM 5.1, which has moved the XML input files
  to a new location. Stay tuned!

* Performance improvements in writing to the sqlite3 database holding MCS
  status and results.

* Updated support for Monte Carlo simulations on NERSC.gov.

* Added preliminary support for dockerizing GCAM and pygcam. See, for example,
  https://hub.docker.com/r/plevin/pygcam-v1.0.1. The idea is that a Docker
  container is pre-loaded with some version of GCAM and pygcam, and it can
  be run using a script that mounts host directories inside the container and
  maps host locations in .pygcam.cfg to locations in the Linux container.
  Let me know if you want to use this and I can share the work
  in progress.

Version 1.0.1 (15 Nov 2017)
-----------------------------
* Corrected .yml files to put ``semver`` specification in correct section.

* Allow ``gt --version`` to run without having an .pygcam.cfg file in place.

* Updated instructions for running on Windows to include using the Anaconda prompt.

* Configuration variable ``GCAM.VersionNumber`` is set based on the GCAM
  executable's reported version.

Version 1.0.0 (14 Nov 2017)
-----------------------------
* Added code to gcam sub-command to create link to java libs on macOS,
  as is done in the run-gcam.command script in the Mac distribution.

* A bug in the ModelInterface code in gcam-v4.4 prevented the ``pygcam``
  query sub-command from working. Please install gcam-v4.4.1 (when available)
  or update your the gcam-v4.4 installation, replacing the file
  ``.../input/gcam-data-system/_common/ModelInterface/src/ModelInterface.jar``
  with the updated file, available
  `here <https://github.com/JGCRI/pygcam/releases/download/v1.0rc5/ModelInterface.jar>`_

* Modified ``init`` sub-command to use prompt_toolkit to provide
  filename completion via the tab key. This works on Windows only
  from a standard command prompt, not from a Cygwin terminal. (The
  ``init`` sub-command works, but without filename completion.)

* Added check that config variable GCAM.VersionNumber matches what the
  GCAM executable reports. If different, the config var is set as per
  the GCAM executable.

Version 1.0rc5 (6 Nov 2017)
-----------------------------
* Modified .yml installation files to deal with problem
  installing SALib.

Version 1.0rc4 (5 Nov 2017)
-----------------------------
* Much improved ``init`` sub-command and detection of missing
  configuration file, guiding user to run the ``init`` command.
  The ``init`` command now sets up the tutorial files by default.

* Improved tutorial to work with files provided by ``init``,
  and improved documentation in general.

* Configuration defaults are now saved to ~/.pygcam.defaults
  rather than cluttering the ~/.pygcam.cfg configuration file
  with this information.

* Eliminated config vars GCAM.Root and GCAM.Current in favor
  of GCAM.RefWorkspace. Some users may have to adjust their config
  files.

Version 1.0rc1 (2 Nov 2017)
-----------------------------
* Revised installation procedure now uses Anaconda environments to
  ensure Python package compatibility. Dropped "pyinstaller" versions.

* Created "conditional XML" to allow portions of XML input files to
  be selected based on the value of configuration and/or environment
  variables.

* All environment variables are now available in the configuration
  system as ``$`` prefixed names as in Unix shells. That is, you can access,
  say, the ``USER`` environment variable as ``%($USER)s`` in the config file.

* Modified configuration of the logging system to allow Log Level to be set
  globally and/or by individual modules.

* Created browser-based "MCS Explorer" to help analyze Monte Carlo results.
  Features include distributions of results, tornado plots of uncertainty
  importance, scatterplots of inputs vs outputs, and an interactive
  parallel-coordinate plot for exploring parameter interactions.

* Created browser-based GUI that provides interactive access to all features
  of the "gt" (gcamtool) command.

* Merged pygcam-mcs into pygcam. Use command ``gt mcs on`` to enable the
  Monte Carlo features. Note that MCS support is available only on Linux currently.

* Created sub-command ``ippsetup`` to configure ipython-parallel for the
  Slurm resource manager. Support for PBS and LSF is possible is users
  request it.

* Re-designed the MCS framework to use ipython-parallel. Workers now
  receive instructions from the ipyparallel controller and return results
  to the controller, which updates the database.

* Added "optional" attribute to the ``<step>`` element to allow some steps
  to be defined for occasional use. Elements marked optional="true" are
  run only if explicitly mentioned on the command-line (via the -s flag).

* The "query" sub-command now accepts arguments (``+b`` and ``+B``) to control
  processing of pre-formed batch query files.

* Modified all "global" single-letter arguments to use "+" prefix rather
  than "-" prefix, e.g., "gt +P my-project run" to specify the project
  to run. Long names retain the "--" prefix, e.g., "gt --projectName my-proj".

Version 1.0b12 (22 May 2017)
-----------------------------
* No new features, just updates to get documentation building
  properly on ReadTheDocs.org.

Version 1.0b11 (17 May 2017)
-----------------------------
* Created "init" command to interactively set key config variables

* Added config variables GCAM.LogFileFormat and GCAM.LogConsoleFormat to
  customize the messages produced by the logging system.

* Added setPriceElasticity function, callable from scenarios.xml scripts

* Improved GCAM installation script to work across all 3 GCAM platforms.

* Fixed home drive / home directory access on Windows

* Added "saveAs" attribute to query specification to allow a query
  to be rewritten (i.e., aggregated) different ways and saved to CSV
  files with different names.


Version 1.0b10 (9 Feb 2017)
-----------------------------
* Fixed bugs in pyinstaller versions


Version 1.0b9 (8 Feb 2017)
-----------------------------
* Changed default value of GCAM.SandboxRoot from {GCAM.Root}/ws to
  {GCAM.Root}/sandbox

* Added "mi" sub-command to invoke ModelInterface from the command-line after
  creating a model_interface.properties file that refers to the project's
  custom query file (if GCAM.MI.QueryFile is set) or to the reference query file.

* Various fixes for the "one-directory" version of pygcam installer

* Improved install-gcam.py script

* Addressed matplotlib issue on Macs

Version 1.0b8 (31 Jan 2017)
-----------------------------
* Added label to identify default scenario group in listing groups via "gt run -G"

* Added function to carbonTax.py to create linked land-use change CO2 to carbon
  tax or cap policies:

  ``genLinkedBioCarbonPolicyFile(filename, market='global', regions=None, forTax=True, forCap=False)``

* Also added function (bioCarbonTax) callable from XML setup file to access this feature.

* Added initial support to integrate pygcam-mcs (coming soon!)

Version 1.0b7 (6 Dec 2016)
-----------------------------
* Made the <scenariosFile> element optional in project.xml, using the value of
  GCAM.ScenarioSetupFile by default.

* Added function callable from setup XML, <protectionScenario name="xxx"/>, which
  indicates a protection scenario to use from the file defined by config variable
  GCAM.ProtectionXmlFile.

* Reversed previous modification to handling of "gt config -e" (edit config file)
  which had placed quotes around the value of `GCAM.TextEditor`. This breaks
  commands like "emacs -nw" since this is now seen as the command name. Solution is
  for users with spaces within a command name to add the quotes in the config file, e.g.,

  ``GCAM.TextEditor = "c:/Programs/Some Path With Spaces/someEditor.exe"``

* Added check to prevent deletion of files within reference workspace, which could
  happen under specific circumstances with symbolic links.

* Added new "srcGroupDir" attribute to <scenario> element to identify a directory
  holding static XML files for a scenario, allowing related scenarios to share these
  files without requiring copying or symlinks.

Version 1.0b5 (9 Nov 2016)
-----------------------------

* Minor adjustments to setup to label documentation with correct version and
  to allow symlink warning for Windows to be suppressed by setting config var
  GCAM.SymlinkWarning = False

Version 1.0b4 (9 Nov 2016)
-----------------------------

* Fixed lingering symlink issues on Windows version.

Version 1.0b3 (7 Nov 2016)
-----------------------------

* Fixed several problems with Windows version:

  * Whereas on Linux and OS X, the user's home
    directory is unambiguous, Windows has both ``HOMESHARE`` and ``HOMEPATH``, at least one
    of which should be non-empty, but neither is guaranteed correct. Thus for Windows, the
    user can define ``PYGCAM_HOME`` to be the folder in which to create the ``.pygcam.cfg`
    file. Pygcam looks for the first directory found searching in the order ``PYGCAM_HOME``,
    ``HOMESHARE``, and finally ``HOMEPATH``.

  * Pygcam was attempting to symlink some files and failing if the Windows user didn't have
    symlink permission. This has been corrected to copy in all cases if symlinks fail.

  * When copying is required, pygcam was copying more than was required from the reference
    workspace. (With v4.3, the "input" folder holds much more than just XML files...) The
    copying is now limited to folders containing XML files. (But it's still best if you can
    arrange to have permission to create symbolic links, since that avoids all the copying.)

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
