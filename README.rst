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
