Configuration System
=============================

The ``pygcam`` scripts and libraries rely on a configuration file to:

  * define the location of essential and optional files,
  * allow the user to set defaults for many command-line arguments to scripts, and
  * define both global default and project-specific values for all parameters.

The configuration file and variables are described below.

.. seealso::
   Use the :ref:`gt init <init>` command to initialize your configuration file.

   Usage of the ``config`` sub-command is described on the :ref:`gt config <config>`
   page. See :doc:`pygcam.config` for documentation of the API to the configuration system.

   ``pygcam`` uses the Python :mod:`ConfigParser` package. See the documentation
   there for more details.


Configuration file sections
----------------------------
The configuration file is divided into sections indicated by a name within square brackets.
All variable declarations following a section declaration, until the next section
declaration (if any) appear in the declared section.

Default section
^^^^^^^^^^^^^^^^^^^^^^
Default values are defined in the ``[DEFAULT]`` section. When ``pygcam`` requests the value
of a variable from a project section (see below), the default value is returned if the
variable is not defined in the project section. Variables whose values apply to multiple
projects can be defined conveniently in the ``[DEFAULT]`` section.

All pre-defined ``pygcam`` variables are defined in the ``[DEFAULT]`` section,
allowing them to be overridden on a project-by-project basis.

Project sections
^^^^^^^^^^^^^^^^^^^^^^
Each project must have its own section. For example, to setup a project called,
say, "myproj", I would create the section ``[myproj]``. Following this, I would define
variables particular to this project, e.g., where to find the files defining scenarios,
queries, and so on.

Note that the :ref:`new <new>` sub-command will set up the structure for a new
project and (optionally) add a section to the user's config file for the named project.


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

  #. Finally, the user's configuration file is read if it exists; otherwise the
     file is created with the initial contents being a commented-out version of
     ``pygcam/etc/system.cfg``. This provides a handy reference to the available parameters
     and their default values.

     * On Linux and OS X, the user's configuration file is found in ``$HOME/.pygcam.cfg``

     * On Windows, the file ``.pygcam.cfg`` will be stored in the directory identified
       by the first of the following environment variables defined to have a non-empty
       value: ``PYGCAM_HOME``, ``HOMESHARE``, and ``HOMEPATH``. The
       first variable, ``PYGCAM_HOME`` is known only to pygcam, while at least one of
       the other two should be set by Windows.

     * In all cases, the directory in which the configuration file is located is
       assigned to the pygcam configuration variable ``Home``.

The values in each successive configuration file override default values for
variables of the same name that are set in files read earlier. Values can also be set in
project-specific sections whose names should match project names defined in the
:doc:`project-xml` file. Thus when a user specifies a project to operate on, either on the
command-line to :doc:`gcamtool` or as the value of ``GCAM.DefaultProject`` in ``$HOME/.pygcam.cfg``,
the project-specific values override any values set in ``[DEFAULT]`` sections.

For example, consider the following values in ``$HOME/.pygcam.cfg``:

.. code-block:: cfg

     [DEFAULT]
     GCAM.RefWorkspace = %(Home)s/GCAM/gcam-v4.3

     [Project1]
     GCAM.RefWorkspace = /other/location/GCAM/gcam-v4.4

     [OtherProject]
     # no value set here for GCAM.RefWorkspace

The default value for ``GCAM.RefWorkspace`` is ``%(Home)s/GCAM/gcam-v4.3``. This value is
used for the project ``OtherProject`` since no project-specific value is defined, but the project
``Project1`` overrides this with the value ``/other/location/GCAM/gcam-v4.4``.

The available parameters and their default values are described below.


Editing the user configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can edit the configuration file, ``$HOME/.pygcam.cfg``, with any editor capable of
working with plain text, i.e., not a word-processor such as Word. Use the command
``gt config -e`` to invoke an editor on the configuration file.

The command invoked by ``gt config -e`` to edit the config file is the value of the
configuration parameter ``GCAM.TextEditor``, which defaults to a system-appropriate
value shown in the table below. Set this value in the configuration file to invoke
your preferred editor.

For example, if you prefer the ``emacs`` editor on a Mac, you can add this line to
``~/.pygcam.cfg`` to cause the Finder to open the file using the emacs application:

.. code-block:: cfg

   GCAM.TextEditor = open -a emacs

Or, to edit the config file using the PyCharm app, use this:

.. code-block:: cfg

   GCAM.TextEditor = open -a PyCharm

If the editor command is not found on your execution ``PATH``, you can specify the
full pathname. Use quotes around the path if it includes spaces, as in the examples
below.

To use Notepad++ on Windows, use the following (adjusted as necessary for your
installation location):

.. code-block:: cfg

     GCAM.TextEditor = "C:/Program Files/Notepad++/notepad++.exe"

To use PyCharm, use the following -- again, adjusted to match your installation
location:

.. code-block:: cfg

     GCAM.TextEditor  = "C:/Program Files/JetBrains/PyCharm 2018.1.4/bin/pycharm64.exe"


Invoking the command:

.. code-block:: sh

     gt config -e

will cause the editor to be invoked on your configuration file.


Referencing configuration variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A powerful feature of the configuration system is that variables can be defined in
terms of other variables. The syntax for referencing the value of a variable is to
precede the variable name with ``%(`` and follow it with ``)s``. Thus to reference
variable ``GCAM.QueryDir``, you would write ``%(GCAM.QueryDir)s``.

.. note::

   When referencing a variable in the config file, you must include the
   trailing ``s`` after the closing parenthesis, or a Python exception will be raised.

   Also note that variable names are case-sensitive.

