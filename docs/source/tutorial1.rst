Tutorial, Part 1
=================

1.0 Introduction
-----------------
The command-line interface to ``pygcam`` uses the :doc:`gcamtool` script,
which is installed when you install ``pygcam``. In this tutorial, we focus on the
:ref:`run <run-label>`
sub-command, which performs actions defined in the :doc:`project-xml` file, the location
of which is specified by the config parameter ``GCAM.ProjectXmlFile``, which defaults to
``%(GCAM.ProjectDir)s/etc/project.xml``.

The basic GCAM workflow consists of a defining and running a baseline scenario and one
or more policy scenarios, and then comparing the policy cases to the baseline.

  - The :doc:`project-xml` file describes all the workflow steps required to setup, run, and
    analyze the scenarios.

  - The :doc:`scenarios-xml` file defines the required modification to reference GCAM input
    XML files required to implement the desired scenarios.

The entire workflow or select steps can be run using the :ref:`run <run-label>` sub-command.

.. code-block:: sh

   $ gt run

With no other options specified (as above), the default scenario group (identified in
the project.xml file) of the default project (defined in your configuration file) will
be run, starting with the scenario identified as the baseline, followed by all
policy scenarios. All defined workflow steps will be executed in the order defined,
for all scenarios.

There are several general options available to the :doc:`gcamtool` command that apply
to all sub-commands, including the ability to set the desired level of diagnostic output
(the "log level"), and to run the command on a compute node on a cluster computing system.

The :ref:`"run" sub-command <run-label>` also provides many options, including the
ability to select which scenario group to run and limit which scenarios and steps to
run (or not run). Use the help flag (``-h`` or ``--help``) to see all the options:

.. code-block:: sh

   $ gt run -h

You can see the available sub-commands and global command-line arguments by running
this command:

.. code-block:: sh

   $ gt -h

The options to each sub-command can be found by using ``-h`` after the sub-command, e.g.,

.. code-block:: sh

   $ gt diff -h

----------------

We begin Part 1 of the tutorial by creating a project called ``ctax`` using the
templates files provided by ``pygcam``.

1.1 Create the project structure and initial configuration file
----------------------------------------------------------------------
The first step in creating a new product is to run gcamtool
:ref:`new <new-label>` sub-command. To create the project ``ctax``
with the project directory ``/Users/rjp/projects/ctax``, I would
run the following command:

.. code-block:: bash

   gt new -c -r /Users/rjp/projects ctax

This both creates the initial file structure in ``/Users/rjp/projects/ctax``,
and (because I specified the ``-c`` flag) adds a section for ``ctax`` to my
configuration file, which is found in my home directory. In my case, it is
in ``/Users/rjp/projects/.pygcam.cfg``.

When ``gt`` runs, it checks whether this file exists. If the file is not found,
it is created with all available configuration parameters shown in comments (i.e.,
lines starting with '#') explaining their purpose and showing their default values.
To uncomment a line, simply remove the leading '#' character.

Here is the ``.pygcam.cfg`` file (with the long listing of default settings
removed):

.. code-block:: cfg

    [DEFAULT]

    # default config settings are listed here in comments...

    [ctax]
    # Added by "new" sub-command Sun Sep 25 13:47:49 2016
    GCAM.ProjectDir        = %(GCAM.ProjectRoot)s/ctax
    GCAM.ScenarioSetupFile = %(GCAM.ProjectDir)s/etc/scenarios.xml
    GCAM.RewriteSetsFile   = %(GCAM.ProjectDir)s/etc/rewriteSets.xml

The next step is to customize this to our environment.

.. note:: See :doc:`config` for a detail description of the configuration system.

1.2 Customize .pygcam.cfg
----------------------------
Our first task will be to set ``GCAM.DefaultProject`` so we don't have to keep typing
``gt -P ctax``. We add this setting the ``[DEFAULT]`` section

.. code-block:: cfg

   GCAM.DefaultProject = ctax

You can edit the configuration file with any editor capable of working with plain text.
(Word-processors such as Word introduce formatting information into the file which
renders it unusable by ``pygcam``.) You can use the command ``gt config -e`` to
invoke a system-appropriate editor on the configuration file. See the :doc:`config`
page for details.

1.3 Check configuration
----------------------------
We can check that key file and directory pathnames required by ``pycgam`` exist
by running this command:

.. code-block:: bash

    $ gt config -t
    OK: GCAM.SandboxRoot = /Users/rjp/ws
    OK: GCAM.SandboxDir = /Users/rjp/ws/ctax/
    OK: GCAM.ProjectRoot = /Users/rjp/bitbucket
    OK: GCAM.ProjectDir = /tmp/ctax
    OK: GCAM.QueryDir = /tmp/ctax/queries
    OK: GCAM.MI.Dir = /Users/rjp/GCAM/current/input/gcam-data-system/_common/ModelInterface/src
    OK: GCAM.RefWorkspace = /Users/rjp/GCAM/current
    OK: GCAM.TempDir = /tmp
    OK: GCAM.UserTempDir = /Users/rjp/tmp
    OK: GCAM.ProjectXmlFile = /tmp/ctax/etc/project.xml
    OK: GCAM.RefConfigFile = /Users/rjp/GCAM/current/exe/configuration_ref.xml
    OK: GCAM.MI.JarFile = /Users/rjp/GCAM/current/input/gcam-data-system/_common/ModelInterface/src/ModelInterface.jar
    OK: GCAM.RewriteSetsFile = /tmp/ctax/etc/rewriteSets.xml


1.4 Examine default project files
-----------------------------------
The default ``scenarios.xml`` file defines two scenario groups, each with a
baseline and 4 policy scenarios with different levels of C tax. The default
scenario does not exclude unmanaged land from consideration, while the second
scenario excludes 90% of unmanaged land, which is the default in the GCAM
reference scenario.

The :ref:`run <run-label>` sub-command offers several options that list
project elements and display commands that would be run.

To list the scenario groups in the default project:

.. code-block:: bash

    $ gt run -G
    Scenario groups:
      protect-0
      protect-90

List all the scenarios in the default scenario group:

.. code-block:: bash

    $ gt run -L
    Scenarios:
      base-0
      tax-25-0
      tax-10-0
      tax-15-0
      tax-20-0


List all the scenarios in group ``protect-90``:

.. code-block:: bash

    $ gt run -L -g protect-90
    Scenarios:
      base-90
      tax-25-90
      tax-15-90
      tax-10-90
      tax-20-90

List all project steps for the default scenario group of the default project:

.. code-block:: bash

    $ gt run -l
    Steps:
      setup
      prequery
      gcam
      query
      plot
      diff
      plotDiff
      xlsx

1.5 Run "setup" on a single baseline
------------------------------------------

Now we will run just the ``setup`` step the baseline scenario.

The first time we run
setup, it will create a local copy (using symbolic links in some cases, when possible)
of the reference GCAM workspace that is used to create run-time sandbox directories.
This can be useful in a high-performance computing environment if you will be running
numerous scenarios on compute nodes that have access to fast temporary storage, since
each scenario will copy from that location rather than the reference GCAM which may be
on a slower disk.

.. code-block:: bash

    $ gt run -S base-0 -s setup

    rjp@bebop:~ $ gt -P ctax run -s setup -S base-0
    2016-09-25 15:33:03,705 INFO [base-0, 1, setup] @setup -b base-0 -g protect-0 -S base-0 -w /Users/rjp/ws/ctax/base-0 -p 2050 -y 2015-2050
    2016-09-25 15:33:03,713 INFO Setting up GCAM workspace '/Users/rjp/ws/ctax/Workspace' for GCAM 4.3
    2016-09-25 15:33:03,714 WARNING Ignoring unknown files specified in GCAM.WorkspaceFilesToLink: ['libs']
    2016-09-25 15:33:03,714 INFO Copying /Users/rjp/GCAM/current/exe/XMLDBDriver.jar to /Users/rjp/ws/ctax/Workspace/exe/XMLDBDriver.jar
    2016-09-25 15:33:03,716 INFO Copying /Users/rjp/GCAM/current/exe/gcam.exe to /Users/rjp/ws/ctax/Workspace/exe/gcam.exe
    2016-09-25 15:33:03,745 INFO Copying /Users/rjp/GCAM/current/exe/log_conf.xml to /Users/rjp/ws/ctax/Workspace/exe/log_conf.xml
    2016-09-25 15:33:03,746 INFO Setting up sandbox '/Users/rjp/ws/ctax/base-0'
    2016-09-25 15:33:03,747 WARNING Ignoring unknown files specified in GCAM.SandboxFilesToLink: ['libs']
    2016-09-25 15:33:03,747 INFO Copying /Users/rjp/ws/ctax/Workspace/exe/XMLDBDriver.jar to /Users/rjp/ws/ctax/base-0/exe/XMLDBDriver.jar
    2016-09-25 15:33:03,747 INFO Copying /Users/rjp/ws/ctax/Workspace/exe/log_conf.xml to /Users/rjp/ws/ctax/base-0/exe/log_conf.xml
    2016-09-25 15:33:03,765 INFO Generating local-xml for scenario base-0
    2016-09-25 15:33:03,765 INFO No XML files to copy in /tmp/ctax/xmlsrc/base-0/xml
    2016-09-25 15:33:03,766 INFO Copy /Users/rjp/GCAM/current/exe/configuration_ref.xml
          to /Volumes/PlevinSSD/rjp/ws/ctax/Workspace/local-xml/base-0/config.xml
    2016-09-25 15:33:03,861 INFO Delete ScenarioComponent name='protected_land_input_2' for scenario
    2016-09-25 15:33:03,866 INFO Delete ScenarioComponent name='protected_land_input_3' for scenario
    2016-09-25 15:33:03,872 INFO Generating dyn-xml for scenario base-0
    2016-09-25 15:33:03,873 INFO Link static XML files in /Users/rjp/ws/ctax/base-0/local-xml/base-0 to /Users/rjp/ws/ctax/base-0/dyn-xml/base-0
    2016-09-25 15:33:03,873 INFO Link additional static XML files in /Users/rjp/ws/ctax/base-0/local-xml/base-0 to /Users/rjp/ws/ctax/base-0/dyn-xml/base-0


1.6 Run a single baseline
-----------------------------------
Now we'll run all remaining steps for the baseline scenario.
We already ran the ``setup`` step, so we use the ``-k`` flag to
skip it.

.. code-block:: bash

    $ gt run -k setup -S base-0

This runs gcam, runs the defined queries to create CSV files, and generates
a plot.

*In* :doc:`tutorial2`, *we examine and customize plots generated by the project.*
