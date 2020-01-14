GCAM tool (``gt``)
===================

The gt script unifies GCAM workflow managment functionality into a
single script with sub-commands. Generic sub-commands are implemented directly
by the pygcam library. Project-specific features can be added via
:ref:`plugins <plugins-label>`.


.. note::
   Quick links to sub-commands:
   :ref:`building <building>`,
   :ref:`chart <chart>`,
   :ref:`config <config>`,
   :ref:`diff <diff>`,
   :ref:`gcam <gcam>`,
   :ref:`gui <gui>`,
   :ref:`init <init>`,
   :ref:`mcs <mcs>`,
   :ref:`mi <mi>`,
   :ref:`new <new>`,
   :ref:`protect <protect>`,
   :ref:`query <query>`,
   :ref:`run <run>`,
   :ref:`setup <setup>`,
   :ref:`sandbox <sandbox>`,
   :ref:`transport <transport>`

The sub-commands support all the major workflow setups, including

  * Modify XML files and configuration.xml to set up a modeling experiment
    (See the :ref:`setup <setup>` sub-command and :doc:`setup` for more
    information.)

  * Run GCAM in an automatically-created workspace, allowing multiple
    instances of GCAM to run simultaneously, e.g., on parallel computing systems
    (See the :ref:`gcam <gcam>` sub-command.)

  * Execute batch queries against the XML database to extract GCAM results,
    with on-the-fly regionalization based on a simple region-mapping file.
    (See the :ref:`query <query>` sub-command.)

  * Compute differences between policy and baseline scenarios, including
    linear annualization of values between time-steps, and
    (See the :ref:`diff <diff>` sub-command.)

  * Plot results, with flexible control of figure features including
    title, axis labels, scale, and so on.
    (See the :ref:`chart <chart>` sub-command.)

  * Manage (create, delete, rename, run commands in) automatically-created
    workspaces. (See the :ref:`sandbox <sandbox>` sub-command.)

In addition, the :ref:`run <run>` sub-command allows workflow steps to be
defined in an XML file so that individual or groups of steps can be executed for one
or more scenarios. The ``run`` sub-command supports direct invocation of other
workflow steps as well as running arbitrary programs of the user's choosing.

Finally, gt allows all project steps to be run on a compute node in a
High-Performance Computing environment by specifying ``+b`` or ``--batch`` on the
command-line. (Note that this is not available on Mac OS X or Windows.)

For example, the command:

.. code-block:: bash

   gt +b +P MyProject run -S MyScenario

runs all steps for scenario ``MyScenario`` in the project ``MyProject`` by
queuing a batch job on the default queue. Arguments to ``gt`` allow
the user to set various resource requirements and to select the queue to use.

The command to run to queue the batch job is taken from the configuration
file parameter ``GCAM.BatchCommand``. Example batch commands for the SLURM
and PBS job management systems are provided in variables ``GCAM.QueueSLURM``
and ``GCAM.QueuePBS``, respectively.

Command-line usage is described below. Note that some command-line
(e.g., batch-related) options must precede the sub-command, whereas
sub-command specific options must follow it.

.. note::

  Note that arguments that pertain regardless of the sub-command
  (e.g., ``+P`` to identify the project name) are specified *prior to*
  the sub-command, and use ``+`` rather than ``-``. This is to avoid
  conflicts between these "main" arguments and sub-command arguments.
  (An exception is ``gt -h``, which retains the ``-``.) Long-form
  argument names use two hyphens, as in ``--projectName``.)

