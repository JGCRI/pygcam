Terminology
===========

The following terminology is used throughout the ``pygcam`` documentation.

.. _API-def:

API or Application Programming Interface
  The public classes, methods, and function provided by the ``pygcam``
  module to facilitate construction of custom scripts,
  :ref:`plug-ins <plugin-def>`, and :ref:`setup extensions <setup-ext-def>`.

.. _baseline-scenario-def:

Baseline scenario
  A scenario establishing a starting point from which changes are
  calculated based on running a :ref:`policy scenario <policy-scenario-def>`.

.. _gcamtool-def:

gcamtool
  The main executable Python script that provides command-line access to
  the features of ``pygcam``. It provides a set of "sub-commands" that
  perform specific workflow steps and allow you to run the steps defined
  in a project.

.. _plugin-def:

Plug-in
  Python code that conforms to the :doc:`pygcam.subcommand` protocol,
  making it accessible by :ref:`gcamtool <gcamtool-def>`. Plug-ins have
  access to several useful features of gcamtool, such as controlling
  logging verbosity and the ability to be run in batch-mode on cluster
  computing systems, and running within the same process as gcamtool.

.. _policy-scenario-def:

Policy scenario
  A :ref:`scenario <scenario-def>` that defines a change relative to
  a specific :ref:`baseline <baseline-scenario-def>` scenario.

.. _project-def:

Project definition
  Defines one or more :ref:`scenario groups <scenario-group-def>`, the
  workflow :ref:`steps <step-def>`, and optional :ref:`query <query-def>`
  definitions, and other data that is modified dynamically and stored in
  temporary files for use by project :ref:`steps <step-def>`.

.. _project-file-def:

Project file
  An XML file containing one or more :ref:`project <project-def>` definitions.
  If multiple projects are defined in a single project file, they share data,
  workflow :ref:`steps <step-def>`, and variables that are defined in the
  ``<defaults>`` section. See also: :doc:`project-xml`.

.. _query-def:

Query definitions
  A list of XML queries used to extract data from the GCAM database into CSV
  files. Query definitions can simply be references to queries by name, or they
  can include references to :ref:`rewrite sets <rewrite-sets-def>` to cause
  rewrites to be added to the XML query on-the-fly. See also: :doc:`query-xml`.

.. _rewrite-sets-def:

Rewrite sets
  A set of transformations, defined in XML, to be applied to results of queries
  run against the GCAM database. These are typically used to aggregate query
  results into fewer categories. Rewrite sets allow commonly used sets of
  rewrite commands to be stored separately and assigned a name, allowing them
  to be referenced by :ref:`queries <query-def>` defined in the
  :ref:`project file <project-file-def>` or in a separate XML file.
  See also: :doc:`rewrites-xml`.

.. _sandbox-def:

Sandbox
  A dynamically generated directory containing all the files and directories
  (or links to them) required to run GCAM in isolation from other scenarios.
  See also: :ref:`sandbox <sandbox>` sub-command.

.. _scenario-def:

Scenario
  A single set of input and output files for a specific run of GCAM. Scenarios
  can be :ref:`baselines <baseline-scenario-def>` or
  :ref:`policy <policy-scenario-def>` scenarios. Each scenario is run in its
  own :ref:`sandbox <sandbox-def>`, allowing multiple scenarios to be run
  simultaneously, e.g., on a cluster computing system.

.. _scenario-group-def:

Scenario group
   A set of :ref:`scenarios <scenario-def>` consisting of one
   :ref:`baseline scenario <baseline-scenario-def>` and one or more
   :ref:`policy scenarios <policy-scenario-def>`. A single
   :ref:`project <project-def>` can have multiple scenario groups.
   The baseline for one scenario group can be used as the
   starting point for the baseline in another scenario group within
   the same project.

.. _step-def:

Step
  A command defined in a :ref:`project file <project-file-def>` to execute
  a single workflow step. Commands that begin with the "@" character refer
  to sub-commands within :ref:`gcamtool <gcamtool-def>`.
  See also: :ref:`run <run>` sub-command.

.. _setup-ext-def:

Setup extension
  Python code defining a subclass of the :doc:`XMLEditor <pygcam.xmlEditor>`
  class to perform project-specific setup steps, making them accessible
  from within :ref:`setup XML <setup-xml-def>` files.

.. _setup-xml-def:

Setup XML
  An XML file providing instructions for how to transform reference GCAM
  XML files as required to run desired scenarios. See also: :doc:`scenarios-xml`.
