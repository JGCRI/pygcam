``gcamtool.py``
===============

The gcamtool.py script organizes GCAM workflow functionality into a single
script with sub-commands. The sub-commands are implemented via plug-ins,
so new sub-commands are easily added.

Command-line usage is described below.

Usage
-----
.. argparse::
   :module: pygcam.bin.gcamtool
   :func: _getMainParser
   :prog: gcamtool.py

   runProj : @after
      .. _runProj-label:

      [Note: This script reads instructions from the file :ref:`project.xml <project-xml>`, the
      location of which is taken from the user's :ref:`~/.pygcam.cfg <pygcam-cfg>` file. The
      :ref:`gcamtool runProj <runProj-label>` sub-command was developed for use with the
      `gcam-utils <https://bitbucket.org/plevin/gcam-utils/wiki/Home>`__
      scripts, however any scripts or programs can be called in workflow 'steps'.]

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

      [N.B. The :ref:`project.xml <protect-xml>` page describes the XML input file to this sub-command.]