Usage
-----
.. argparse::
   :module: pygcam.tool
   :func: _getMainParser
   :prog: gt


   run : @replace
      .. _run:

      This sub-command reads instructions from the file :doc:`project-xml`, the
      location of which is taken from the user's :ref:`~/.pygcam.cfg <pygcam-cfg>` file.
      The workflow steps indicated in the XML file and command-line determine which
      commands to run.

      Examples:

      Run all steps for the default scenario group for project 'Foo':

      ::

          gt +P Foo run

      Run all steps for scenario group 'test' for project 'Foo', but only for
      scenarios 'baseline' and 'policy-1':

      ::

          gt +P Foo run -g test -S baseline,policy1

      or, equivalently:

      ::

          gt +P Foo run --group test --scenario baseline --step policy1

      Run only the 'setup' and 'gcam' steps for scenario 'baseline' in the
      default scenario group:

      ::

          gt +P Foo run -s setup,gcam -S baseline,policy-1

      Same as above, but queue a batch job to run these commands on the queue
      'short':

      ::

          gt +b +q short +P Foo run -s setup,gcam -S baseline,policy-1


      Note that the command above will run the two scenarios ('baseline' and
      'policy-1') in a single batch job. To run scenarios in separate batch
      jobs, use the ``-D`` or ``--distribute`` option to the run sub-commmand:

      ::

         gt +q short +P Foo run -D -S baseline,policy-1

      The "distribute" option knows that various project steps for non-baseline
      scenarios may  depend on baseline scenarios, so the baseline is always run first,
      with the non-baseline scenarios queued as dependent on the successful completion
      of the baseline. If no scenarios are explicitly named, all scenarios in the group
      are run, as usual.

      The ``-n`` flag displays the commands that would be executed for a command, but
      doesn't run them:

      ::

          gt +P Foo run -s setup,gcam -S baseline,policy-1 -n


   building : @replace
      .. _building:

      Generates a template CSV file which can be edited to set building energy efficiency
      improvements that are applied by the callable function "buildingTechEfficiency", which
      must be called in your scenarios.xml file.

   chart : @replace
      .. _chart:

      The ``chart`` sub-command generates plots from GCAM-style ".csv" files.
      Two types of plots are currently supported: (i) stacked bar plots based on summing values
      over all years (with optional interpolation of annual values), by the given 'indexCol'
      (default is 'region'), and (ii) stacked bar plots by year for some data column, where the data
      are grouped by and summed across elements with the indicated 'indexCol'. The first option is
      indicated by using the ``-S`` (``--sumYears``) option. Numerous options allow the appearance to
      be customized.

      You can perform on-the-fly unit conversions using the ``-m`` / ``--multiplier`` or
      ``-V`` / ``--divisor`` arguments, which cause all values in "year columns" to be
      multiplied or divided, respectively, by the values provided. Values can be specified
      as numeric constants or using symbolic constants defined in the :doc:`pygcam.units`
      module.


   config : @replace
      .. _config:

      The config command list the values of configuration variables from ~/.pygcam.cfg.
      With no arguments, it displays the values of all variables for the default project.
      Use the ``-d`` flag to show only values from the ``[DEFAULT]`` section.

      If an argument ``name`` is provided, it is treated as a substring pattern, unless the
      ``-x`` flag is given (see below). All configuration variables containing the give name
      are displayed with their values. The match is case-insensitive.

      If the ``-x`` or ``--exact`` flag is specified, the argument is treated as an exact
      variable name (case-sensitive) and only the value is printed. This is useful mainly
      for scripting. For general use the substring matching is more convenient.

      Examples:

      .. code-block:: bash

         $ gt config project
         [MyProject]
         GCAM.DefaultProject = MyProject
         GCAM.ProjectRoot = /Users/rjp/bitbucket/myProject
         GCAM.ProjectXmlFile = /Users/rjp/bitbucket/myProject/etc/project.xml

         $ gt config -x GCAM.DefaultProject
         MyProject

         $ gt config sand
         MyProject]
         GCAM.SandboxRoot = /Users/rjp/ws/myProject

         $ gt config sand -d
         [DEFAULT]
         GCAM.SandboxRoot = /Users/rjp/ws


   diff : @replace
      .. _diff:

      The ``diff`` sub-command script computes the differences between results from two or
      more CSV files generated from batch queries run on a GCAM database, saving
      the results in either a CSV or XLSX file, according to the extension given to
      the output file. If not provided, the output filename defaults to differences.csv.

      If multiple otherFiles are given (i.e., the referenceFile plus 2 or more other
      files named on the command-line), the resulting CSV file will contain one difference
      matrix for each otherFile, with a label indicating which pair of files were used
      to produce each result.

      When the output file is in XLSX format, each result is
      written to a separate worksheet. If the -c flag is specified, no differences are
      computed; rather, the .csv file contents are combined into a single .xlsx file.


   gcam : @replace
      .. _gcam:

      The ``gcam`` sub-command runs the GCAM executable on the designated configuration
      file, scenario, or workspace. Typical use (e.g., from a ``project.xml`` file) would
      be to run GCAM by referencing a directory named the same as a scenario, holding a
      file called ``config.xml``, as is generated by the ``setup`` sub-command. (See
      :doc:`setup`.)

      If a `workspace` is specified on the command-line, it is used. Otherwise, if a
      `scenario` is specified, the workspace defined by {GCAM.SandboxDir}/{scenario}
      is used. If neither `workspace` nor `scenario` are defined, the value of config
      variable ``GCAM.RefWorkspace`` is used, i.e., GCAM is run in the reference
      workspace.

      If the workspace doesn't exist, it is created based on the reference GCAM workspace,
      defined by the configuration variable ``GCAM.RefWorkspace``. By default, read-only
      directories (e.g., input and libs) are symbolically linked from the new workspace to
      the reference one. (See the :ref:`new <new>` sub-command for more information
      on the creation of workspaces.)

      Directories into which GCAM writes results
      (e.g., output and exe) are created in the new workspace, but read-only files within exe
      (e.g., the GCAM executable) are symbolically linked (with the same caveat for Windows
      users.)

      Usage example:

      .. code-block:: bash

         gt gcam -S ~/MyProject/scenarios -s MyScenario -w ~/sandboxes/MyProject/MyScenario

      would run the scenario ``MyScenario`` in the newly created sandbox (workspace)
      ``~/sandboxes/MyProject/MyScenario`` using the configuration file
      ``~/MyProject/scenarios/MyScenario/config.xml``.


   gui : @replace
      .. _gui:

       Run the Graphical User Interface (GUI) generated from the command-line interface
       in a local web server available at http://127.0.0.1:8050.


   init : @replace
      .. _init:

      Create the configuration file ~/.pygcam.cfg and initialize key variables, based
      on command-line arguments, or interactive prompts. See :doc:`initialize` for
      details.

   mcs : @replace
      .. _mcs:

      Enable or disable Monte Carlo Simulation (MCS) mode, or check whether MCS mode
      is currently enabled or disabled.

   mi : @replace
      .. _mi:

      Invoke ModelInterface from the command-line after changing directory to the value
      of config variable ``GCAM.QueryDir``. If the file ``model_interface.properties`` is found,
      it is used as is, unless the ``-u/--updateProperties`` flag is specified, in which case
      the file is modified so that the ``queryFile`` entry refers to the value of
      ``GCAM.MI.QueryFile``, if this refer to an existing file, otherwise, by variable the
      ``GCAM.MI.RefQueryFile``.

      If the file ``model_interface.properties`` is not found, it is created automatically
      before invoking ModelInterface.

      If the ``-d/--useDefault`` flag is given, the ``model_interface.properties`` file is
      modified to refer to the GCAM reference ``Main_Queries.xml`` file.

      If you have a customized queries XML file, set the config variable ``GCAM.MI.QueryFile``
      to the path to this file and it will be loaded into ModelInterface via this command.


   new : @replace
      .. _new:

      Create the directory structure and basic files required for a new pygcam project.
      If a directory is specified with the ``-r`` flag, the project is created with the
      given name in that directory; otherwise the project is created in the directory
      identified by the config variable ``GCAM.ProjectRoot``.

      This sub-command creates examples of ``xmlsrc/scenarios.py``,
      ``etc/protection.xml``, ``etc/project.xml``, ``etc/rewriteSets.xml``, and
      ``etc/scenarios.xml`` that can be edited to fit the needs of your project.
      The file ``etc/Instructions.txt`` is also created to provide further information.

      If the ``-c`` flag is given, a basic entry for the new project is added to the
      users configuration file, ``$HOME/.pygcam.cfg``. Before modifying the config file,
      a backup is created in ``$HOME/.pygcam.cfg~``. For example, the command

      .. code-block:: sh

         gt new -c foo

      generates and entry like this:

      .. code-block:: cfg

         [foo]
         # Added by "new" sub-command Thu Sep 22 14:30:29 2016
         GCAM.ProjectDir        = %(GCAM.ProjectRoot)s/foo
         GCAM.ScenarioSetupFile = %(GCAM.ProjectDir)s/etc/scenarios.xml
         GCAM.RewriteSetsFile   = %(GCAM.ProjectDir)s/etc/rewriteSets.xml

      The example project defines two scenario groups, consisting of a baseline
      and 4 carbon tax scenarios. In one group, 90% of unmanaged land is protected
      (i.e., removed from consideration), as in the reference GCAM scenario. In the
      other scenario group, this protection is not performed, so all land is
      considered available for use.

   protect : @replace
      .. _protect:

      Generate versions of GCAM's land_input XML files that protect a given fraction of
      land of the given land types in the given regions by subtracting the required land
      area from the "managed" land classes, thereby removing them from consideration in
      land allocations.

      Simple protection scenarios can be specified on the command-line. More complex
      scenarios can be specified in an XML file, :ref:`landProtection.xml <protect-xml>`.

      Examples:

      .. code-block:: bash

         # Create and modify copies of the reference land files, renaming them with
         # "prot\_" prefix. Protect 80% of the "UnmanagedForest" and "UnmanagedPasture"
         # land classes in the specified regions only.

         CLASSES=UnmanagedForest,UnmanagedPasture
         REGIONS='Australia_NZ,Canada,EU-12,EU-15,Japan,Middle East,Taiwan,USA'
         OUTDIR="$HOME/tmp/xml"

         gt protect -f 0.8 "$INFILES" -l "$CLASSES" -r "$REGIONS" -o "$OUTDIR" -t 'prot_{filename}'


      .. code-block:: bash

         # Run the land protection scenario "s1", described in the file ``$HOME/protect.xml``,
         # placing the results in the directory ``$HOME/ws/workspace1``

         gt protect -s s1 -S "$HOME/protect.xml" -w "$HOME/ws/workspace1"


   query : @replace
      .. _query:

      Run one or more GCAM database queries by generating and running the
      named XML queries. The results are placed in a file in the specified
      output directory with a name composed of the basename of the
      XML query file plus the scenario name. For example,

      .. code-block:: bash

         gt query -o. -s MyReference,MyPolicyCase liquids-by-region

      would run the ``liquids-by-region`` query on two scenarios, MyReference and
      MyPolicyCase. Query results will be stored in the files
      ``./liquids-by-region-MyReference.csv`` and ``./liquids-by-region-MyPolicyCase.csv``.

      The named queries are located using the value of config variable ``GCAM.QueryPath``,
      which can be overridden with the ``-Q`` argument. The QueryPath consists of one or
      more colon-delimited (on Unix) or semicolon-delimited (on Windows) elements that
      can identify directories or XML files. The elements of QueryPath are searched in
      order until the named query is found. If a path element is a directory, the filename
      composed of the query + '.xml' is sought in that directory. If the path element is
      an XML file, a query with a title matching the query name (first literally, then by
      replacing ``'_'`` and ``'-'`` characters with spaces) is sought. Note that query names are
      case-sensitive.


   sandbox : @replace
      .. _sandbox:

      The ``sandbox`` sub-command allows you to create, delete, show the path of, or run a shell
      command in a workspace. If the ``--scenario`` argument is given, the operation is
      performed on a scenario-specific workspace within a project directory. If ``--scenario``
      is not specified, the operation is performed on the project directory that contains
      individual scenario workspaces. Note that the :ref:`gcam <gcam>` sub-command
      automatically creates workspaces as needed.

      N.B. You can run ``sandbox`` with the ``--path`` option before performing any
      operations to be sure of the directory that will be operated on, or use the
      ``--noExecute`` option to show the command that would be executed by ``--run``.


   setup : @replace
      .. _setup:

      The ``setup`` sub-command automates modification to copies of GCAM's input XML
      files and construction of a corresponding configuration XML file.
      See :doc:`setup` for a detailed description.


   transport : @replace
      .. _transport:

      Generates a template CSV file which can be edited to set transport energy efficiency
      improvements that are applied by the callable function "transportTechEfficiency", which
      must be called in your scenarios.xml file.

Extending gt using plug-ins
------------------------------
  .. _plugins-label:

The gt script will load any python files whose name ends in
``_plugin.py``, found in any of the directories indicated in the config
file variable ``GCAM.PluginPath``. The value of ``GCAM.PluginPath`` must
be a sequence of directory names separated by colons (``:``) on Unix-like
systems or by semi-colons (``;``) on Windows.

See :doc:`pygcam.subcommand` for documentation of the plug-in API.
