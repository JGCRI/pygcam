Release Notes
================

pygcam 2.0
-------------

The main new feature of pygcam version 2.0 -- which resulted in a wide
set of changes -- is the ability to run the GCAM data system per trial
in a Monte Carlo simulation (MCS). This enables the application of
distributions to values in data system input (CSV) files, with all
dependent XML files receiving consistent values.

This change required separation of distinct portions of the setup process
so that configuration files could be created and modified before updating
the data system to produce new XML files, and finally modifying the
potentially new XML files if needed in the final setup phase.

In addition, some files that were written when the simulation was
generated (via the ``gensim`` command) in pygcam 1.x needed to be
written per trial, requiring them to be stored in per-trial directories
rather than in shared ones.

The pygcam sandbox structure had been stable for many years and the code
sometimes built these assumptions into pathname creation. All of these had
to be revisted in version 2.0.

Removed features
~~~~~~~~~~~~~~~~~~

* Dropped support for GCAM versions prior to version 5.3

* Dropped support for SALib

* Eliminated infrequently used command-line arguments, opting instead to control these
  via config variables

    * Config vars can be set on the command-line: ``gt --set variable=value``


Configuration Variable Name Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rationalized configuration variable names, prefixing with ``Sandbox`` or ``Project``
in most cases, with these changes:

+-------------------------+----------------------------+
| Old name                | New Name                   |
+=========================+============================+
| GCAM.XmlSrcDir          | GCAM.ProjectXmlSrc         |
+-------------------------+----------------------------+
| GCAM.ProjectXmlFile     | GCAMProjectFile            |
+-------------------------+----------------------------+
| MCS.ParametersFile      | MCS.ProjectParametersFile  |
+-------------------------+----------------------------+
| MCS.Root                | MCS.SandboxRoot            |
+-------------------------+----------------------------+
| MCS.ResultsFile         | MCS.ProjectResultsFile     |
+-------------------------+----------------------------+
| MCS.RunSimsDir          | MCS.SandboxSimsDir         |
+-------------------------+----------------------------+
| MCS.RunDbDir            | MCS.SandboxDbDir           |
+-------------------------+----------------------------+
| MCS.RunDbPath           | MCS.SandboxDbPath          |
+-------------------------+----------------------------+
| MCS.DbURL               | MCS.SandboxDbURL           |
+-------------------------+----------------------------+
| MCS.UserFilesDir        | MCS.ProjectFilesDir        |
+-------------------------+----------------------------+
| MCS.RunWorkspace        | MCS.SandboxWorkspace       |
+-------------------------+----------------------------+
| MCS.RunInputDir         | MCS.SandboxInputDir        |
+-------------------------+----------------------------+
| MCS.PlotDir             | MCS.SandboxPlotDir         |
+-------------------------+----------------------------+
| GCAM.ScenarioSetupFile  | GCAM.ScenariosFile         |
+-------------------------+----------------------------+
| GCAM.ScenarioGroup      | GCAM.ScenarioSubdir        |
+-------------------------+----------------------------+

.. note::
  In pygcam terminology, a `workspace` is an original
  GCAM distribution workspace or a copy thereof. A `sandbox`
  is a subcategory of workspace created by pygcam in which
  GCAM is run for a specific scenario. It generally has links
  back to a shared (non-sandbox) workspace.


Changes to Sandbox Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note:: **VERIFY THIS**

   * (Hopefully) eliminated redundant directory level in {sandbox}/{scenario}/local-xml
     => Workspace/local-xml/{scenario}, resulting in {sandbox}/{scenario}/local-xml/{scenario} by

     * Moving local-xml out of Workspace, to top level shared/{scenario}/local-xml, and
     * Changing symlink to {sandbox}/{scenario}/local-xml => shared/{scenario}/local-xml

   * Revised runtime directory structure for both non-MCS and MCS cases


Code Revisions
~~~~~~~~~~~~~~~~~~~~~

* Refactored to reduce the size of very long (> 2000 line) files.
  New files include file_utils.py, sandbox.py, xml_edit.py

* Debugged existing tests and added many new ones

* Added new setup options to run only config-modifying commands or the
  non-config-modifying commands. This allows the GCAM data system to be
  run between these two setup steps.

.. note:: REVISIT THIS NEXT SECTION

Using sub-directories with scenario groups
------------------------------------------------

* Dropped support for the ``<scenario>`` element's ``subdir`` attribute in scenarios.xml.

* Distinguish and create better names for:

    * <project subdir="xxx">
    * <scenario subdir="xxx">   # dropped support for this, but might still be trickling through
    * scenario group subdir if <scenarioGroup useGroupDir="true">

        * runsim takes (scenario) group name

    * XML group subdir

        * whether to use scenario group in the xmlsrc directory as well, otherwise all files at top level under xmlsrc

    * sandbox group subdir

        * Allows a subdir between {SandboxRoot}/{ProjectName}/{SandboxSubdir}/{scenario}
        * This can differ from scenario group name (is this really necessary?)

* sim_subdir in McsSandbox. New (?)

    * allows multiple simulations (with different reference workspace?) under the same project name
    * Note that this is different than sim_id, which allows multiple simulations using the same GCAM files

