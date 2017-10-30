Tutorial, Part 1
=================

1.0 Introduction
-----------------
The command-line interface to ``pygcam`` uses the :doc:`gcamtool` script,
which is installed when you install ``pygcam``. In this tutorial, we focus on the
:ref:`run <run>`
sub-command, which performs actions defined in the :doc:`project-xml` file, the location
of which is specified by the config parameter ``GCAM.ProjectXmlFile``, which defaults to
``%(GCAM.ProjectDir)s/etc/project.xml``.

The basic GCAM workflow consists of a defining and running a baseline scenario and one
or more policy scenarios, and then comparing the policy cases to the baseline.

  - The :doc:`project-xml` file describes all the workflow steps required to setup, run, and
    analyze the scenarios.

  - The :doc:`scenarios-xml` file defines the required modification to reference GCAM input
    XML files required to implement the desired scenarios.

The entire workflow or select steps can be run using the :ref:`run <run>` sub-command.

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

The :ref:`"run" sub-command <run>` also provides many options, including the
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

We begin Part 1 of the tutorial by examining a minimal project called ``tutorial``.

1.1 Minimal example project
-----------------------------
The following is an example ``project.xml`` file that doesn't do anything other than
allow us to explore some of the features of the ref:`"run" sub-command <run>`

.. code-block:: xml
   :linenos:

    <?xml version="1.0" encoding="UTF-8"?>
    <projects>
        <project name="tutorial">
            <steps>
                <step name="step1" runFor="baseline">echo "step 1(baseline)"</step>
                <step name="step2" runFor="baseline">echo "step 2 (baseline)"</step>
                <step name="step3" runFor="policy">echo "step 3 (policy)"</step>
                <step name="step4" runFor="policy">echo "step 4 (policy)"</step>
                <step name="step5" runFor="all">echo "step 5 (all)"</step>
                <step name="step6" runFor="all">echo "step 6 (all)"</step>
            </steps>
            <scenariosFile name="scenarios.xml"/>
        </project>
    </projects>

The file above defines steps for a projected name "tutorial" (see line 3). Each ``<step>``
is given a name which can be specified on the command-line as a step to run or to skip.
All non-skipped steps are run in the order indicated, for all relevant scenarios.

Note lines 5 and 6 indicate ``runFor="baseline"``. As this suggests, these steps are run
only for baseline scenarios. (Baseline scenarios are indicated as such in the ``scenarios.xml``
file, which we will turn to shortly.)

Similarly, lines 7 and 8 are run only for "policy" (i.e., non-baseline) scenarios. Finally, lines
9 and 10 are run for all scenarios, baseline and non-baseline.

1.2 Minimal scenarios file
---------------------------
The GCAM 4.3 distribution includes files that define various
levels of carbon taxes:

.. code-block:: sh

    rjp@bebop:~/GCAM/gcam-4.3/input/policy $ ls -l carbon*
    -rw-rw-r--  1 rjp  staff  5462 Oct 10  2016 carbon_tax_10_5.xml
    -rw-rw-r--  1 rjp  staff  5463 Oct 10  2016 carbon_tax_15_5.xml
    -rw-rw-r--  1 rjp  staff  5463 Oct 10  2016 carbon_tax_20_5.xml
    -rw-rw-r--  1 rjp  staff  4123 Oct 10  2016 carbon_tax_25_5.xml

We will use these files in our example.

The following ``scenarios.xml`` file defines a baseline that modifies nothing in
the GCAM reference scenario, and a single scenario implementing a $25 per
tonne carbon tax.

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <scenarios name="tutorial" defaultGroup="tax">
       <scenarioGroup name="tax">
          <scenario name="base" baseline="1"/>
          <scenario name="tax-25">
             <add name='carbon_tax'>../input/policy/carbon_tax_25_5.xml</add>
          </scenario>
       </scenarioGroup>
    </scenarios>

The file defines a single "scenario group" named "tax", containing two scenarios,
one called "base", which is the baseline, and another called "tax-25", which is a
policy scenario.

We can see all steps from ``project.xml`` that would be run using the command:

.. code-block:: sh

    $ gt +P tutorial run -n
    2016-10-04 11:32:14,197 INFO [base, 1, step1] echo "step 1 (baseline)"
    2016-10-04 11:32:14,198 INFO [base, 2, step2] echo "step 2 (baseline)"
    2016-10-04 11:32:14,198 INFO [base, 5, step5] echo "step 5 (all)"
    2016-10-04 11:32:14,198 INFO [base, 6, step6] echo "step 6 (all)"
    2016-10-04 11:32:14,199 INFO [tax-25, 3, step3] echo "step 3 (policy)"
    2016-10-04 11:32:14,199 INFO [tax-25, 4, step4] echo "step 4 (policy)"
    2016-10-04 11:32:14,199 INFO [tax-25, 5, step5] echo "step 5 (all)"
    2016-10-04 11:32:14,199 INFO [tax-25, 6, step6] echo "step 6 (all)"

