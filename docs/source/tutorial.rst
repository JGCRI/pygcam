Tutorial
=========

We begin by creating a project called ``ctax`` using the templates files
provided by ``pygcam``. Subsequently we will customize these templates to
develop an alternative project.

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

----------------

1. Create the project structure and initial configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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

2. Customize .pygcam.cfg
^^^^^^^^^^^^^^^^^^^^^^^^^
Our first task will be to set ``GCAM.DefaultProject`` so we don't have to keep typing
``gt -P ctax``. We add this setting the ``[DEFAULT]`` section

 .. code-block:: cfg

    GCAM.DefaultProject = ctax

You can edit the configuration file with any editor capable of working with plain text.
(Word-processors such as Word introduce formatting information into the file which
renders it unusable by ``pygcam``.) You can use the command ``gt config -e`` to
invoke a system-appropriate editor on the configuration file. See the :doc:`config`
page for details.

3. Check configuration
^^^^^^^^^^^^^^^^^^^^^^^^
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


4. Examine default project files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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

5. Run "setup" on a single baseline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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


6. Run a single baseline
^^^^^^^^^^^^^^^^^^^^^^^^^^
Now we'll run all remaining steps for the baseline scenario.
We already ran the ``setup`` step, so we use the ``-k`` flag to
skip it.

 .. code-block:: bash

    $ gt run -k setup -S base-0

This runs gcam, runs the defined queries to create CSV files, and generates
a plot.

7. Examine output files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We can check where the output files are going by querying the configuration
system. The ``config`` sub-command takes uses the given argument as a
regular expression to match a portion of any config variable name. It's
case-insensitive by default. So you can find out where the sandbox dir is
by running

 .. code-block:: bash

    $ gt run config sand

    [ctax]
    GCAM.SandboxDir = /Users/rjp/ws/paper1/
    GCAM.SandboxFilesToLink = input libs exe/gcam.exe
    GCAM.SandboxProjectDir = /Users/rjp/ws/paper1
    GCAM.SandboxRefWorkspace = /Users/rjp/ws/paper1/Workspace
    GCAM.SandboxRoot = /Users/rjp/ws

We could be more specific and get just the one result:

 .. code-block:: bash

    $ gt run config sandboxdir

    [ctax]
              GCAM.SandboxDir = /Users/rjp/ws/paper1/

Finally, if we want to use the result in a script or in command, we can
get a "clean" copy of the value by using the ``-x`` flag. In this case,
the value is used verbatim, and it is case-sensitive. Here we use the
value directly in an ``cd`` command.

 .. code-block:: bash

    $ cd `gt config GCAM.SandboxDir -x`
    $ ls -l
    total 0
    drwxrwx---  5 rjp  staff  272 Sep 25 15:37 Workspace/
    drwxrwx---  5 rjp  staff  306 Sep 25 15:47 base-0/

    $ cd base-0
    $ ls -l
    total 32
    lrwxrwxr-x  1 rjp  staff   36 Sep 25 15:37 dyn-xml@ -> /Users/rjp/ws/ctax/Workspace/dyn-xml
    drwxrwx---  3 rjp  staff  272 Sep 25 15:56 exe/
    lrwxrwxr-x  1 rjp  staff   34 Sep 25 15:37 input@ -> /Users/rjp/ws/ctax/Workspace/input
    lrwxrwxr-x  1 rjp  staff   33 Sep 25 15:37 libs@ -> /Users/rjp/ws/ctax/Workspace/libs
    lrwxrwxr-x  1 rjp  staff   38 Sep 25 15:37 local-xml@ -> /Users/rjp/ws/ctax/Workspace/local-xml
    drwxrwx---  3 rjp  staff  408 Sep 25 15:58 output/
    drwxrwx---  4 rjp  staff  306 Sep 25 15:58 queryResults/

The CSV files are in the ``queryResults`` directory, and generated plots are in the ``figures``
directory within. The ``queries`` directory holds the queries that were extracted from the
``Main_queries.xml`` file to run them in ModelInterface in batch model.

 .. code-block:: bash

    $ cd queryResults/
    $ ls -lR
    total 160
    -rw-rw-r--  1 rjp  staff    447 Sep 25 15:58 Climate_forcing-base-0.csv
    -rw-rw-r--  1 rjp  staff    468 Sep 25 15:58 Global_mean_temperature-base-0.csv
    -rw-rw-r--  1 rjp  staff  20849 Sep 25 15:58 Land_Allocation-base-0.csv
    -rw-rw-r--  1 rjp  staff  38000 Sep 25 15:58 Refined-liquids-production-by-technology-base-0.csv
    drwxr-xr-x  2 rjp  staff    102 Sep 25 15:58 figures/
    -rw-rw-r--  1 rjp  staff   7389 Sep 25 15:58 mi.log
    drwxrwx---  2 rjp  staff    238 Sep 25 15:47 queries/

    ./figures:
    total 80
    -rw-rw-r--  1 rjp  staff  38399 Sep 25 15:58 Refined-liquids-production-by-technology-base-0.png

    ./queries:
    total 112
    -rw-rw-r--  1 rjp  staff   1459 Sep 25 15:49 Climate_forcing.xml
    -rw-rw-r--  1 rjp  staff   1495 Sep 25 15:49 Global_mean_temperature.xml
    -rw-rw-r--  1 rjp  staff  38788 Sep 25 15:49 Land_Allocation.xml
    -rw-rw-r--  1 rjp  staff   2773 Sep 25 15:49 Refined-liquids-production-by-technology.xml
    -rw-rw-r--  1 rjp  staff   2970 Sep 25 15:49 generated-batch-query.xml

