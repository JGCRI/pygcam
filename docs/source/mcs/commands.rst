Sub-commands for Monte Carlo Simulation
========================================

The ``pygcam.mcs`` sub-package provides additional plug-ins for the :doc:`../gcamtool`
to support defining, running, and analyzing Monte Carlo Simulations (MCS) with GCAM.

The :doc:`../gcamtool` will automatically load the built-in sub-commands
defined in ``pygcam.mcs`` if the file ``$HOME/.use_pygcam_mcs`` exists.
This "sentinel" file allows the ``pygcam-mcs`` to be "turned off" to produce
shorter help messages when not working with Monte Carlo simulations. Use the
:ref:`gt mcs <mcs>` sub-command to enable, disable, or check the status
of MCS mode.

This page describes only the sub-commands provided by ``pygcam.mcs``. See the
:doc:`../gcamtool` documentation for more info.

.. note::
   Quick links to sub-commands:
   :ref:`addexp <addexp>`,
   :ref:`analyze <analyze>`,
   :ref:`cluster <cluster>`,
   :ref:`delsim <delsim>`,
   :ref:`explore <explore>`,
   :ref:`discrete <discrete>`,
   :ref:`gensim <gensim>`,
   :ref:`ippsetup <ippsetup>`,
   :ref:`iterate <iterate>`,
   :ref:`runsim <runsim>`,

.. argparse::
   :ref: pygcam.mcs.dummy_tool.getMainParser
   :prog: gt

   addexp : @replace
      .. _addexp:

      Adds the named experiment to the database, with an optional description.

   analyze : @replace
      .. _analyze:

      Analyze simulation results stored in the database for the given simulation.
      At least one of ``-c``, ``-d``, ``-i``, ``-g``, ``-p``, ``-t`` (or their
      longname equivalents) must be specified.

   cluster : @replace
      .. _cluster:

      Start an :doc:`ipyparallel <ipyparallel:intro>` cluster after generating batch
      file templates based on parameters in ``.pygcam.cfg`` and the number of tasks
      to run. Note that the :ref:`runsim <runsim>` sub-command will start a cluster
      if one is not already running. More often, this command is used to stop a cluster.

   discrete : @replace
      .. _discrete:

      Convert csv files to the .ddist format.

   explore : @replace
      .. _explore:

      Run the MCS "explorer", a browser-based interactive tool for exploring Monte
      Carlo simulation results. After running ``gt explore``, point your browser to
      http://localhost:8050 to load the :doc:`explorer`.

   gensim : @replace
      .. _gensim:

      Generates input files for simulations by reading ``{ProjectDir}/mcs/parameters.xml``
      in the project directory.

   delsim : @replace
      .. _delsim:

      Delete simulation results and re-initialize the database for the given user
      application. This is done automatically by the sub-command ``gensim`` when
      the ``--delete`` flag is specified.

   ippsetup : @replace
      .. _ippsetup:

      Create a new ipyparallel profile to use with ``pygcam.mcs``. This command
      generates the profile and edits the default configuration files as per
      command-line arguments to this sub-command.

   iterate : @replace
      .. _iterate:

      Run a command in each ``trialDir``, or if ``expName`` is given, in each
      ``expDir``. The following arguments are available for use in the command
      string, specified within curly braces: ``appName``, ``simId``, ``trialNum``,
      ``expName``, ``trialDir``, ``expDir``. For example, to run the fictional program
      “foo” in each trialDir for a given set of parameters, you might write::

        gt iterate -s1 -c “foo -s{simId} -t{trialNum} -i{trialDir}/x -o{trialDir}/y/z.txt”.

   parallelPlot : @replace
      .. _parallelPlot:

      Generate a parallel coordinates plot for a set of simulation results.


   runsim : @replace
      .. _runsim:

      Run the identified trials on compute engines.

