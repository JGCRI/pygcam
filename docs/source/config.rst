Configuration System
=============================

The ``pygcam`` scripts and libraries rely on a configuration file to:

  * define the location of essential and optional files,
  * allow the user to set defaults for many command-line arguments to scripts, and
  * define both global default and project-specific values for all parameters

The :doc:`pygcam.config` module provides access to configuration parameters. The
configuration file and the API to access it are described below.

.. seealso::
   Usage of the ``config`` sub-command is described on the
   :ref:`gt config <config-label>` page. See :doc:`pygcam.config`
   for documentation of the API to the configuration system.

.. _pygcam-cfg:

The configuration files
-----------------------
There are up to 4 configuration files read, two of which are user-modifiable:

  #. First, ``pygcam/etc/system.cfg`` is read from within the ``pygcam`` package. This
     defines all known config variables and provides their default values as described
     below. The values in this file are the appropriate values for Linux and similar systems.
     *This file should not be modified by the user.*

  #. Next, a platform-specific file is read, if it exists. Currently, the only such
     files are ``pygcam/etc/Windows.cfg`` and ``pygcam/etc/Darwin.cfg``, read on Windows
     and Macintosh systems, respectively. (N.B. "Darwin" is the official platform name
     for the Macintosh operating system.) *These files should not be modified by the user.*

  #. Next, if the environment variable ``PYGCAM_SITE_CONFIG`` is defined, it should
     refer to a configuration file that defines site-specific settings. This file is
     optional; it allows an administrator to consolidate site-specific values to
     simplify configuration for users.

  #. Finally, the user's own ``$HOME/.pygcam.cfg`` is read if it exists; otherwise the
     file is created with the initial contents being a commented-out version of
     ``pygcam/etc/system.cfg``. This provides a handy reference to the available parameters
     and their default values.

The values in each successive configuration file override default values for
variables of the same name that are set in files read earlier. Values can also be set in
project-specific sections whose names should match project names defined in the
:doc:`project-xml` file. Thus when a user specifies a project to operate on, either on the
command-line to :doc:`gcamtool` or as the value of ``GCAM.DefaultProject`` in ``$HOME/.pygcam.cfg``,
the project-specific values override any values set in ``[DEFAULT]`` sections.

For example, consider the following values in ``$HOME/.pygcam.cfg``:

  .. code-block:: cfg

     [DEFAULT]
     GCAM.Root = %(Home)s/GCAM

     [Project1]
     GCAM.Root = /other/location/GCAM

     [OtherProject]
     # no value set here for GCAM.ROOT

The default value for ``GCAM.Root`` is ``%(Home)s/GCAM``. This value is used for the
project ``OtherProject`` since no project-specific value is defined, but the project
``Project1`` overrides this with the value ``/other/location/GCAM``.

The available parameters and their default values are described below.


Editing the user configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can edit the configuration file, ``$HOME/.pygcam.cfg``, with any editor capable of
working with plain text, i.e., not a word-processor such as Word. Use the command
``gt config -e`` to invoke an editor on the configuration file.

The command invoked by ``gt config -e`` to edit the config file is the value of the
configuration parameter ``GCAM.TextEditor``, which defaults to a system-appropriate
value shown in the table below. Set this value in the configuration file to invoke
your preferred editor. For example, if you prefer the ``emacs`` editor, you can add
this line to ``~/.pygcam.cfg``:

  .. code-block:: cfg

     GCAM.TextEditor = emacs

Then, invoking the command:

  .. code-block:: bash

     gt config -e

will cause the command ``emacs $HOME/.pygcam.cfg`` to be run.

Referencing configuration variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A powerful feature of the configuration system is that variables can be defined in
terms of other variables. The syntax for referencing the value of a variable is to
precede the variable name with ``%(`` and follow it with ``)s``. This to reference
variable ``GCAM.QueryDir``, you would write ``%(GCAM.QueryDir)s``. Note that variable
names are case-sensitive.

Note that variable values are substituted when a variable's value is requested, not
when the configuration file is read. The difference is that if variable ``A`` is
defined in terms of variable ``B``, (e.g., ``A = %(B)s/something/else``), you can
subsequently change ``B`` and the value of ``A`` will reflect this when ``A`` is
accessed by ``pygcam``.

.. note::

   When de-referencing a variable in the config file, you must include the
   trailing 's' after the closing parenthesis, or a Python exception will be raised.

