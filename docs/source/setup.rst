GCAM XML-Setup
=======================

The XML-Setup system provides tools for modifying standard and custom XML
input files that control GCAM's behavior. The XML-Setup system copies the
designated files to the scenario's run-time "sandbox" before modifying them
and updating the GCAM configuration file that tells GCAM which
XML data files to load.

.. note:: The :doc:`pygcam.xmlEditor` module relies on the *XML Starlet* program, a
   command-line tool that can search and edit XML files (among other tricks.) It is
   available for all three GCAM platforms.
   `Download XML Starlet <http://xmlstar.sourceforge.net/download.php>`_.
   It should be included on all modern Linux systems. It is available in binary
   (executable) form for Windows, but must be compiled on Mac OS X. Contact the
   author if you need a copy for the Mac.

User-defined Python scripts and XML files
constitute the "source code" used to generate the XML data and
configuration files described by the scripts. The generated XML files
are written to a directory called ``local-xml`` in the run-time
:ref:`workspace <workspaces-label>`.

.. seealso::

     Command-line usage is described on the :ref:`gt setup <setup>` page.

Usage
------

The XML-Setup system allows scenarios to be defined in XML or in Python.
In addition, functions can be added in Python that are accessible via
XML.

The higher-level XML method should be adequate and more convenient for
many projects. The :doc:`scenarios-xml` page documents the XML file format
and provides a complete example.

Pythonistas should review the API provided by :doc:`pygcam.xmlEditor` and
the many XML-accessible functions available therein.

The :ref:`setup <setup>` sub-command provides options to allow you
to specify either the Python or XML approach. Determination of the file
to use follows this sequence:

  #. If a Python module or an XML setup file is specified on the command-line,
     the indicated file is used.
  #. If neither command-line option is used, the value of configuration file
     variable ``GCAM.ScenarioSetupFile`` is used (if set) as the path to an
     XML file.
  #. If the variable is not set, the ultimate default is to look for a file
     called ``scenarios.py`` at the location computed by combining the value
     of configuration variable ``GCAM.XmlSrc``, an optional group sub-directory,
     and ``scenarios.py``. For example, if ``GCAM.XmlSrc`` is set to
     ``/Users/xyz/project/xmlsrc``, and the group directory ``FuelShock``
     is in use, the path to the Python module would be
     ``/Users/xyz/project/xmlsrc/FuelShock/scenarios.py``.


Python setup scripts
------------------------

The module includes the :doc:`pygcam.xmlEditor` class that provides core XML
editing functionality and identifies scenarios relationships, i.e., that
a given policy scenario is based on a particular baseline scenario. The
structure can have an arbitrary number of layers. For example, a
"bioenergy baseline" scenario may be shared across several analyses, each
of which refines the shared scenario to create a baseline specific to the analysis.

Core features
--------------

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

Workspaces and Sandboxes
-------------------------
Pygcam creates two levels of GCAM workspaces. To distinguish them, the directory in
which GCAM is run is referred to as a `sandbox`. The directory whose contents are
copied and/or symlinked to create the sandbox is referred to as a `workspace`.

To ensure that sets of related runs use the same reference workspace, the
:ref:`setup <setup>` sub-command copies and/or symlinks files from the reference
workspace (identified by config variable ``GCAM.RefWorkspace``) to a directory
called ``Workspace`` in the sandbox directory. This directory is created only when
it doesn't exist already, however you can force the directory to be recreated either
by deleting it manually or via the :ref:`sandbox <sandbox>` sub-command.

Depending on your project workflow (and on Windows, level of administrative privileges)
you can choose to copy or symlink files and directories back to their source. This applies
to both the run-time workspace created from the reference Workspace, and the sandboxes
created from the run-time workspace.

By default, the run-time workspace is created with a symlink to the reference workspace's
``input`` directory, but the ``exe`` directory is copied.

By default, sandboxes are created with symlinks to the run-time workspace's ``input``
directory and the GCAM executable in the ``exe`` directory. The ``output`` directory
and directories used by ``pygcam`` are created as needed.

The following twoo variables control which files to symlink or copy. All required files and
directories not named in these variables are copied. Note that if the config variable
``GCAM.CopyAllFiles`` is set to ``True``, or on Windows, if the user does not have
permission to create symlinks, all files are copied regardless of the settings of these
variables.

      ``GCAM.WorkspaceFilesToLink``
         A list of paths relative to ``GCAM.RefWorkspace`` that should be symlinked to same
         relative location under ``{GCAM.SandboxDir}/Workspace``.

      ``GCAM.SandboxFilesToLink``
         A list of paths relative to ``{GCAM.SandboxDir}/Workspace`` that should be symlinked
         to the same relative location in the current sandbox directory.


Design notes
-------------

Benefits
^^^^^^^^^
  * Automates and simplifies modification of XML files, which is less
    error-prone than manually editing these files.

  * Documents changes made to the standard GCAM setup, without
    requiring maintenance of ancillary files. (The script is
    the documentation.)

  * Facilitates project file management using version control systems such
    as ``svn`` or ``git`` by operating on small scripts rather than large
    XML files.

  * Centralizes common functionality. Modifications to the Python xmlEditor
    module are immediately available to all projects.

  * Simplifies synchronization between baseline and policy scenarios:
    after updating the baseline script (adding constraints, changing
    stop-period, etc.), re-running the policy setup scripts keep
    everything synchronized.

Rationale
^^^^^^^^^^
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