Here's the generated figure:

  .. image:: images/Refined-liquids-production-by-technology-base-0.png

8. Run policy cases for default scenario group
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Now we run the policy cases, i.e., everything but the
baseline. Similar to the ``-k`` flag, which skips steps,
we can use the ``-K`` flag to skip scenarios. Since we
already ran ``base-0``, we'll skip it and run all the
policy scenarios.

 .. code-block:: bash

    $ gt run -K base-0

Or, if we prefer, we can run just one policy scenario:

 .. code-block:: bash

    $ gt run -S tax-10-0

9. Examine policy case results
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Policy cases produce more results than do baselines since they also
compute and plot differences from the baseline. The ``queryResults``
directory looks similar to that for the baseline scenario, but there
is now also a ``diffs`` directory:

 .. code-block:: bash

    $ cd ../../tax-10-0/
    $ ls
    diffs/        dyn-xml@      exe/          input@        local-xml@    output/       queryResults/

    $ cd diffs
    $ ls
    Climate_forcing-tax-10-0-base-0.csv                           diffs.xlsx
    Global_mean_temperature-tax-10-0-base-0.csv                   figures/
    Land_Allocation-tax-10-0-base-0.csv                           tax-10-0-annual.xlsx
    Refined-liquids-production-by-technology-tax-10-0-base-0.csv

    $ ls -lR
    total 416
    -rw-rw-r--  1 rjp  staff     273 Sep 22 18:57 Climate_forcing-tax-10-0-base-0.csv
    -rw-rw-r--  1 rjp  staff     299 Sep 22 18:57 Global_mean_temperature-tax-10-0-base-0.csv
    -rw-rw-r--  1 rjp  staff    8221 Sep 22 18:57 Land_Allocation-tax-10-0-base-0.csv
    -rw-rw-r--  1 rjp  staff   22360 Sep 22 18:57 Refined-liquids-production-by-technology-tax-10-0-base-0.csv
    -rw-rw-r--  1 rjp  staff   39411 Sep 22 15:32 diffs.xlsx
    drwxr-xr-x  2 rjp  staff     272 Sep 22 18:22 figures/
    -rw-rw-r--  1 rjp  staff  123476 Sep 22 15:32 tax-10-0-annual.xlsx

    ./figures:
    total 400
    -rw-rw-r--  1 rjp  staff  30029 Sep 22 18:57 Climate_forcing-tax-10-0-base-0.png
    -rw-rw-r--  1 rjp  staff  30280 Sep 22 18:57 Global_mean_temperature-tax-10-0-base-0.png
    -rw-rw-r--  1 rjp  staff  59195 Sep 22 18:57 Land_Allocation-tax-10-0-base-0-by-region-2050.png
    -rw-rw-r--  1 rjp  staff  35138 Sep 22 18:57 Refined-liquids-production-by-technology-tax-10-0-base-0-USA.png
    -rw-rw-r--  1 rjp  staff  37023 Sep 22 18:57 Refined-liquids-production-by-technology-tax-10-0-base-0.png

Notice that there's are also two XLSX files generated: ``diffs.xlsx`` and ``tax-10-0-annual.xlsx``.
Each an Excel workbook with all query differences results, one query per worksheet, with an index
with links on the first worksheet. The difference is that the file ``tax-10-0-annual.xlsx`` shows
values interpolated between time-step years, whereas ``diffs.xlsx`` is just the difference from the
queries as produced by GCAM.

Here are the generated figures for the differences from the baseline:


  .. image:: images/Refined-liquids-production-by-technology-base-0.png

---------

  .. image:: images/Climate_forcing-tax-10-0-base-0.png

---------

  .. image:: images/Global_mean_temperature-tax-10-0-base-0.png

---------

  .. image:: images/Land_Allocation-tax-10-0-base-0-by-region-2050.png

---------

  .. image:: images/Refined-liquids-production-by-technology-tax-10-0-base-0-USA.png

---------

  .. image:: images/Refined-liquids-production-by-technology-tax-10-0-base-0.png

