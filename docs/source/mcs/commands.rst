Sub-commands for Monte Carlo Simulation
========================================

The ``pygcam.mcs`` sub-package provides additional plug-ins for the :doc:`../gcamtool`
to support defining, running, and analyzing Monte Carlo Simulations (MCS) with GCAM.

The :doc:`../gcamtool` will automatically load the built-in sub-commands
defined in ``pygcam.mcs`` if the file ``$HOME/.use_pygcam_mcs`` exists.
This "sentinel" file allows the ``pygcam-mcs`` to be "turned off" to produce
shorter help messages when not working with Monte Carlo simulations. Use the
:ref:`gt mcs <mcs-label>` sub-command to enable, disable, or check the status
of MCS mode.

This page describes only the sub-commands provided by ``pygcam.mcs``. See the
:doc:`../gcamtool` documentation for more info.

.. note::
   Quick links to sub-commands:
   :ref:`addexp <addexp-label>`,
   :ref:`analyze <analyze-label>`,
   :ref:`cluster <cluster-label>`,
   :ref:`delsim <delsim-label>`,
   :ref:`discrete <discrete-label>`,
   :ref:`gensim <gensim-label>`,
   :ref:`iterate <iterate-label>`,
   :ref:`newsim <newsim-label>`,
   :ref:`runsim <runsim-label>`,

.. argparse::
   :module: pygcam.mcs.dummy_tool
   :func: _getMainParser
   :prog: gt

   addexp : @replace
      .. _addexp-label:

      Adds the named experiment to the database, with an optional description.

   analyze : @replace
      .. _analyze-label:

      Analyze simulation results stored in the database for the given simulation.
      At least one of ``-c``, ``-d``, ``-i``, ``-g``, ``-p``, ``-t`` (or their
      longname equivalents) must be specified.

   cluster : @replace
      .. _cluster-label:

      Start an :doc:`ipyparallel <ipyparallel:intro>` cluster after generating batch
      file templates based on parameters in ``.pygcam.cfg`` and the number of tasks
      to run.

   discrete : @replace
      .. _discrete-label:

      Convert csv files to the .ddist format.

   gensim : @replace
      .. _gensim-label:

      Generates input files for simulations by reading ``{ProjectDir}/mcs/parameters.xml``
      in the project directory.


   delsim : @replace
      .. _delsim-label:

      Delete simulation results and re-initialize the database for the given user
      application. This is done automatically by the sub-command ``newsim`` and
      should be used only to recreate the database from scratch.

   iterate : @replace
      .. _iterate-label:

      Run a command in each ``trialDir``, or if ``expName`` is given, in each
      ``expDir``. The following arguments are available for use in the command
      string, specified within curly braces: ``appName``, ``simId``, ``trialNum``,
      ``expName``, ``trialDir``, ``expDir``. For example, to run the fictional program
      “foo” in each trialDir for a given set of parameters, you might write::

        gt iterate -s1 -c “foo -s{simId} -t{trialNum} -i{trialDir}/x -o{trialDir}/y/z.txt”.

   newsim : @replace
      .. _newsim-label:


   parallelPlot : @replace
      .. _parallelPlot-label:

      Generate a parallel coordinates plot for a set of simulation results.


   runsim : @replace
      .. _runsim-label:

      Run the identified trials on compute engines.