Variable values are substituted when a variable's value is requested, not
when the configuration file is read. The difference is that if variable ``A`` is
defined in terms of variable ``B``, (e.g., ``A = %(B)s/something/else``), you can
subsequently change ``B`` and the value of ``A`` will reflect this when ``A`` is
accessed by ``pygcam``.

All known variables are given default values in the pygcam system files. Users
can create variables in any of the user controlled config files, if desired.

Environment variables
~~~~~~~~~~~~~~~~~~~~~~~
All defined environmental variables are loaded into the config parameter space before
reading any configuration files, and are accessible with a prefix of ``$``, as in a
UNIX shell. For example, to reference the environment variable ``SCRATCH``, you can
use ``%($SCRATCH)s``.


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
that all required and optional variables are set to reasonable values. You can
do a basic (not foolproof) check that the required files and directories exist
using the command:

.. code-block:: sh

     gt config -t

which will print out a listing of files and their status.

You can also specify a project to check that project's variables. For example,
I can test the values set for project ``myproj`` with the following command,
shown with command output:

.. code-block:: sh

     $ gt +P myproj config -t

    OK: GCAM.SandboxRoot = /people/plev920/ws
    OK: GCAM.SandboxDir = /people/plev920/ws/myproj/
    OK: GCAM.ProjectRoot = /people/plev920/bitbucket
    OK: GCAM.ProjectDir = /people/plev920/bitbucket/myproj
    OK: GCAM.QueryDir = /people/plev920/bitbucket/myproj/queries
    OK: GCAM.MI.Dir = /people/plev920/GCAM/current/input/gcam-data-system/_common/ModelInterface/src
    OK: GCAM.RefWorkspace = /people/plev920/GCAM/current
    OK: GCAM.TempDir = /pic/scratch/plev920/tmp
    OK: GCAM.UserTempDir = /people/plev920/tmp
    OK: GCAM.ProjectXmlFile = /people/plev920/bitbucket/myproj/etc/project.xml
    OK: GCAM.RefConfigFile = /people/plev920/GCAM/current/exe/configuration_ref.xml
    OK: GCAM.MI.JarFile = /people/plev920/GCAM/current/input/gcam-data-system/_common/ModelInterface/src/ModelInterface.jar
    OK: GCAM.RewriteSetsFile = /people/plev920/bitbucket/myproj/etc/rewriteSets.xml


Location of GCAM program and data files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The configuration variable ``GCAM.RefWorkspace`` must point to a directory
structured like the standard GCAM workspace, with sub-directories
for ``input``, ``output``, ``libs``, and ``exe``. These files are the reference
files used by :doc:`gcamtool` to set up "sandbox" workspaces in which to run GCAM.

``pygcam`` does not run GCAM in the reference workspace's ``exe`` directory;
it uses the files there to create new workspaces as required. Creating separate
workspaces for each scenario allows multiple scenarios to be run simultaneously
without contention for the XML database which is created at the end of the model
run. This is essential when running on a computing cluster.

The variable ``GCAM.MI.Dir`` should point to a directory holding the ModelInterface
program. This is used to execute batch queries to extract results from GCAM. By
default, this location is computed from the ``GCAM.RefWorkspace``, but you can
change it if necessary, e.g., if you're using a customized version of ModelInterface.


Default configuration variables and values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The system default values are provided in the ``pygcam`` package in the file
``pygcam/etc/system.cfg``, which is listed below. In addition to these values,
several values are read from platform-specific files, as noted above. These
values are shown below.

For Windows:
~~~~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../pygcam/etc/Windows.cfg
   :language: cfg

For MacOS:
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


.. _logging:

Configuring the logging system
-------------------------------

Setting logging verbosity
^^^^^^^^^^^^^^^^^^^^^^^^^^
When the :doc:`gcamtool` runs, or when pygcam functions are called from your
own code, diagnostic and informational messages are printed. You can control
the level of output by setting the ``GCAM.LogLevel`` in your ``.pygcam.cfg``
file. (See :py:mod:`logging` for further details.)

The simplest setting is just one of the following values, in order of
decreasing verbosity: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, and ``FATAL``.
This will apply to all pygcam modules.

You can also specify verbosity by module, by specifying a module name and the
level for that module as a comma-separated list of "module:level" strings,
e.g.,:

.. code-block:: cfg

     GCAM.LogLevel = WARN, .utils:INFO, .scenarioSetup:DEBUG, CI_plugin:INFO, \
       .mcs.worker:DEBUG,, myProj.writeFuncs:DEBUG

In this example, the default level is set to ``WARN``, and three pygcam modules
have their levels set: pygcam.utils is set to INFO, pygcam.scenarioSetup is set
to DEBUG, and pygcam.mcs.worker is set to DEBUG. A user's plugin can also use
the logging system. This example sets logging levels for the user's
``CI_Plugin`` and ``myProj.writeFuncs`` modules.

Console / file logs and message formatting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Note that the module name is shown in the console log messages. Setting
``GCAM.LogLevel`` to DEBUG produces the maximum number of log messages;
setting it to FATAL minimizes message verbocity.

Other relevant variables are shown here with their default values:

.. code-block:: cfg

    # If set, application logger messages are written here. Note that
    # this is different than the GCAM.BatchLogFile for batch job output.
    GCAM.LogFile = %(GCAM.SandboxRoot)s/log/gt.log

    # Show log messages on the console (terminal)
    GCAM.LogConsole = True

    # Format strings for log files and console messages. Note doubled
    # '%%' required here around logging parameters to avoid attempted
    # variable substitution within the config system.
    GCAM.LogFileFormat    = %%(asctime)s %%(levelname)s %%(name)s:%%(lineno)d %%(message)s
    GCAM.LogConsoleFormat = %%(levelname)s %%(name)s: %%(message)s