The ``-n`` argument to the ``run`` sub-command says "show me the commands, but
don't run them."

To run them, we use the same command without the ``-n``:

.. code-block:: sh

    $ gt +P tutorial run
    2016-10-04 11:27:08,649 INFO [base, 1, step1] echo "step 1 (baseline)"
    step 1(baseline)
    2016-10-04 11:27:08,653 INFO [base, 2, step2] echo "step 2 (baseline)"
    step 2 (baseline)
    2016-10-04 11:27:08,658 INFO [base, 5, step5] echo "step 5 (all)"
    step 5 (all)
    2016-10-04 11:27:08,662 INFO [base, 6, step6] echo "step 6 (all)"
    step 6 (all)
    2016-10-04 11:27:08,667 INFO [tax-25, 3, step3] echo "step 3 (policy)"
    step 3 (policy)
    2016-10-04 11:27:08,671 INFO [tax-25, 4, step4] echo "step 4 (policy)"
    step 4 (policy)
    2016-10-04 11:27:08,675 INFO [tax-25, 5, step5] echo "step 5 (all)"
    step 5 (all)
    2016-10-04 11:27:08,680 INFO [tax-25, 6, step6] echo "step 6 (all)"
    step 6 (all)

1.3 Introspection commands
-----------------------------------
You can use ``-G``, ``-L`` and ``-l`` arguments to the "run" subcommand to list
defined scenario groups, scenarios, and steps, respectively. These can be specified
together or separately:

.. code-block:: sh

    $ gt +P tutorial run -G
    Scenario groups:
      tax
    $ gt +P tutorial run -L
    Scenarios:
      base
      tax-25
    $ gt +P tutorial run -l
    Steps:
      step1
      step2
      step3
      step4
      step5
      step6
    $ gt +P tutorial run -l -L -G
    $ gt +P tutorial run -G
    Scenario groups:
      tax
    Scenarios:
      base
      tax-25
    Steps:
      step1
      step2
      step3
      step4
      step5
      step6

Note that if we had multiple scenario groups defined, we could specify one
using the ``-g`` flag, in which case the scenarios listed by ``-L`` would be
those for the designated group.


1.5 Selecting and skipping scenarios and steps
-------------------------------------------------

You can select which scenarios and steps to run using the ``-S``
and ``-s`` flags, respective. For example, to run "step1" and "step2"
for the baseline scenario "base", we would use this command:

.. code-block:: bash

    $ gt run -S base -s step1,step2
    rjp@bebop:~ $ gt +P ctax run -s setup -S base-0
    2016-10-04 12:03:13,746 INFO [base, 1, step1] echo "step 1 (baseline)"
    step 1 (baseline)
    2016-10-04 12:03:13,750 INFO [base, 2, step2] echo "step 2 (baseline)"
    step 2 (baseline)

Note that when listing multiple steps or scenarios, you must separate
their names with a "," and you must not include spaces.

Sometimes we want to run most of the steps except for a few. Use the
``-K`` and ``-k`` flags to indicate which scenarios or steps, respectively,
to skip. All other defined scenarios and steps will be run.

This command runs all scenarios other than "base":

.. code-block:: bash

    $ gt +P tutorial run -K base
    2016-10-04 12:06:08,430 INFO [tax-25, 3, step3] echo "step 3 (policy)"
    step 3 (policy)
    2016-10-04 12:06:08,434 INFO [tax-25, 4, step4] echo "step 4 (policy)"
    step 4 (policy)
    2016-10-04 12:06:08,438 INFO [tax-25, 5, step5] echo "step 5 (all)"
    step 5 (all)
    2016-10-04 12:06:08,442 INFO [tax-25, 6, step6] echo "step 6 (all)"
    step 6 (all)

This command runs all scenarios other than "base", and all steps other than
steps 3 and 5:

.. code-block:: bash

    $ gt +P tutorial run -K base -k step3,step5
    2016-10-04 12:06:44,010 INFO [tax-25, 4, step4] echo "step 4 (policy)"
    step 4 (policy)
    2016-10-04 12:06:44,014 INFO [tax-25, 6, step6] echo "step 6 (all)"
    step 6 (all)

1.4 Creating additional scenarios
-----------------------------------
We can add more tax scenarios to our file by copying and pasting the
existing one, and changing a few instances of "25" to other values,
producing the following:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <scenarios name="tutorial" defaultGroup="tax">

        <scenarioGroup name="tax">
            <scenario name="base" baseline="1"/>

            <scenario name="tax-10">
                <add name="carbon_tax">../input/policy/carbon_tax_10_5.xml</add>
            </scenario>

            <scenario name="tax-15">
                <add name="carbon_tax">../input/policy/carbon_tax_15_5.xml</add>
            </scenario>

            <scenario name="tax-20">
                <add name="carbon_tax">../input/policy/carbon_tax_20_5.xml</add>
            </scenario>

            <scenario name="tax-25">
                <add name="carbon_tax">../input/policy/carbon_tax_25_5.xml</add>
            </scenario>
        </scenarioGroup>
    </scenarios>

