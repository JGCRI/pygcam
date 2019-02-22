Tutorial, Part 1
=================

1.0 Introduction
-----------------

.. note::
  The first step after :doc:`installing <install>` ``pygcam`` is to run
  the :ref:`gt init <init>` command to initialize your ``pygcam`` configuration
  file. You will need to know where you have GCAM installed, and where you would like
  to put "project" files, which describe your project, and "sandboxes", which are
  where GCAM workspaces are dynamically created.

Command-line basics
^^^^^^^^^^^^^^^^^^^^^^
The command-line interface to ``pygcam`` uses the :doc:`gcamtool` script,
which is installed when you install ``pygcam``. The ``gt`` command itself is just
a wrapper for all the task-specific options, referred to as "sub-commands".

The ``gt`` command itself, and all sub-commands accept a variety of command-line options
(a.k.a. "flags") that consist of either ``-`` or ``+`` followed by a single letter, or
starting with ``--`` (2 dashes) followed by longer names. Most options offer both the
short and long form. For example, you can get help for any command by specifying either
``-h`` or ``--help``. The following two commands are equivalent::

    $ gt init -h

    $ gt init --help

.. note::
  In this tutorial, typed commands are shown preceded by the standard Unix
  ``$`` prompt. You should not type the ``$``, just the command following it!

Either of these will produce this message, describing all available options
and any required arguments::

  usage: gt init [-h] [-c] [-C] [-g GCAMDIR] [--overwrite] [-P DEFAULTPROJECT]
                 [-p PROJECTDIR] [-s SANDBOXDIR]

  optional arguments:
    -h, --help            show this help message and exit
    -c, --create-project  Create the project structure for the given default
                          project. If neither -c/--create-project nor -C/--no-
                          create-project is specified, the user is queried
                          interactively.
    -C, --no-create-project
    -g GCAMDIR, --gcamDir GCAMDIR
                          The directory that is a GCAM v4.3 or v4.4 workspace.
                          Sets config var GCAM.RefWorkspace. By default, looks
                          for gcam-v4.4 (then v4.3) in ~, ~/GCAM, and ~/gcam,
                          where "~" indicates your home directory.
    --overwrite           Overwrite an existing config file. (Makes a backup
                          first in ~/.pygcam.cfg~, but user is required to
                          confirm overwriting the file.)
    -P DEFAULTPROJECT, --defaultProject DEFAULTPROJECT
                          Set the value of config var GCAM.DefaultProject to the
                          given value.
    -p PROJECTDIR, --projectDir PROJECTDIR
                          The directory in which to create pygcam project
                          directories. Sets config var GCAM.ProjectRoot. Default
                          is "~/GCAM/projects".
    -s SANDBOXDIR, --sandboxDir SANDBOXDIR
                          The directory in which to create pygcam project
                          directories. Sets config var GCAM.SandboxRoot. Default
                          is "~/GCAM/sandboxes".


There are many "global" options available to the :doc:`gcamtool` command that apply
to all sub-commands, such as overriding the default project to run on a specific project,
setting the desired level of diagnostic output
(the "log level"), and to run the command on a compute node on a cluster computing system.
These are distinguished by having their short form start with a ``+``, though their long
form retains the ``--`` prefix. (An exception to this rule is the ``-h`` flag, which uses
the ``-`` prefix in all cases.) To see the global options, use the command::

  $ gt -h

Of course, you can also refer to the :doc:`gcamtool` page on this site.

Initialize your configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you haven't done so already, run the :ref:`init <init>` command to
initialize your pygcam configuration file, ``.pygcam.cfg``.

     * On Linux and macOS, the configuration file is found in your home directory,
       i.e., the value of the environment variable ``HOME``.

     * On Windows, the configuration will be stored in the directory identified
       by the first of the following environment variables defined to have a non-empty
       value: ``PYGCAM_HOME``, ``HOMESHARE``, and ``HOMEPATH``. The
       first variable, ``PYGCAM_HOME`` is known only to pygcam, while at least one of
       the other two should be set by Windows.

See :doc:`initialize` for further details.

You can also use the :ref:`config <config>` command to retrieve ``pygcam``'s idea
of your home directory. Here's how it looks on macOS (and similar on Linux/Unix):

.. code-block:: sh

  # List all configuration variables that include the word "home" (case insensitive)
  $ gt config home
  [tutorial]
            $HOME = /Users/rjp
       $JAVA_HOME = /Library/Java/JavaVirtualMachines/jdk1.8.0_74.jdk/Contents/Home
             Home = /Users/rjp

  # Show the value of the configuration variable "Home" (case sensitive)
  $ gt config -x Home
  /Users/rjp

