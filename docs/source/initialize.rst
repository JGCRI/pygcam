Initializing the configuration file
====================================

The :ref:`init <init>` sub-command creates the configuration file
``~/.pygcam.cfg`` and initializes key variables, based on command-line
arguments (if provided) or interactive prompts. The :ref:`init <init>`
sub-command must be run before any other :doc:`gcamtool` command can
be run (with the exception of displaying command-line help).

The information required to initialize your config file includes:

  * **The name of your default project.** This is used to identify the project
    you're currently working on, to avoid having to specify ``+P project_name`` to
    every ``gt`` command. The default project is ``ctax``, assuming you want to
    start by exploring the example project provided.

  * **The location of your GCAM installation.** This can differ by project, but you
    must identify at least one GCAM version to initialize your configuration. (See
    :ref:`Locating GCAM <locating_gcam>`, below.

  * **Where your project information will reside.** By default, project directories
    are assumed to exist under a single "project root". You can, however, set a different
    project directory for any project you wish.

  * **Where your run-time "sandboxes" will reside.** Likewise, you can have a single
    "sandbox" directory under which all your run-time GCAM sandboxes (separate
    GCAM workspaces) reside, or you can set these to specific directories by project.

If you run the ``init`` without identifying all of these directories using command-line
options, ``init`` asks for the missing values interactively.

.. _locating_gcam:

Locating GCAM
--------------

The ``init`` sub-command will look for your GCAM installation directory (which is
assumed to be named either ``gcam-v4.4`` or ``gcam-v4.3``) in these directories, in
order: ``~`` (your home directory), ``~/GCAM``, and ``~/gcam``. All directories are
tried for ``gcam-v4.4`` first, then for ``gcam-v4.3``. You can override this either
on the command-line, or interactively.

Creating the default project
-----------------------------
If you specify ``-c / --create-project``, the structure for the given default project
will be created in the specified project directory. If you specify ``-C / --no-create-project``,
the project will not be created. If you specify neither, you will be asked whether
to create the project. If the project directory already exists, you will be asked whether
to overwrite it.

Note that the :ref:`init <init>`  sub-command creates the project structure by invoking the
:ref:`new <new>` sub-command internally. This creates several directories and copies example
XML files from the ``pygcam`` distribution. The example files define the "ctax" project, which
includes a baseline and 4 carbon tax policies. This is intended as a working starting point.

If you choose not to have ``init`` create the project structure, you can run ``new`` manually.

Example
---------
The simplest approach is to simply run ``gt init`` and respond to the interactive prompts,
as in the following example. As run here, the values presented for where GCAM is installed
and for the sandboxes were accepted (by hitting return).

.. code-block:: sh

 $ gt init
 Enter default project name? (default=ctax)? myproj
 Where is GCAM installed? (default=/Users/rjp/GCAM/gcam-v4.3)?
 Directory in which to create pygcam projects? (default=/Users/rjp/GCAM/projects)? ~/tmp/test/projects
 Directory in which to create pygcam run-time sandboxes? (default=/Users/rjp/tmp/test/sandboxes)?
 Created /Users/rjp/.pygcam.cfg with contents:

 [DEFAULT]
 GCAM.DefaultProject  = myproj
 GCAM.RefWorkspace    = /Users/rjp/GCAM/gcam-v4.3
 GCAM.ProjectRoot     = /Users/rjp/tmp/test/projects
 GCAM.SandboxRoot     = /Users/rjp/tmp/test/sandboxes
 GCAM.RewriteSetsFile = %(GCAM.ProjectDir)s/etc/rewriteSets.xml

 [myproj]
 GCAM.LogLevel = INFO

 Create the project structure for "myproj" (Y/n)? y
 Created project "myproj" in /Users/rjp/tmp/test/projects/myproj

Alternatively, you can provide values on the command-line, which can be useful for writing
your own scripts.

Immediately after running ``gt init`` you can run the baseline and all policy scenarios
in the example project with the command::

    gt run

