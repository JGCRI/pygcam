The ``pygcam.config`` module
=============================

This module provides access to configuration parameters. The parameters listed below
are defined with the given defaults, and then the user's ``~/.pygcam.cfg`` file is read,
overriding any defaults. User values should be defined in a section called ``[GCAM]``.

API
---

.. automodule:: pygcam.config
   :members:


Default values
--------------
The following config file is read (from the string ``pygcam.config._SystemDefaults``)
prior to reading the user's configuration file (``~/.pygcam.cfg``). In addition, all
environment variables are converted to config variables for easy reference (e.g.,
``%(Home)s``, the value of which is the user's home directory).

When de-referencing a config variable in the config file, beware the trailing 's'
after the closing parenthesis, which is necessary or an exception will be thrown.

  .. code-block:: INI

      [GCAM]
      # Sets the folder holding the symlink "current" which refers
      # to a folder holding Main_User_Workspace and ModelInterface.
      # (This is one way of setting up the code, but not required.)
      GCAM.Root = %(Home)s/GCAM

      # Refers to the GCAM folder holding the version of the model
      # you want to use. It is convenient to make this a symbolic link.
      GCAM.Current = %(GCAM.Root)s/current

      # The location of the Main_User_Workspace to use. This can refer
      # to any folder; GCAM.Current is just an optional convention.
      GCAM.Workspace = %(GCAM.Current)s/Main_User_Workspace

      # The location of GCAM source code (for the purpose of reading
      # the .csv file that defines the current regional aggregation.
      GCAM.SourceWorkspace =

      # The location of the ModelInterface to use.
      GCAM.ModelInterface = %(GCAM.Current)s/ModelInterface

      # The location of the default input file for runProject.py
      GCAM.ProjectXmlFile = %(Home)/gcam_project.xml

      # The location of the libraries needed by ModelInterface.
      # (Not needed if using GCAM with BaseX rather than dbxml.)
      GCAM.JavaLibPath = %(GCAM.Workspace)s/libs/dbxml/lib

      # Arguments to java to ensure that ModelInterface has enough
      # heap space.
      GCAM.JavaArgs = -Xms512m -Xmx2g

      # A string with one or more colon-delimited elements that identify
      # directories or XML files in which to find batch query definitions.
      GCAM.QueryPath = .

      # Columns to drop when processing results of XML batch queries
      GCAM.ColumnsToDrop = scenario,Notes,Date

      # The name of the queue used for submitting batch jobs on a cluster.
      GCAM.DefaultQueue = standard

      GCAM.QsubCommand = qsub -q {queueName} -N {jobName} -l walltime={walltime} \
         -d {exeDir} -e {logFile} -m n -j oe -l pvmem=6GB \
         -v QUEUE_GCAM_CONFIG_FILE='{configs}',QUEUE_GCAM_WORKSPACE='{workspace}',QUEUE_GCAM_NO_RUN_GCAM={noRunGCAM}

      # Note: --signal=USR1@15 => send SIGUSR1 15s before walltime expires
      GCAM.SlurmCommand = sbatch -p {queueName} --nodes=1 -J {jobName} -t {walltime} \
         -D {exeDir} --get-user-env=L -s --mem=6000 --tmp=6000 \
         --export=QUEUE_GCAM_CONFIG_FILE='{configs}',QUEUE_GCAM_WORKSPACE='{workspace}',QUEUE_GCAM_NO_RUN_GCAM={noRunGCAM}

      GCAM.BatchCommand = %(GCAM.QsubCommand)s

      # Arguments to qsub's "-l" flag that define required resources
      GCAM.QsubResources = pvmem=6GB

      # Environment variables to pass to qsub. (Not needed by most users.)
      GCAM.QsubEnviroVars =

      # Default location in which to look for scenario directories
      GCAM.ScenariosDir = %(GCAM.Root)s/scenarios

      # For qsub, the default number of minutes to allocate per task.
      GCAM.Minutes = 20

      # Whether to use the "virtual buffer", allowing ModelInterface to
      # run without generating pop-up windows on Linux.
      GCAM.UseVirtualBuffer = yes

      # A script to run by queueGCAM after GCAM completes. The script is
      # called with 3 arguments: workspace directory, XML configuration
      # file, and scenario name.
      GCAM.PostProcessor =

      # A file that maps GCAM regions to rename them or to aggregate
      # them. Each line consists of a GCAM region name, some number of
      # tabs, and the name to map the region to.
      GCAM.RegionMapFile =

      # Where to create temporary files
      GCAM.TempDir = /tmp
