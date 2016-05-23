Tutorial -- Using ``pygcam``
=============================

  .. note::

        This tutorial is currently under development!

Initial configuration
-----------------------

The ``pygcam`` package uses a configuration file stored in ``$(HOME)/.pygcam.cfg``. When ``gt``
runs, it checks whether this file exists. If not, it creates the file, with all possible
configuration parameters shown in comments explaining their purpose and showing their
default values. Uncomment a line by removing the leading '#' character.

``pygcam`` requires that certain variables be set. The table below shows
key variables, indicating whether they are required or optional, and whether their value
must be a file or directory.

+----------------------+----------+-----------+
| Variable name        | Required | Type      |
+======================+==========+===========+
| GCAM.SandboxRoot     | yes      | directory |
+----------------------+----------+-----------+
| GCAM.ProjectRoot     | yes      | directory |
+----------------------+----------+-----------+
| GCAM.QueryDir        | yes      | directory |
+----------------------+----------+-----------+
| GCAM.ModelInterface  | yes      | directory |
+----------------------+----------+-----------+
| GCAM.RefWorkspace    | yes      | directory |
+----------------------+----------+-----------+
| GCAM.TempDir         | yes      | directory |
+----------------------+----------+-----------+
| GCAM.ProjectXmlFile  | yes      | file      |
+----------------------+----------+-----------+
| GCAM.RefConfigFile   | yes      | file      |
+----------------------+----------+-----------+
| GCAM.JarFile         | yes      | file      |
+----------------------+----------+-----------+
| GCAM.RegionMapFile   | no       | directory |
+----------------------+----------+-----------+
| GCAM.UserTempDir     | no       | directory |
+----------------------+----------+-----------+
| GCAM.RewriteSetsFile | no       | file      |
+----------------------+----------+-----------+

    .. seealso::

       The configuration API and default variable settings are described in :doc:`config`

Configuration file sections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The configuration file is divided into sections indicated by a name in square brackets.
All variable declarations following a section declaration, until the next section
declaration (if any) appear in the declared section. You can declare a section multiple
times to add new values to the section.

Project sections
~~~~~~~~~~~~~~~~~~
Each project should have its own section. For example, to setup a project called, say,
"Paper1", I would create the section ``[Paper1]``. Following this, I would define variables
particular to this project, e.g., where the to find the files defining scenarios, queries,
and so on.

Default section
~~~~~~~~~~~~~~~~~
Default values are defined in the ``[DEFAULT]`` section. When ``pygcam`` requests the value
of a variable from a project section, the default value is returned if the variable is not
defined in the project section. Variables that you want to set uniformly for all of your
projects can be defined in the ``[DEFAULT]`` section.

All pre-defined ``pygcam`` variables are defined in the ``[DEFAULT]`` section,
allowing them to be overridden on a project-by-project basis.

Using configuration variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Within the configuration file, variables are often defined in terms of other variables.
The syntax for referencing the value of a variable is the precede the variable name with
``%(`` and follow it with ``)s``. This to reference variable ``GCAM.QueryDir``, you
would write ``%(GCAM.QueryDir)``. Note that variable names are case-sensitive.

Variables' values are substituted when a variable's value is requested, not when the
variable is defined. The difference is that if variable ``A`` is defined in terms of
variable ``B``, (e.g., ``A = %(B)s/something/else``), you can subsequently change
``B`` and the value of ``A`` will show this when ``A`` is accessed by ``pygcam``.