---------

10. Modify plot appearance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The ``chart`` sub-command offers numerous options to control the appearance
of figures.

 .. note::
    See :doc:`project-xml` for a detailed description of the elements
    of ``project.xml`` files.

Open the file ``project.xml``, found in the ``etc`` directory within the
project directory for the ``ctax`` project. Observe the following:

  - There are 2 "steps" that generate plots, one that generates plots
    for a single baseline or policy scenario (line 32), and another that plots
    differences between a policy scenario and the baseline (line 36), based on
    the files generated by the "diff" step (line 35).

  - The command-line arguments for the scenario plots commands are organized in
    two areas. Line 58 defines a variable called ``scenPlotArgs``, which holds
    arguments common to all scenario plots, for convenience. The arguments there are:

    .. code-block:: bash

       -D {batchDir} --outputDir figures --years {years} --label --labelColor black --box


    - ``-D {batchDir}`` indicates the directory in which files are found. The value
      ``{batchDir}`` is filled in at run-time, since it differs for each scenario.
    - ``--outputDir figures`` indicates that plots should be written in the directory
      ``figures``, relative to the directory specified with ``-D``.
    - ``--years {years}`` says to plot results for this range of years. The value for
      ``{years}`` is defined at line 11. This is defined in a variable to allow the
      range to be changed consistently for all plots by changing either the start or
      end years, defined at lines 9 and 10, which in turn form the value for ``years``
    - ``--label`` requests that a label be rendered down the right side of the figure
      with the name of the file.
    - ``--labelColor black`` requests that the label on the right side should be black.
    - ``--box`` draws a box around the plot.

  - There is only one scenario plot defined, at line 63, which plots the data in the file
    ``Refined-liquids-production-by-technology-{scenario}.csv``, where ``{scenario}``
    is replaced by the current scenario being evaluated. CSV files generated by
    queries are named by the query name (with spaces replaced by hyphens)
    followed by the scenario name, and with a preceding hyphen. The remainder of line
    provides arguments specific to that plot:

    .. code-block:: bash

       -Y EJ -I technology -i -T 'Refined liquid fuels production' -c region -n 4

    - ``-Y EJ`` sets the y-axis label to "EJ"
    - ``-i`` indicates that the data should be annually interpolated
    - ``-T 'Refined liquid fuels production'`` sets the plot title
    - ``-c region`` specifies that the "region" column in the data file should be
      presented as the segments in the stacked bar chart and in the legend.
    - ``-n 4`` indicates that the legend should be presented in 4 columns.

We will now modify the plot slightly. We'll start by copying row  Let's make the label
light grey, rather than black, and we'll remove the box around the plot. Remove the ``--box``
argument and change ``black`` to ``grey``. Let's also add a new argument, ``-O`` (letter O,
not zero) which causes the plot to be opened after it is created. This works on Macs and Windows
computers, and may work on Linux depending how your window system is configured. Otherwise,
navigate in a file browser to the directory ``ctax/base-0/queryResults/figures`` in the
run-time directory for the project, which you can recover by running:

 .. code-block:: bash

    gt config sandboxroot

We'll also change the number of columns in the legend by changing ``-n 3`` on line 62 to ``-n 4``,
and remove the interpolated annual values to plot only the 5-year time-steps. Just remove ``-i``
on line 62.

To see the modified plot, rerun the "plot" step for the ``base-0`` scenario:

 .. code-block:: bash

    gt run -s plot -S base-0

It should look like this:

 .. image:: images/Refined-liquids-production-by-technology-base-0-mod.png


Finally, let's present the information as an "unstacked" barchart format,
split out by one region, rest-of-world, and total. Let's also add a suffix
to the generated filename that distinguishes it from the original figure,
and also generates PDF rather than PNG format. To do this, add this line
after line 62 (note that the line is split here for legibility):

 .. code-block:: bash

    <text>Refined-liquids-production-by-technology-{scenario}.csv -x unstacked.pdf \
    -u technology -U China -Y EJ -T 'Refined liquid fuels production' -n 3</text>


The new arguments are these:

  - ``-x unstacked.pdf`` Results in the filename
    ``Refined-liquids-production-by-technology-base-0-unstacked.pdf``
  - ``-u technology`` indicates to generate an unstacked bargraph using
    the values in the "technology" column of the query results. Note
    that the time-step values are summed over the entire time horizon.
  - ``-U China`` says to split out China from the rest of the world.

The result should look like this:

 .. image:: images/Refined-liquids-production-by-technology-base-0-unstacked.png


 .. note:: Run the command ``gt chart -h`` to list the options available
    to affect plot generation.

11. Run second scenario group
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We would like to run the other scenario group, but
we've forgotten its name. We use the ``-G`` flag to
list scenario groups:

 .. code-block:: bash

    $ gt run -G
    Scenario groups:
      protect-0
      protect-90

