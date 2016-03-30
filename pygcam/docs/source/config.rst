The ``pygcam.config`` module
=============================

This module provides access to configuration parameters. The parameters listed below
are defined with the given defaults, and then the user's ``~/.pygcam.cfg`` file is read,
overriding any defaults. User values should be defined in a section called ``[GCAM]``.

API
---

.. automodule:: pygcam.config
   :members:


.. _pygcam-cfg:


Default values
--------------
The following config file is read (from the string ``pygcam.config._SystemDefaults``)
prior to reading the user's configuration file (``~/.pygcam.cfg``). In addition, all
environment variables are converted to config variables for easy reference (e.g.,
``%(Home)s``, the value of which is the user's home directory).

When de-referencing a config variable in the config file, beware the trailing 's'
after the closing parenthesis, which is necessary or an exception will be thrown.

  .. code-block:: cfg

        [DEFAULT]
        # This project is used if '-s' flag not given to gcamtool
        GCAM.DefaultProject =

        # Where to find plug-ins. Internal plugin directory is added
        # automatically. Use this to add custom plug-ins outside the pygcam
        # source tree. The value is a semicolon-delimited (on Windows) or
        # colon-delimited (on Unix) string of directories to search for files
        # matching the pattern '*_plugin.py' NOTE: This must be set in the
        # DEFAULT section.
        GCAM.PluginPath =

        # Sets the folder holding the symlink "current" which refers
        # to a folder holding Main_User_Workspace and ModelInterface.
        # (This is one way of setting up the code, but not required.)
        GCAM.Root = %(Home)s/GCAM

        # Refers to the GCAM folder holding the version of the model
        # you want to use. It is convenient to make this a symbolic link.
        GCAM.Current = %(GCAM.Root)s/current

        # The default location in which to find or create GCAM workspaces
        GCAM.RunWorkspaceRoot = %(GCAM.Root)s/ws

        # The location of the Main_User_Workspace to use. This can refer
        # to any folder; GCAM.Current is just an optional convention.
        GCAM.RefWorkspace = %(GCAM.Current)s/Main_User_Workspace

        GCAM.RefQueryDir = %(GCAM.RefWorkspace)s/output/queries

        # The location of the ModelInterface to use.
        GCAM.ModelInterface = %(GCAM.Current)s/ModelInterface

        GCAM.ModelInterfaceLogFile = %(GCAM.TempDir)s/mi.log

        # QueryPath is string with one or more colon-delimited elements that
        # identify directories or XML files in which to find batch query
        # definitions.
        GCAM.QueryDir    = %(GCAM.RefQueryDir)s
        GCAM.QueryPath   = %(GCAM.QueryDir)s/Main_Queries.xml

        # The location of GCAM source code (for the purpose of reading
        # the .csv file that defines the current regional aggregation.
        GCAM.SourceWorkspace =

        # Root directory for where the user keeps project folders
        GCAM.ProjectRoot    = %(Home)s/projects

        # If using the XML "setup" system, this is the root folder for
        # setup source files
        GCAM.XmlSrc         = %(GCAM.ProjectRoot)s/xmlsrc

        # The folders for setup-generated XML files.
        GCAM.LocalXml       = %(GCAM.ProjectRoot)s/local-xml
        GCAM.DynXml         = %(GCAM.ProjectRoot)s/dyn-xml

        # The default input file for the runProj sub-command
        GCAM.ProjectXmlFile = %(GCAM.ProjectRoot)s/etc/project.xml

        # Default location in which to look for scenario directories
        GCAM.ScenariosDir =

        # The location of the libraries needed by ModelInterface
        GCAM.JavaLibPath = %(GCAM.RefWorkspace)s/libs/basex

        # Arguments to java to ensure that ModelInterface has enough
        # heap space.
        GCAM.JavaArgs = -Xms512m -Xmx2g

        # The name of the database file (or directory, for BaseX)
        GCAM.DbFile	  = database_basexdb

        # Columns to drop when processing results of XML batch queries
        GCAM.ColumnsToDrop = scenario,Notes,Date

        # Change this if desired to increase or decrease diagnostic messages.
        # A default value can be set here, and a project-specific value can
        # be set in the project's config file section. Possible values (from most
        # to least verbose) are: DEBUG, INFO, WARNING, ERROR, CRITICAL
        GCAM.LogLevel   = WARNING

        # Save log messages in the indicated file
        GCAM.LogFile    =

        # Show log messages on the console (terminal)
        GCAM.LogConsole = True

        # The name of the queue used for submitting batch jobs on a cluster.
        GCAM.DefaultQueue = standard

        GCAM.QsubCommand = qsub -q {queueName} -N {jobName} -l walltime={walltime} \
          -d {exeDir} -e {logFile} -m n -j oe -l pvmem=6GB -v %(GCAM.OtherBatchArgs)s \
          QUEUE_GCAM_CONFIG_FILE='{configs}',QUEUE_GCAM_WORKSPACE='{workspace}',QUEUE_GCAM_NO_RUN_GCAM={noRunGCAM}

        # --signal=USR1@15 => send SIGUSR1 15s before walltime expires
        GCAM.SlurmCommand = sbatch -p {queueName} --nodes=1 -J {jobName} -t {walltime} \
          -D {exeDir} --get-user-env=L -s --mem=6000 --tmp=6000 %(GCAM.OtherBatchArgs)s \
          --export=QUEUE_GCAM_CONFIG_FILE='{configs}',QUEUE_GCAM_WORKSPACE='{workspace}',QUEUE_GCAM_NO_RUN_GCAM={noRunGCAM}

        # Arbitrary arguments to add to the selected batch command
        GCAM.OtherBatchArgs =

        GCAM.BatchCommand = %(GCAM.SlurmCommand)s

        # Set this to a command to run when the -l flag is passed to gcamtool's
        # "run" sub-command. The same options are available for substitution as
        # for the GCAM.BatchCommand.
        GCAM.LocalCommand =

        # Arguments to qsub's "-l" flag that define required resources
        GCAM.QsubResources = pvmem=6GB

        # Environment variables to pass to qsub. (Not needed by most users.)
        GCAM.QsubEnviroVars =

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

        # For Windows users without permission to create symlinks
        GCAM.CopyAllFiles = False
