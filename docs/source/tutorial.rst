Tutorial
=========

.. note::

   *This tutorial is currently under development.*

Elements to understand:

  * Configuration file
  * gt command and sub-commands
  * project.xml
  * rewrite sets
  * query specifications (two forms -- move doc from pygcam.query to non-programmer page)
  * setup -- the most challenging bit still


Overview
----------
Here we provide a brief introduction to the elements of this tutorial. The tutorial
explains how to setup ``pygcam`` and manage the GCAM workflow. The steps involved
in using ``pygcam`` are explained briefly here, and in more
detail in the sections that follow.


1. Install pygcam
^^^^^^^^^^^^^^^^^^^

Before using ``pygcam``, you must install a Python 2.7 environment and then
install the ``pygcam`` package. See the :doc:`install` page for details.
Windows users should also see :ref:`windows-label`.

2. Configure pygcam
^^^^^^^^^^^^^^^^^^^^
The ``pygcam`` scripts and libraries rely on a configuration file to:

  * define the location of essential and optional files,
  * allow the user to set defaults for many command-line arguments to scripts, and
  * define both global default and project-specific values for all parameters

See :ref:`Initial Configuration <initial-configuration-label>` for how to set up
the configuration file for the first time, and the :doc:`config` page for
detailed information about the configuration file.

3. Define the project
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Many of the features of the :doc:`gcamtool` script can be used directly without
setting up a project definition. However, the full workflow-management capabilities
of ``pygcam`` require an XML-based project definition file that describes:

* one or more projects that may have different workflow steps
* one or more "scenario groups" that define a baseline and related policy scenarios
* a set of steps to perform (e.g., run GCAM, query the database, compute differences
  between scenario results, plot figures of scenario results and differences from
  baselines.)
* data required by some of the steps

See :doc:`project-xml` for a detailed description of the file's XML schema.

.. note::

   The :ref:`new <new-label>` sub-command of the :doc:`gcamtool` script can be used to create the
   initial structure and files required for a new project, and optionally, insert
   a section for the new project in the ``$HOME/.pygcam.cfg`` configuration file.


4. Setup the project files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The :ref:`setup <setup-label>` sub-command of the :doc:`gcamtool` script provides
support for modifying GCAM's XML data files and configuration file according to
the needs of your project. See :doc:`setup` for details.

This is the only step of the pygcam workflow process that requires Python programming.
Work is underway to allow simple projects to be defined without requiring Python code.


5. Run the project
^^^^^^^^^^^^^^^^^^^^^
Project workflow is managed using the :ref:`run <run-label>` sub-command of the
:doc:`gcamtool` script, which reads the :doc:`project-xml` file to
understand the project setup, and offers numerous options allowing you
to choose which project, scenario group, or scenarios to operate on and which
steps to run.


------------------------------------------

.. _initial-configuration-label:

Initial configuration
-----------------------

The ``pygcam`` package uses a configuration file called ``.pygcam.cfg``, stored in
the user's home directory, i.e., ``$(HOME)/.pygcam.cfg``. When ``gt`` runs, it
checks whether this file exists. If the file is not found, it is created with all
available configuration parameters shown in comments (i.e., lines starting with '#')
explaining their purpose and showing their default values. To uncomment a line,
simply remove the leading '#' character.

Edit the configuration file with any editor capable of
working with plain text---not a word-processor such as Word. You can use
the command ``gt config -e`` to invoke a system-appropriate editor on the
configuration file. See the :doc:`config` page for details.

Configuration file sections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The configuration file is divided into sections indicated by a name in square brackets.
All variable declarations following a section declaration, until the next section
declaration (if any) appear in the declared section. You can declare a section multiple
times to add new values to the section.
(See :ref:`Sample Configuration File <sample-config-label>`, below.)

Project sections
~~~~~~~~~~~~~~~~~~
Each project should have its own section. For example, to setup a project called, say,
"Paper1", I would create the section ``[Paper1]``. Following this, I would define variables
particular to this project, e.g., where the to find the files defining scenarios, queries,
and so on.

Default section
~~~~~~~~~~~~~~~~~
Default values are defined in the ``[DEFAULT]`` section. When ``pygcam`` requests the value
of a variable from a project section, the default value is returned if the variable is not
defined in the project section. Variables that you want to set uniformly for all of your
projects can be defined in the ``[DEFAULT]`` section.

All pre-defined ``pygcam`` variables are defined in the ``[DEFAULT]`` section,
allowing them to be overridden on a project-by-project basis.

.. _sample-config-label:

Sample configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Below is a sample configuration file for a project called ``Paper1``. The user has
created some (non-pygcam) variables prefixed by ``User.``. The prefixes are merely a
convention to identify standard pygcam variables. For user-defined variables, use any
prefix desired, or none at all.

 .. code-block:: cfg

    [DEFAULT]
    GCAM.DefaultProject = Paper1

    User.RepoRoot       = %(Home)s/git-repo
    GCAM.SandboxRoot    = %(Home)s/ws

    GCAM.LogLevel       = INFO
    GCAM.ShowStackTrace = True
    GCAM.ModelInterfaceLogFile = %(Home)s/tmp/mi.log
    GCAM.UseVirtualBuffer = True

    GCAM.Root           = %(Home)s/GCAM
    GCAM.RefWorkspace   = %(GCAM.Current)s/Main_User_Workspace
    GCAM.ModelInterface = /pic/projects/GCAM/ModelInterface
    GCAM.JavaLibPath    = /pic/projects/GCAM/GCAM-libraries/lib/basex
    GCAM.OtherBatchArgs = -A my_account

    GCAM.QueryDir  = %(GCAM.ProjectDir)s/queries
    GCAM.QueryPath = %(GCAM.QueryDir)s

    # Default location for query results
    GCAM.OutputDir = %(Home)s/ws/output

    # Setup config files to not write extraneous files, so of which are very large
    GCAM.WriteDebugFile     = False
    GCAM.WritePrices        = False
    GCAM.WriteXmlOutputFile = False
    GCAM.WriteOutputCsv     = False

    [Paper1]
    GCAM.RegionMapFile = %(GCAM.ProjectDir)s/etc/Regions.txt

------------------------------------------------


Running a GCAM experiment
----------------------------
The basic GCAM experiment consists of a running a baseline scenario and one or more policy
scenarios that are compared to the baseline. In ``pygcam``, the experiment is defined in
a :doc:`project-xml` file, the location of which is specified by the config parameter
``GCAM.ProjectXmlFile``, which defaults to ``%(GCAM.ProjectDir)s/etc/project.xml``.

The :doc:`project-xml` file describes all the workflow steps required to setup, run, and
analyze the scenarios. The entire workflow or select steps can be run using the gcamtool
`:ref: run <run-label>` sub-command.