Before running the commands, let's examine the steps that would run, using
the ``-n`` flag:

 .. code-block:: bash

    $ gt run -g protect-90 -n

This results in a fairly long list of commands which don't display nicely here
so we won't attempt to show them.

Now we run all steps of all scenarios in group ``protect-90`` with this command:

 .. code-block:: bash

    $ gt run -g protect-90


12. Run an entire project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We have been running scenarios and scenario groups individually
until now, but we can also run the entire project with a single short
command:

 .. code-block:: bash

    $ gt run -a

Without the ``-a`` flag, all steps for all scenarios in the default
scenario group would be run.


13. Run on a computing cluster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We can batch the job on SLURM by adding a single command-line option.

 .. code-block:: bash

    $ gt -b run

We can set the default time limit in our configuration file, or we can
set it on the command-line.

The ``-B`` flag displays what would occur if we ran in batch mode. The command
(minus the batch-related arguments) is written as a script to a temporary file,
which is then queued using the ``sbatch`` command. The script deletes itself.

 .. code-block:: bash

    $ gt -b -m 60 -j job1 -B run

    2016-09-25 15:16:51,666 INFO Creating batch script '/people/plev920/tmp/tmprpRPq7.pygcam.sh'

    sbatch -p short,slurm --nodes=1 -J job1 -t 01:00:00 --get-user-env=10L -s -A GCAM -n 3 \
    -o /people/plev920/ws/paper1/log/gt-%j.out -e /people/plev920/ws/paper1/log/gt-%j.out \
    /people/plev920/tmp/tmprpRPq7.pygcam.sh

    Script file '/people/plev920/tmp/tmprpRPq7.pygcam.sh':

    #!/bin/bash
    rm -f /people/plev920/tmp/tmprpRPq7.pygcam.sh
    $ gt -m 60 -j job1 run


.. _sample-config-label:

Sample configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Below is a sample configuration file for a project called ``Paper1``. By convention,
variables are named with a prefix identifying where they are defined. All variables
defined by ``pygcam`` begin with ``GCAM.``, so if you create your own variables (e.g.,
to define values used in defining other variables) you should avoid confusion by avoiding
this prefix. You can use any prefix desired, or none at all.

 .. code-block:: cfg

    [DEFAULT]
    GCAM.DefaultProject = paper1
    GCAM.Version        = 4.3

    GCAM.ProjectRoot    = %(Home)s/GCAM/projects
    GCAM.SandboxRoot    = %(Home)s/GCAM/sandboxes

    GCAM.LogLevel       = INFO
    GCAM.MI.LogFile     = %(Home)s/tmp/mi.log
    GCAM.MI.Dir         = /pic/projects/GCAM/ModelInterface

    GCAM.OtherBatchArgs = -A my_account

    GCAM.TextEditor     = open -a emacs

    # Setup config files to not write extraneous files, so of which are very large
    GCAM.WriteDebugFile     = False
    GCAM.WritePrices        = False
    GCAM.WriteXmlOutputFile = False
    GCAM.WriteOutputCsv     = False

    [ctax]
    GCAM.RewriteSetsFile	= %(GCAM.ProjectDir)s/etc/rewriteSets.xml
    GCAM.ScenarioSetupFile	= %(GCAM.ProjectDir)s/etc/scenarios.xml
    GCAM.LogLevel           = DEBUG

------------------------------------------------

Customizing project steps
---------------------------
The generic workflow steps defined in the :doc:`project-xml` file may suffice for
many projects. It is likely, however, that you will want to customize several other
elements of the project file.

Queries
^^^^^^^
The queries identified in the project file (or in an external file) determine which
results are extracted from the GCAM database for each run of the model, and thus
determine which subsequent steps (computing differences, creating charts) can be
performed. To plot results, you must first extract them from the database using
a query.

Queries can be extracted on-the-fly from files used with ModelInterface by specifying
the location of the XML file in the configuration variable ``GCAM.QueryPath`` and
referencing the desired query by its defined "title". (See the
:ref:`query sub-command <query-label>` and the :doc:`pygcam.query` API documentation
for more information.)

Rewrite sets
^^^^^^^^^^^^^
Standard GCAM XML queries can define "rewrites" which modify the values of chosen
data elements to allow them to be aggregated. For example, you can aggregate all
values of CornAEZ01, CornAEZ02, ..., CornAEZ18 to be returned simply as "Corn".

In ``pygcam`` this idea is taken a step further by allowing you to define reusable,
named "rewrite sets" that can be applied on-the-fly to
queries named in the project file. For example, if you are working with a particular
regional aggregation, you can define this aggregation once in a ``rewrites.xml`` file
and reference the name of the rewrite set when specifying queries in :doc:`project-xml`.
See :doc:`rewrite sets <rewrites-xml>` for more information.