Validating configuration settings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
``pygcam`` requires that certain configuration variables be set. The table
below shows key variables, indicating whether they are required or optional,
and whether their value must be a file or directory.

+----------------------+----------+-----------+
| Variable name        | Required | Type      |
+======================+==========+===========+
| GCAM.SandboxRoot     | yes      | directory |
+----------------------+----------+-----------+
| GCAM.ProjectRoot     | yes      | directory |
+----------------------+----------+-----------+
| GCAM.QueryDir        | yes      | directory |
+----------------------+----------+-----------+
| GCAM.MI.Dir          | yes      | directory |
+----------------------+----------+-----------+
| GCAM.RefWorkspace    | yes      | directory |
+----------------------+----------+-----------+
| GCAM.TempDir         | yes      | directory |
+----------------------+----------+-----------+
| GCAM.ProjectXmlFile  | yes      | file      |
+----------------------+----------+-----------+
| GCAM.RefConfigFile   | yes      | file      |
+----------------------+----------+-----------+
| GCAM.MI.JarFile      | yes      | file      |
+----------------------+----------+-----------+
| GCAM.UserTempDir     | no       | directory |
+----------------------+----------+-----------+
| GCAM.RegionMapFile   | no       | file      |
+----------------------+----------+-----------+
| GCAM.RewriteSetsFile | no       | file      |
+----------------------+----------+-----------+

The ``config`` sub-command provides a limited amount of validation by checking
that all required and optional variables are set to reasonable values. To check
the config file, run the command ``gt config -t``. You can specify a project to
check that project's variables. For example, I can test the values set for project
``Paper1`` with the following command, shown with command output:

  .. code-block:: bash

     $ gt -P paper1 config -t
     OK: GCAM.SandboxRoot = /Users/rjp/ws
     OK: GCAM.SandboxDir = /Users/rjp/ws/paper1
     OK: GCAM.ProjectRoot = /Users/rjp/bitbucket
     OK: GCAM.ProjectDir = /Users/rjp/bitbucket/paper1
     OK: GCAM.QueryDir = /Users/rjp/bitbucket/paper1/queries
     OK: GCAM.MI.Dir = /Users/rjp/GCAM/current/ModelInterface
     OK: GCAM.RefWorkspace = /Users/rjp/GCAM/current/Main_User_Workspace
     OK: GCAM.TempDir = /tmp
     OK: GCAM.UserTempDir = /Users/rjp/tmp
     OK: GCAM.ProjectXmlFile = /Users/rjp/bitbucket/paper1/etc/project.xml
     OK: GCAM.RefConfigFile = /Users/rjp/GCAM/current/Main_User_Workspace/exe/configuration_ref.xml
     OK: GCAM.MI.JarFile = /Users/rjp/bitbucket/gcam-proj/ModelInterface/ModelInterface.jar
     OK: GCAM.RegionMapFile = /Users/rjp/bitbucket/paper1/etc/Regions.txt


Location of GCAM program and data files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The configuration variable ``GCAM.RefWorkspace`` must point to a directory
structured like the standard GCAM ``Main_User_Workspace``, with sub-directories
for ``input``, ``output``, ``libs``, and ``exe``. These files are the reference
files used by :doc:`gcamtool` to set up "sandbox" workspaces in which to run GCAM.

``pygcam`` does not run GCAM in the reference workspace's ``exe`` directory;
it uses the files there to create new workspaces as required. Creating separate
workspaces for each scenario allows multiple scenarios to be run simultaneously
without contention for the XML database which is created at the end of the model
run. This is essential when running on a computing cluster.

The variable ``GCAM.MI.Dir`` should point to a directory holding the ModelInterface
program. This is used to execute batch queries to extract results from GCAM.


Default values
^^^^^^^^^^^^^^^
The system default values are provided in the ``pygcam`` package in the file
``pygcam/etc/system.cfg``, which is listed below. In addition to these values,
several values are read from platform-specific files, as noted above. These
values are shown below.

For Windows:
~~~~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../pygcam/etc/Windows.cfg
   :language: cfg

For Macintosh OS X:
~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../pygcam/etc/Darwin.cfg
   :language: cfg

Default configuration variable dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The following figure shows variable dependencies according to the default
definitions. Variables lower in the figure depend on those above them. Thus,
if you change a variable with "descendants", you affect the definition of
everything below it in the figure.

  .. image:: images/ConfigVarStructure.jpg

The system defaults file
~~~~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../pygcam/etc/system.cfg
   :language: cfg
