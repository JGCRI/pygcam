GCAM XML-Setup
=======================

This page provides an introduction to the XML-Setup system. The
API is documented with the :doc:`pygcam.xmlEditor` module. See also the
:ref:`setup <setup-label>` sub-command.

The XML-Setup system provides a Python API to the XML input files
that control much of GCAM's behavior.
The XML-Setup system operates  on standard GCAM input XML files to
create modified copies of designated files and to manage corresponding
modifications to the main GCAM ``configuration.xml`` file.

User-defined Python scripts and any hand-coded XML files
constitute the "source code" used to generate XML data and
configuration files described by the scripts. The generated XML files
are written to a ``local-xml`` folder identified by the user's script.

The module includes the :doc:`pygcam.xmlEditor` class that provides core XML
editing functionality and identifies scenarios relationships, i.e., that
a given policy scenario is based on a particular baseline scenario. The
structure can have an arbitrary number of layers. For example, a
"bioenergy baseline" scenario may be shared across several analyses, each
of which refines the shared scenario to create a baseline specific to the analysis.

.. note:: The :doc:`pygcam.xmlEditor` module relies on the *XML Starlet* program, a
   command-line tool that can search and edit XML files (among other tricks.) It is available
   for all three GCAM platforms. `Download XML Starlet <http://xmlstar.sourceforge.net/download.php>`_.
   It should be included on all modern Linux systems. It is available in binary (executable)
   form for Windows, but must be compiled on Mac OS X.


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