Same as above, but on Windows:

.. code-block:: sh

  $ gt config home
  [tutorial]
      $ANACONDA_HOME = /cygdrive/c/Users/rjp/Anaconda2
           $CYG_HOME = /cygdrive/c/Users/rjp
               $HOME = C:\cygwin64\home\rjp
          $HOMEDRIVE = C:
           $HOMEPATH = \Users\rjp
                Home = C:/Users/rjp

  $ gt config -x Home
  C:/Users/rjp


The "run" sub-command
^^^^^^^^^^^^^^^^^^^^^^
In this tutorial, we focus on the :ref:`run <run>` sub-command, which performs actions defined
in the :doc:`project-xml` file, the location of which is specified by the config parameter
``GCAM.ProjectXmlFile``, which defaults to ``%(GCAM.ProjectDir)s/etc/project.xml``.

The basic GCAM workflow consists of a defining and running a baseline scenario and one
or more policy scenarios, and then comparing the policy cases to the baseline.

  - The :doc:`project-xml` file describes all the workflow steps required to setup, run, and
    analyze the scenarios.

  - The :doc:`scenarios-xml` file defines the required modifications to reference GCAM
    input and configuration XML files required to implement the desired scenarios. The file can
    define multiple "scenario groups", each consisting of a baseline and one or more policy scenarios.

The entire workflow or select steps can be run using the :ref:`run <run>` sub-command.
If no options are specified, as in::

   $ gt run

the default scenario group (identified in :doc:`project-xml`) of the default project
(defined in your configuration file) will
be run, starting with the scenario identified as the baseline, followed by all
policy scenarios. All defined workflow steps will be executed in the order defined,
for all scenarios.

The :ref:`run <run>` sub-command provides many options, including the
ability to select which scenario group to run and limit which scenarios and steps to
run (or not run). Use the help flag (``-h`` or ``--help``) to see all the options:

.. code-block:: sh

   $ gt run -h


We begin Part 1 of the tutorial by examining a minimal project called ``tutorial``.
The project and scenario XML files are installed for you by the :ref:`init <init>`
sub-command.

1.1 The project.xml file
-----------------------------
The following :doc:`project-xml` file is included automatically when you run the
:ref:`init <init>` or :ref:`new <new>` sub-commands.

.. note::
  For complete documentation of all XML file formats, see :doc:`xmlFiles`.

.. literalinclude:: ../../pygcam/etc/examples/project.xml
   :language: xml
   :linenos:

The file above defines steps to run for the "tutorial" project (see line 8).
Each ``<step>`` is given a name which can be specified on the command-line as a step to
run or to skip. All non-skipped steps are run in the order indicated, for all relevant scenarios.

The file starts by defining two project variables (lines 10 and 11) for the ``startYear``
and ``endYear`` of our analysis, and by combining these into a third variable, ``years`` (line 12).
The attribute ``eval="1"`` indicates that the value shown should be evaluated to convert
the variables named in curly-braces to their text values.

Next, the workflow steps are defined. The steps shown, or variations thereof, will be used for
most GCAM projects. Each step has a required ``name`` attribute, which is used to identify
the step on the command-line when you want to run or skip specific steps. The text between
the ``<step>`` and ``</step>`` elements is the command to run for that step, after performing
variable substitution on the text. Commands that start with ``@`` refer to built-in or plug-in
commands, which can be run internally by :doc:`gcamtool`.

The ``runFor`` attribute is optional. If not specified, the step will be run for both baseline
and policy (non-baseline) scenarios. You can indicate ``runFor="baseline"`` to run the step
only for baseline scenarios, or ``runFor="policy"`` to run it only for non-baseline scenarios.
Some steps (e.g., computing differences) make sense only for policy scenarios.
(Baseline scenarios are indicated as such in the ``scenarios.xml`` file, which we will turn to
shortly.)

List defined steps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use the ``-l`` or ``--listSteps`` option to the :ref:`run <run>` sub-command to list the defined
project steps::

    $ gt run --listSteps
    Steps:
      setup
      gcam
      query
      diff
      plotDiff
      xlsx

1.2 The scenarios.xml file
---------------------------
The following :doc:`scenarios-xml` file is also included automatically when you run the
:ref:`init <init>` or :ref:`new <new>` sub-commands. It defines one scenario group
consisting of a baseline and 4 carbon tax policy scenarios:

.. literalinclude:: ../../pygcam/etc/examples/scenarios.xml
   :language: xml
   :linenos:

This scenarios file relies on files distributed with GCAM that define various
levels of carbon taxes::

    $ cd ~/GCAM/gcam-v5.1.1/input/policy
    $ ls carbon*
    carbon_tax_10_5.xml  carbon_tax_15_5.xml  carbon_tax_20_5.xml  carbon_tax_25_5.xml

The baseline defined above modifies nothing in the GCAM reference scenario.
Each of the four policy scenarios differs from this baseline only by
including in the XML configuration file and a file that implements a carbon tax
that starts at $10 or $25 per tonne of fossil and industrial CO\ :sub:`2` in 2020,
and increases by 5% per year.

The two scenarios ``tax-bio-10`` and ``tax-bio-25`` additionally call a built-in
:ref:`setup <setup>` function that also applies the carbon tax to biogenic carbon.

List defined scenario groups and scenarios
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use the ``-G`` (or ``--listGroups``) option to the :ref:`run <run>` sub-command
to list the defined scenario groups, and the ``-L`` (or ``--listScenarios``) option
to list defined scenario names. You can use these individually or together
(with the ``-l``/``--listSteps`` if you wish, too)::

  $ gt run -l -L -G
  Scenario groups:
    group (default)
  Scenarios:
    base
    tax-10
    tax-25
    tax-bio-10
    tax-bio-25
  Steps:
    setup
    gcam
    query
    diff
    plotDiff
    xlsx

We can see all actual step commands as well, without running them, using the
``-n`` or ``--noRun`` option to the :ref:`run <run>` sub-command:

.. code-block:: sh

    $ gt run -n
    INFO pygcam.project: [base, 1, setup] @setup -b base -g group -S base -w /Users/rjp/tmp/tut/sandboxes/tutorial/base -p 2050 -y 2015-2050
    INFO pygcam.project: [base, 2, gcam] @gcam -s base -S ../local-xml
    INFO pygcam.project: [base, 3, query] @query -o /Users/rjp/tmp/tut/sandboxes/tutorial/base/queryResults -w /Users/rjp/tmp/tut/sandboxes/tutorial/base -s base -q "/tmp/tmphIQDum.queries.xml"
    INFO pygcam.project: [tax-bio-10, 4, setup] @setup -b base -s tax-bio-10 -g group -S tax-bio-10 -w /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-10 -p 2050 -y 2015-2050
    INFO pygcam.project: [tax-bio-10, 5, gcam] @gcam -s tax-bio-10 -S ../local-xml
    INFO pygcam.project: [tax-bio-10, 6, query] @query -o /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-10/queryResults -w /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-10 -s tax-bio-10 -q "/tmp/tmpeLs3qD.queries.xml"
    INFO pygcam.project: [tax-bio-10, 7, diff] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/ -y 2015-2050 -q /tmp/tmpeLs3qD.queries.xml base tax-bio-10
    INFO pygcam.project: [tax-bio-10, 8, plotDiff] @chart -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-10/diffs --outputDir figures --years 2015-2050 --label --ygrid --zeroLine --reference base --scenario tax-bio-10 --fromFile /tmp/tmpr0FFMt.project.txt
    INFO pygcam.project: [tax-bio-10, 9, xlsx] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-10/diffs -c -y 2015-2050 -o diffs.xlsx /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-10/diffs/*.csv
    INFO pygcam.project: [tax-10, 4, setup] @setup -b base -s tax-10 -g group -S tax-10 -w /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10 -p 2050 -y 2015-2050
    INFO pygcam.project: [tax-10, 5, gcam] @gcam -s tax-10 -S ../local-xml
    INFO pygcam.project: [tax-10, 6, query] @query -o /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10/queryResults -w /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10 -s tax-10 -q "/tmp/tmpGhBkT2.queries.xml"
    INFO pygcam.project: [tax-10, 7, diff] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/ -y 2015-2050 -q /tmp/tmpGhBkT2.queries.xml base tax-10
    INFO pygcam.project: [tax-10, 8, plotDiff] @chart -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10/diffs --outputDir figures --years 2015-2050 --label --ygrid --zeroLine --reference base --scenario tax-10 --fromFile /tmp/tmp5Thk5Q.project.txt
    INFO pygcam.project: [tax-10, 9, xlsx] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10/diffs -c -y 2015-2050 -o diffs.xlsx /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10/diffs/*.csv
    INFO pygcam.project: [tax-bio-25, 4, setup] @setup -b base -s tax-bio-25 -g group -S tax-bio-25 -w /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-25 -p 2050 -y 2015-2050
    INFO pygcam.project: [tax-bio-25, 5, gcam] @gcam -s tax-bio-25 -S ../local-xml
    INFO pygcam.project: [tax-bio-25, 6, query] @query -o /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-25/queryResults -w /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-25 -s tax-bio-25 -q "/tmp/tmphyJVaz.queries.xml"
    INFO pygcam.project: [tax-bio-25, 7, diff] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/ -y 2015-2050 -q /tmp/tmphyJVaz.queries.xml base tax-bio-25
    INFO pygcam.project: [tax-bio-25, 8, plotDiff] @chart -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-25/diffs --outputDir figures --years 2015-2050 --label --ygrid --zeroLine --reference base --scenario tax-bio-25 --fromFile /tmp/tmpDh5O0u.project.txt
    INFO pygcam.project: [tax-bio-25, 9, xlsx] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-25/diffs -c -y 2015-2050 -o diffs.xlsx /Users/rjp/tmp/tut/sandboxes/tutorial/tax-bio-25/diffs/*.csv
    INFO pygcam.project: [tax-25, 4, setup] @setup -b base -s tax-25 -g group -S tax-25 -w /Users/rjp/tmp/tut/sandboxes/tutorial/tax-25 -p 2050 -y 2015-2050
    INFO pygcam.project: [tax-25, 5, gcam] @gcam -s tax-25 -S ../local-xml
    INFO pygcam.project: [tax-25, 6, query] @query -o /Users/rjp/tmp/tut/sandboxes/tutorial/tax-25/queryResults -w /Users/rjp/tmp/tut/sandboxes/tutorial/tax-25 -s tax-25 -q "/tmp/tmpqP4ZMs.queries.xml"
    INFO pygcam.project: [tax-25, 7, diff] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/ -y 2015-2050 -q /tmp/tmpqP4ZMs.queries.xml base tax-25
    INFO pygcam.project: [tax-25, 8, plotDiff] @chart -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-25/diffs --outputDir figures --years 2015-2050 --label --ygrid --zeroLine --reference base --scenario tax-25 --fromFile /tmp/tmppfe8mK.project.txt
    INFO pygcam.project: [tax-25, 9, xlsx] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-25/diffs -c -y 2015-2050 -o diffs.xlsx /Users/rjp/tmp/tut/sandboxes/tutorial/tax-25/diffs/*.csv

.. note::

   Note that the messages shown above are written using the internal logging facility, at the
   log level ``INFO``. (As indicated on each line.)
   If you set the ``GCAM.LogLevel`` higher than ``INFO`` (i.e., to ``WARNING``, ``ERROR`` or ``FATAL``)
   these messages will be suppressed.

1.3 Selecting and skipping scenarios and steps
-------------------------------------------------

You can select which scenarios and steps to run using the ``-S``
and ``-s`` flags, respective. For example, to run "setup" and
"gcam" steps only for the baseline scenario "base", we would use the
following command::

    $ gt run -S base -s setup,gcam

If we run this with the the ``-n`` option, we can see what would be run::

    $ gt run -S base -s setup -n
    INFO pygcam.project: [base, 1, setup] @setup -b base -g group -S base -w /Users/rjp/tmp/tut/sandboxes/tutorial/base -p 2050 -y 2015-2050
    INFO pygcam.project: [base, 2, gcam] @gcam -s base -S ../local-xml

.. note::

    When listing multiple steps or scenarios, separate
    their names with a "," and do not include spaces.

Sometimes we want to run most of the steps except for a few. Use the
``-K`` and ``-k`` flags to indicate which scenarios or steps, respectively,
to skip. All other defined scenarios and steps will be run.

This command runs all steps other than ``setup`` and ``gcam`` for scenario ``base``::

    $ gt run -S tax-10 -k setup,gcam -n
    INFO pygcam.project: [tax-10, 6, query] @query -o /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10/queryResults -w /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10 -s tax-10 -q "/tmp/tmpVPqhmn.queries.xml"
    INFO pygcam.project: [tax-10, 7, diff] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/ -y 2015-2050 -q /tmp/tmpVPqhmn.queries.xml base tax-10
    INFO pygcam.project: [tax-10, 8, plotDiff] @chart -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10/diffs --outputDir figures --years 2015-2050 --label --ygrid --zeroLine --reference base --scenario tax-10 --fromFile /tmp/tmpD2WMy4.project.txt
    INFO pygcam.project: [tax-10, 9, xlsx] @diff -D /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10/diffs -c -y 2015-2050 -o diffs.xlsx /Users/rjp/tmp/tut/sandboxes/tutorial/tax-10/diffs/*.csv


1.4 Creating additional scenarios
-----------------------------------
We can add more tax scenarios to our file by copying and pasting the
existing one, and changing a few numbers to other values, to also use
the $15 and $20 per tonne files provide. These would look like this:

.. code-block:: xml

    <scenario name="tax-15">
        <add name="carbon_tax">../input/policy/carbon_tax_15_5.xml</add>
    </scenario>

    <scenario name="tax-20">
        <add name="carbon_tax">../input/policy/carbon_tax_20_5.xml</add>
    </scenario>

Copying and pasting isn't a bad approach with our simple scenarios, which merely
add one file each to the reference scenario. If our scenarios were much more
involved, copying and pasting would become troublesome, particularly if we needed
to make changes that affected all the scenarios.

Using iterators
^^^^^^^^^^^^^^^^^^
You can create similar scenarios using "iterators", which define a set of
values to iterate over, with a new scenario (or scenario group) defined for each
value of the iterator.

The following is equivalent to our "cut & paste" example above:

.. literalinclude:: ../../pygcam/etc/examples/scenarios-iterator.xml
   :language: xml
   :linenos:

The example above defines an iterator named "tax", with values 10, 15, 20, and 25.
The scenario group includes the same baseline as before, but now there are just two
``<scenario>`` definitions, one for fossil carbon and one for fossil and biogenic
carbon. The term ``{tax}`` is replaced by each value of the iterator in turn,
defining a new scenario, and indicating which file to include in the ``<add>``
element. Thus, by iterating over the tax levels, we have created 9 scenarios: one
baseline and 8 policy scenarios.

The file shown above is included in your project's ``etc`` directory by the
:ref:`init <init>` and :ref:`new <new>` sub-commands, as ``scenarios-iterator.xml``.
You can cause :doc:`gcamtool` to use this alternate scenarios either by renaming it
to ``scenarios.xml`` (saving the old file, if you wish) or by editing your config
file to include the following:

.. code-block:: cfg

    GCAM.ScenarioSetupFile  = %(GCAM.ProjectDir)s/etc/scenarios-iterator.xml

You can include this in the ``[DEFAULT]`` section, but then it would apply to
all projects. Better to include it in the ``[tutorial]`` projects's section only.

Editing .pygcam.cfg
^^^^^^^^^^^^^^^^^^^^
In the next step, we will edit the configuration file. You can use any editor
capable of working with plain text. (Word-processors such as Word introduce
formatting information into the file which renders it unusable by ``pygcam``.)
On Linux, you might try the simple ``nano`` editor, or the more powerful
(and complicated) ``vim`` or ``emacs`` editors popular with programmers.

On Windows, a good option is the free `Notepad++ <https://notepad-plus-plus.org>`_.
On the Mac, you can use TextEdit.app to edit plain text files.

You can use the command ``gt config -e`` to invoke a system-appropriate editor on
the configuration file. On macOS and Windows, this command defaults to opening
the config file with TextEdit.app (macOS) and NotePad++ (Windows). See the
:doc:`config` page for firther details.

Checking iterator results
^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you set the configuration file variable ``GCAM.ScenarioSetupOutputFile`` to
the pathname of a file, the :ref:`run <run>` sub-command will write the
"expanded" scenario definitions to this file each time it runs. For example:

.. code-block:: cfg

    GCAM.ScenarioSetupOutputFile = %(Home)s/scenariosExpanded.xml

Results in the following:

.. code-block:: sh

    # Set the logLevel high to suppress output, and use -n to avoid running
    # actual commands. This has the side-effect of generating the XML file.
    $ gt --logLevel=ERROR run -n
    $ cat ~/scenariosExpanded.xml
    <setup>
       <scenarioGroup name="group" useGroupDir="0" srcGroupDir="">
          <scenario name="base" baseline="1">
          </scenario>
          <scenario name="tax-10" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_10_5.xml</add>
          </scenario>
          <scenario name="tax-15" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_10_5.xml</add>
          </scenario>
          <scenario name="tax-20" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_10_5.xml</add>
          </scenario>
          <scenario name="tax-25" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_10_5.xml</add>
          </scenario>
          <scenario name="tax-bio-10" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_10_5.xml</add>
             <function name='taxBioCarbon' dynamic='False'>None</function>
          </scenario>
          <scenario name="tax-bio-15" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_10_5.xml</add>
             <function name='taxBioCarbon' dynamic='False'>None</function>
          </scenario>
          <scenario name="tax-bio-20" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_10_5.xml</add>
             <function name='taxBioCarbon' dynamic='False'>None</function>
          </scenario>
          <scenario name="tax-bio-25" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_10_5.xml</add>
             <function name='taxBioCarbon' dynamic='False'>None</function>
          </scenario>
       </scenarioGroup>
    </setup>

In :doc:`tutorial2`, we begin to use :doc:`gcamtool` to run GCAM and analyze
results.
