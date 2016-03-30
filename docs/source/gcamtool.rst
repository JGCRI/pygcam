``gcamtool.py``
================

The gcamtool.py script organizes GCAM workflow functionality into a single
script with sub-commands. The sub-commands are implemented via
:ref:`plugins <plugins-label>`, so new (and project-specific) sub-commands
are easily added.

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


Extending gcamtool using plug-ins
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  .. _plugins-label:

The :doc:`gcamtool` script will load any python files whose name ends in
``_plugin.py``, found in any of the directores indicated in the config
file variable ``GCAM.PluginPath``. The value of ``GCAM.PluginPath`` must
be a sequence of directory names separated by colons (``:``) on Unix-like
systems or by semi-colons (``;``) on Windows. See :doc:`subcommand` for
documentation of the plug-in API.
