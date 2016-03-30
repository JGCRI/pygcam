Introduction
============

The `pygcam` package offers Python-based software tools to help GCAM users work more efficiently with the
model. The tools are intended to meet the needs of different types of users, from basic users who just
want to run the model, to "power" users interested in writing custom scripts, to software developers
wanting to write new tools like graphical user interfaces for working with GCAM.

The main components include:

  * **Software libraries** that simplify development of higher-level software tools (graphical interfaces, scripts)
    that interface with GCAM. The library will provide an Application Programming Interface (API) to the GCAM input
    and output data, and to running GCAM, querying results, and performing common processing tasks such as computing
    differences between policy and baseline scenarios and plotting results.

  ..

  * **Command-line tools** built upon the library described above to package commonly required functionality into a convenient
    form for direct use and to support development of higher-level, custom scripts.

  ..

  * **A Monte Carlo Simulation framework** using GCAM on high-performance computers, allowing users to explore
    uncertainty in model outputs resulting from uncertainty in model inputs, and to characterize the contribution of
    individual parameters to variance in output metrics.

  .. * (Eventually) **Graphical User Interfaces** that simplify use of the libraries and tools as well
     as providing unique capabilities such as graphical exploration and comparison of sets of model
     results.

  * **User documentation** for all of the above.

  ..

  * **Cross-platform capability** on Windows, Mac OS X, and Linux.

  ..

  * **Installer scripts** to simplify installation of tools on users’ computers.


Managing Scenarios
------------------

In GCAM, a *scenario* is just a name assigned within a configuration
file to distinguish runs of GCAM. The scenario name is set in GCAM's
configuration.xml and appears in the upper-left panel of the ModelInterface
application.

In ``pygcam``, the *scenario* concept is made more helpful by implementing
a few simple conventions regarding directory structure and filenames. Using
a consistent structure simplifies use of the library and tools since more
information can be conveyed through the scenario name. The "setup tools" (to
be documented) follow these conventions when generating modified XML, allowing
the other workflow scripts to find the resulting files.

Scenario conventions
^^^^^^^^^^^^^^^^^^^^

We extend the definition of *scenario* to identify a set of XML files that
are used together. In this approach, "scenario" refers to both the name
assigned in a configuration.xml file and a corresponding directory holding
customized XML files, and a configuration file called ``config.xml``.


Managing multiple workspaces
----------------------------

The tools are most convenient to use if you follow the file layout created by
the "setup tools". It is not required to use these tools or this file structure,
but everything is designed to simplify coordination between the programs.
Many of these (absolute and relative) directory locations can be modified to
suit your preferences via the ``pygcam`` configuration file.

This file layout assumes you have multiple projects, and each project involves
multiple baseline and policy scenarios. These project files can all be stored in
a central GCAM work area, which each project folder holding all scenarios for a
project. Consider the following directory structure:

  * ~/workspaces

    * project1

      * scenario.a

        * <custom XML files>
        * config.xml

      * scenario.b

        * <custom XML files>
        * config.xml

    * project2

      * myScenario

        * <custom XML files>
        * config.xml

      * yourScenario

        * <custom XML files>
        * config.xml


With this approach, the script ``queueGCAM.py`` can get the main workspace
location from the variable ``GCAM.WorkspaceRoot`` from the configuration file
``~.pygcam.cfg`` (which, in this approach can be set once for all projects)
and you need only pass the scenario name and project name, allowing the path
to the configuration XML file to computed as
``{GCAM.WorkspaceRoot}/{project}/{scenario}/config.xml``.


XML Setup Tools
---------------

The R-based gcam-data-system (GDS) that comes with GCAM is an excellent
method for managing the core GCAM input files. It is an essential tool for
changing global parameters such as GDP and population whose influence spans
multiple values across XML files.

The GDS, however, is relatively "heavy-weight". Modifying input files
is accomplished most safely by copying the entire ``gcam-data-system``
directory, modifying some CSV inputs, and regenerating the XML
files. This approach doesn't facilitate small-scale changes in select
files. Nor does it address changes to configuration files.

A more subtle issue with relying on the GDS is that any changes to
data values in CSV files must be documented outside the CSV
files. Separating changes from the documentation of those changes
eventually results in divergence between the two.

A lighter-weight approach is to modify the XML files generated by the
R-based system. Manually editing XML files is relatively easy to do,
but keeping files synchronized--so that policy files include all the
changes made in baseline files, for example--is a manual process, and
therefore error-prone.

The GCAM XML-Setup tools were designed to address all of these issues.

Introduction
^^^^^^^^^^^^

The Setup Tool system is a based on a Python module that operates
on standard GCAM input XML files to create modified copies of
designated files and to manage corresponding modifications to the
configuration.xml file. The system can be thought of as an API to
XML files controlling much of GCAM's behavior.

The user-defined Python scripts and any hand-coded XML files
constitute the "source code" used to generate XML data and
configuration files described by the scripts. The generated XML files
are written to a ``local-xml`` folder identified by the user's setup
script.

The module includes a "scenario" class that identifies scenarios
relationships, i.e., that a given policy scenario is based on a
particular baseline scenario. The structure can have an arbitrary
number of layers. For example, a "bioenergy baseline" scenario may be
shared across several analyses, each of which refines the shared
scenario to create a baseline specific to the analysis.

Core functionality
^^^^^^^^^^^^^^^^^^^^

The setup module provides functions that automate the manipulation of XML files, including:

  * Creation of a ``local-xml`` folder in a user-specified location, and per-project folders
    within ``local-xml`` to organize files used for different analyses.

  * Programmatically editing input XML files by copying the designated
    files from the "parent" scenario and creating scenario-specific
    versions within the local-xml project folder. Editing is performed
    using the ``xmlstarlet`` command-line program.
    (See http://xmlstar.sourceforge.net)

  * Likewise, the parent scenario's ``config.xml`` file is copied
    and modified as indicated by the scenario setup script.

  * Automation of arbitrarily complex, multi-file changes ensures that
    all required changes are handled correctly and consistently.

  * Support for dynamically generating policy constraint files that
    compute constraint values based on baseline scenario results. This
    is used primarily for Monte Carlo simulations, in which the
    baseline results for each trial generally differ.

  * Generic GCAM XML functions:

    * Set scenario name, stop period, climate output interval, solution
      tolerance.

    * Add, update, and delete scenario components from
      configuration.xml.

    * Add policy definition and constraint file pairs.

    * Extract a definition from the global technology database and
      create a regional copy for further customization.

    * Currently defined functions can modify performance coefficients,
      non-energy-cost, shutdown rate for specified technologies, residue supply curves,
      and more.


Main benefits
^^^^^^^^^^^^^^^^

  * Automates and simplifies modification of XML files. Less
    error-prone than manually editing these files.

  * Documents changes made to the standard GCAM setup, without
    requiring maintenance of ancillary files. (The script becomes
    the documentation.)

  * Facilitates management of scripts (rather than large XML files) in
    a version control system such as ``svn`` or ``git``.

  * Centralizes common functionality. Modifications to the Python
    module are immediately available to all projects.

  * Simplifies synchronization between baseline and policy scenarios:
    after updating the baseline script (adding constraints, changing
    stop-period, etc.), re-running the policy setup scripts keep
    everything synchronized.