Sample configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Below is a sample configuration file for a project called ``Paper1``. The user has
created some (non-pygcam) variables prefixed by ``User.``. The prefixes are merely a
convention to identify standard pygcam variables. For user-defined variables, use any
prefix desired, or none at all.

 .. code-block:: cfg

    [DEFAULT]
    GCAM.DefaultProject = Paper1

    User.ProjectName    = _NOT_SET_
    User.RepoRoot       = %(Home)s/git-repo
    GCAM.ProjectRoot    = %(User.RepoRoot)s/%(User.ProjectName)s
    GCAM.SandboxRoot    = %(Home)s/ws/%(User.ProjectName)s

    GCAM.LogLevel       = INFO
    GCAM.ShowStackTrace = True
    GCAM.ModelInterfaceLogFile = %(Home)s/tmp/mi.log
    GCAM.UseVirtualBuffer = True

    GCAM.Root           = %(Home)s/GCAM
    GCAM.RefWorkspace   = %(GCAM.Current)s/Main_User_Workspace
    GCAM.ModelInterface = /pic/projects/GCAM/ModelInterface
    GCAM.JavaLibPath    = /pic/projects/GCAM/GCAM-libraries/lib/basex
    GCAM.OtherBatchArgs = -A my_account

    GCAM.QueryDir  = %(GCAM.ProjectRoot)s/queries
    GCAM.QueryPath = %(GCAM.QueryDir)s

    # Default location for query results
    GCAM.OutputDir = %(Home)s/ws/output

    # Setup config files to not write extraneous files, so of which are very large
    GCAM.WriteDebugFile     = False
    GCAM.WritePrices        = False
    GCAM.WriteXmlOutputFile = False
    GCAM.WriteOutputCsv     = False

    [Paper1]
    User.ProjectName   = paper1
    GCAM.RegionMapFile = %(GCAM.ProjectRoot)s/etc/Regions.txt
    GCAM.PluginPath    = %(User.RepoRoot)s/paper1/plugins


Location of GCAM program and data files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The configuration variable ``GCAM.RefWorkspace`` must point to a directory
structured like the standard GCAM ``Main_User_Workspace``, with sub-directories
for ``input``, ``output``, ``libs``, and ``exe``.

The variable ``GCAM.ModelInterface`` should point to a directory holding the
ModelInterface program. This is used to locate the ``jar`` (Java archive) file
that contains the ModelInterface code. The variable ``GCAM.JarFile`` provides
the location of the jar file. The variable is initialized differently on Windows,
OS X, and Linux as follows:

  +---------+---------------------------------------------------------------------------------------+
  | System  | Default definition of GCAM.JarFile                                                    |
  +=========+=======================================================================================+
  | Windows | %(GCAM.ModelInterface)s/ModelInterface.jar                                            |
  +---------+---------------------------------------------------------------------------------------+
  | Linux   | %(GCAM.ModelInterface)s/ModelInterface.jar                                            |
  +---------+---------------------------------------------------------------------------------------+
  | OS X    | %(GCAM.ModelInterface)s/ModelInterface.app/Contents/Resources/Java/ModelInterface.jar |
  +---------+---------------------------------------------------------------------------------------+

You can set either ``GCAM.ModelInterface``, if the definition above for ``GCAM.JarFile`` is correct
for your installation, or you can directly set ``GCAM.JarFile``.

Note that ``pygcam`` does not run GCAM in the reference workspace; it uses the files there to
create new workspaces as required. Creating separate workspaces for each scenario allows multiple
scenarios to be run simultaneously without contention for the XML database which is created at the
end of the model run.

Project structure
------------------

  * XML files
  * xmlsrc, local-xml, dyn-xml
  * scenarios.py


Setting up a GCAM experiment
----------------------------------
TBD.


Running a GCAM experiment
----------------------------

Run-time structure:

  * SandboxRoot
      * *figure showing sandbox structure*

  * Create a file :doc:`project-xml` (template ...)

  * Use the ``run`` sub-command of :doc:`gcamtool`

    * Hint: use ``-l``, ``-L``, and ``-g`` to list steps, scenarios, and groups

    * Choose steps, scenarios, groups to run using ``-s``, ``-S``, and ``-g`` flags,
      and choose steps or scenarios *not* to run using ``-k`` and ``-K`` flags.

    * Setting defaults to simplify use


