``pygcam.config``
=============================

The ``pygcam`` scripts and libraries rely on a configuration file to:

  * define the location of essential and optional files,
  * allow the user to set defaults for many command-line arguments to scripts, and
  * define both global default and project-specific values for all parameters

The ``pygcam.config`` module provides access to configuration parameters. The
configuration file and the API to access it are described below.

.. seealso::
   Usage of the ``config`` sub-command is described on the
   :ref:`gt config <config-label>` page.

.. _pygcam-cfg:

The configuration files
-----------------------
There are three configuration files, two of which the user can modify:

  #. First, ``system.cfg`` is read from within the ``pygcam`` package. This defines all
     known config variables and provides their default values as described below.
     *This file should not be modified by the user.*

  #. Next, if the environment variable ``PYGCAM_SITE_CONFIG`` is defined, it should
     refer to a configuration file in the same format as the ``system.cfg``. This overrides
     system defaults to provide site-level default values. The site configuration file is
     optional and may not be needed in most cases. It is provided  to allow an administrator
     to set site-specific values for a set of users to simplify configuration.

  #. Finally, ``$HOME/.pygcam.cfg`` is read if it exists; otherwise the file is created
     with the initial contents being a commented-out version of ``system.cfg``, which
     provides a handy reference to the available parameters and their default values.

Values in ``$HOME/.pygcam.cfg`` override defaults set in either of the ``system.cfg`` or
site config files and become the default for all projects. Values can also be set in
project-specific sections with names chosen by the user. This name should match the name
of the corresponding project in the :doc:`project-xml` file.

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Within the configuration file, variables are often defined in terms of other variables.
The syntax for referencing the value of a variable is the precede the variable name with
``%(`` and follow it with ``)s``. This to reference variable ``GCAM.QueryDir``, you
would write ``%(GCAM.QueryDir)``. Note that variable names are case-sensitive.

Variables' values are substituted when a variable's value is requested, not when the
variable is defined. The difference is that if variable ``A`` is defined in terms of
variable ``B``, (e.g., ``A = %(B)s/something/else``), you can subsequently change
``B`` and the value of ``A`` will show this when ``A`` is accessed by ``pygcam``.

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

     $ gt -P Paper1 config -t
     OK: GCAM.SandboxRoot = /Users/rjp/ws/paper1
     OK: GCAM.ProjectRoot = /Users/rjp/bitbucket/paper1
     OK: GCAM.QueryDir = /Users/rjp/bitbucket/paper1/queries
     OK: GCAM.ModelInterface = /Users/rjp/GCAM/current/ModelInterface
     OK: GCAM.RefWorkspace = /Users/rjp/GCAM/current/Main_User_Workspace
     OK: GCAM.TempDir = /tmp
     OK: GCAM.UserTempDir = /Users/rjp/tmp
     OK: GCAM.ProjectXmlFile = /Users/rjp/bitbucket/paper1/etc/project.xml
     OK: GCAM.RefConfigFile = /Users/rjp/GCAM/current/Main_User_Workspace/exe/configuration_ref.xml
     OK: GCAM.JarFile = /Users/rjp/bitbucket/gcam-proj/ModelInterface/ModelInterface.jar
     OK: GCAM.RegionMapFile = /Users/rjp/bitbucket/paper1/etc/Regions.txt

Location of GCAM program and data files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The configuration variable ``GCAM.RefWorkspace`` must point to a directory
structured like the standard GCAM ``Main_User_Workspace``, with sub-directories
for ``input``, ``output``, ``libs``, and ``exe``.

The variable ``GCAM.ModelInterface`` should point to a directory holding the
ModelInterface program.

Note that ``pygcam`` does not run GCAM in the reference workspace's ``exe`` directory;
it uses the files there to create new workspaces as required.
Creating separate workspaces for each scenario allows multiple
scenarios to be run simultaneously without contention for the XML database
which is created at the end of the model run.

Default values
^^^^^^^^^^^^^^^
The system default values are provided in the ``pygcam`` package in a file called
``pygcam/etc/system.cfg``, which is listed below.

In addition to these values, several values are set dynamically based on the
operating system being used, as shown in the tables below.

+-----------------------+------------+-----------------+------------+----------+
| Variable              | Linux      | Mac OS X        | Windows    | Other    |
+=======================+============+=================+============+==========+
| Home                  | $HOME      | $HOME           | %HOMEPATH% | $HOME    |
+-----------------------+------------+-----------------+------------+----------+
| GCAM.Executable       | ./gcam.exe | Release/objects | gcam.exe   | gcam.exe |
+-----------------------+------------+-----------------+------------+----------+
| GCAM.UseVirtualBuffer | True       | False           | False      | False    |
+-----------------------+------------+-----------------+------------+----------+
| GCAM.TextEditor       | vi         | open -e         | notepad.exe| vi       |
+-----------------------+------------+-----------------+------------+----------+

In addition, the variable ``GCAM.JarFile`` provides the location of the jar file.
The variable is initialized differently on Windows, OS X, and Linux as follows:

+---------+---------------------------------------------------------------------------------------+
| System  | Default definition of GCAM.JarFile                                                    |
+=========+=======================================================================================+
| Windows | %(GCAM.ModelInterface)s/ModelInterface.jar                                            |
+---------+---------------------------------------------------------------------------------------+
| Linux   | %(GCAM.ModelInterface)s/ModelInterface.jar                                            |
+---------+---------------------------------------------------------------------------------------+
| OS X    | %(GCAM.ModelInterface)s/ModelInterface.app/Contents/Resources/Java/ModelInterface.jar |
+---------+---------------------------------------------------------------------------------------+

The system defaults file
~~~~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../pygcam/etc/system.cfg
   :language: cfg

---------------------------------------------------------

API
---

.. automodule:: pygcam.config
   :members:
