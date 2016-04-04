``gcamtool.py``
================

The gcamtool.py script unifies GCAM workflow managment functionality into a
single script with sub-commands. Most sub-commands are implemented directly
by the pygcam library. Project-specific features can be added via
:ref:`plugins <plugins-label>`.

The sub-commands support all the major workflow setups, including

  * Modifying XML files and configuration.xml to set up a modeling experiment
    (See the :ref:`setup <setup-label>` sub-command and :doc:`setup` for more
    information.)

  * Running GCAM in an automatically-created workspace, allowing multiple
    instances of GCAM to run simultaneously, e.g., on parallel computing systems
    (See the :ref:`gcam <gcam-label>` sub-command.)

  * Executing batch queries against the XML database to extract GCAM results,
    with on-the-fly regionalization based on a simple region-mapping file.
    (See the :ref:`query <query-label>` sub-command.)

  * Computing differences between policy and baseline scenarios, including
    linear annualization of values between time-steps, and
    (See the :ref:`diff <diff-label>` sub-command.)

  * Plotting results, with flexible control of figure features including
    title, axis labels, scale, and so on.
    (See the :ref:`chart <chart-label>` sub-command.)

  * Manage (create, delete, rename, run commands in) automatically-created workspaces.
    (See the :ref:`ws <ws-label>` sub-command.)

In addition, the `runProj <runProj-label>` sub-command allows workflow steps to be
defined in an XML file so that individual or groups of steps can be executed for one
or more scenarios. The ``runProj`` sub-command supports direct invocation of other
workflow steps as well as running arbitrary programs of the user's choosing.

Command-line usage is described below.

Usage
-----
.. argparse::
   :module: pygcam.tool
   :func: _getMainParser
   :prog: gcamtool.py

   runProj : @replace
      .. _runProj-label:

      This sub-command reads instructions from the file :doc:`project-xml`, the
      location of which is taken from the user's :ref:`~/.pygcam.cfg <pygcam-cfg>` file.
      The workflow steps indicated in the XML file and command-line determine which
      commands to run.

      Examples:

      Run all steps for the default scenario group for project 'Foo':

      ::

          runProject.py Foo

      Run all steps for scenario group 'test' for project 'Foo', but only for
      scenarios 'baseline' and 'policy-1':

      ::

          runProject Foo -g test -S baseline,policy1

      or, equivalently:

      ::

          runProject Foo --group test --scenario baseline --step policy1

      Run only the 'setup' and 'gcam' steps for scenario 'baseline' in the
      default scenario group:

      ::

          runProject Foo -s setup,gcam -S baseline,policy-1

      Show the commands that would be executed for the above command, but
      don't run them:

      ::

          runProject Foo -s setup,gcam -S baseline,policy-1 -n


   protect : @replace
      .. _protect-label:

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

         gcamtool.py protect -f 0.8 "$INFILES" -l "$CLASSES" -r "$REGIONS" -o "$OUTDIR" -t 'prot_{filename}'


      .. code-block:: bash

         # Run the land protection scenario "s1", described in the file ``$HOME/protect.xml``,
         # placing the results in the directory ``$HOME/ws/workspace1``

         gcamtool.py protect -s s1 -S "$HOME/protect.xml" -w "$HOME/ws/workspace1"


   chart : @before
      .. _chart-label:


   diff : @before
      .. _diff-label:


   gcam : @before
      .. _gcam-label:


   query : @before
      .. _query-label:


   setup : @before
      .. _setup-label:


   ws : @before
      .. _ws-label:


Extending gcamtool using plug-ins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  .. _plugins-label:

The :doc:`gcamtool` script will load any python files whose name ends in
``_plugin.py``, found in any of the directores indicated in the config
file variable ``GCAM.PluginPath``. The value of ``GCAM.PluginPath`` must
be a sequence of directory names separated by colons (``:``) on Unix-like
systems or by semi-colons (``;``) on Windows. See :doc:`subcommand` for
documentation of the plug-in API.