We can see the additional scenarios using the ``-L`` flag, and see what would be
run using the ``-n`` flag:

.. code-block:: sh

    $ gt +P tutorial run -L
    Scenarios:
      base
      tax-10
      tax-15
      tax-20
      tax-25
    $ gt +P tutorial run -n
    2016-10-04 12:11:22,926 INFO [base, 1, step1] echo "step 1 (baseline)"
    2016-10-04 12:11:22,927 INFO [base, 2, step2] echo "step 2 (baseline)"
    2016-10-04 12:11:22,927 INFO [base, 5, step5] echo "step 5 (all)"
    2016-10-04 12:11:22,927 INFO [base, 6, step6] echo "step 6 (all)"
    2016-10-04 12:11:22,927 INFO [tax-15, 3, step3] echo "step 3 (policy)"
    2016-10-04 12:11:22,927 INFO [tax-15, 4, step4] echo "step 4 (policy)"
    2016-10-04 12:11:22,928 INFO [tax-15, 5, step5] echo "step 5 (all)"
    2016-10-04 12:11:22,928 INFO [tax-15, 6, step6] echo "step 6 (all)"
    2016-10-04 12:11:22,928 INFO [tax-20, 3, step3] echo "step 3 (policy)"
    2016-10-04 12:11:22,928 INFO [tax-20, 4, step4] echo "step 4 (policy)"
    2016-10-04 12:11:22,928 INFO [tax-20, 5, step5] echo "step 5 (all)"
    2016-10-04 12:11:22,929 INFO [tax-20, 6, step6] echo "step 6 (all)"
    2016-10-04 12:11:22,929 INFO [tax-10, 3, step3] echo "step 3 (policy)"
    2016-10-04 12:11:22,929 INFO [tax-10, 4, step4] echo "step 4 (policy)"
    2016-10-04 12:11:22,929 INFO [tax-10, 5, step5] echo "step 5 (all)"
    2016-10-04 12:11:22,929 INFO [tax-10, 6, step6] echo "step 6 (all)"
    2016-10-04 12:11:22,930 INFO [tax-25, 3, step3] echo "step 3 (policy)"
    2016-10-04 12:11:22,930 INFO [tax-25, 4, step4] echo "step 4 (policy)"
    2016-10-04 12:11:22,930 INFO [tax-25, 5, step5] echo "step 5 (all)"
    2016-10-04 12:11:22,930 INFO [tax-25, 6, step6] echo "step 6 (all)"

1.5 Using iterators
---------------------
Copying and pasting isn't a bad approach with our simple scenarios, which merely
add one file each to the reference scenario. If our scenarios were much more
involved, copying and pasting would become troublesome, particularly if we needed
to make changes that affected all the scenarios.

You can instead define similar scenarios using "iterators", which define a set of
values to iterate over, with a new scenario (or scenario group) defined for each
value of the iterator.

The following is equivalent to our "cut & paste" example above:

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <scenarios name="tutorial" defaultGroup="tax">

        <!-- Our policy scenarios will use these levels of carbon taxes -->
        <iterator name="tax" values="10,15,20,25"/>

        <scenarioGroup name="tax">
            <scenario name="base" baseline="1"/>

            <!-- e.g., tax-10 for $10/tonne tax -->
            <scenario name="tax-{tax}" iterator="tax">
                <!-- C tax filenames differ only in the amount of tax -->
                <add name="carbon_tax">../input/policy/carbon_tax_{tax}_5.xml</add>
            </scenario>
        </scenarioGroup>
    </scenarios>

The example above defines an iterator named "tax", with values 10, 15, 20, and 25.
The scenario group includes the same baseline as before, but now there's only one
``<scenario>`` definition for the four policy cases. The term ``{tax}`` is replaced
by each value of the iterator in turn, defining a new scenario, and the file that
is included by the ``<add>`` element likewise uses the iterator value.

If you set the configuration file variable ``GCAM.ScenarioSetupOutputFile`` to
the pathname of a file, the ``run`` sub-command will write the "expanded" scenario
definitions to this file each time it runs. For example:

.. code-block:: cfg

    GCAM.ScenarioSetupOutputFile = %(Home)s/scenariosExpanded.xml

Results in the following:

.. code-block:: sh

    $ cat ~/scenariosExpanded.xml
    <setup>

       <scenarioGroup name="tax" useGroupDir="0">
          <scenario name="base" baseline="1">
          </scenario>
          <scenario name="tax-10" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_10_5.xml</add>
          </scenario>
          <scenario name="tax-15" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_15_5.xml</add>
          </scenario>
          <scenario name="tax-20" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_20_5.xml</add>
          </scenario>
          <scenario name="tax-25" baseline="0">
             <add name='carbon_tax'>../input/policy/carbon_tax_25_5.xml</add>
          </scenario>
       </scenarioGroup>
    </setup>

*In* :doc:`tutorial2`, *we begin to work with a "real" project definition.*
