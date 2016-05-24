``pygcam.config``
=============================

The ``pygcam`` scripts and libraries rely on a configuration file to:

  * define the location of essential and optional files,
  * allow the user to set defaults for many command-line arguments to scripts, and
  * define both global default and project-specific values for all parameters

The ``pygcam.config`` module provides access to configuration parameters. The
configuration file and the API to access it are described below.

.. _pygcam-cfg:

The configuration files
-----------------------
There are three configuration files, two of which the user can modify:

  1. First, ``system.cfg`` is read from within the ``pygcam`` package. This defines all
     known config variables and provides their default values as described below.
     *This file should not be modified by the user.*

  2. Next, if the environment variable ``PYGCAM_SITE_CONFIG`` is defined, it should
     refer to a configuration file in the same format as the ``system.cfg``. This overrides
     system defaults to provide site-level default values. The site configuration file is
     optional and may not be needed in most cases. It is provided  to allow an administrator
     to set site-specific values for a set of users to simplify configuration.

  3. Finally, ``$HOME/.pygcam.cfg`` is read if it exists; otherwise the file is created
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


Editing the configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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

  .. code-block:: shell

     gt config -e

will cause the command ``emacs $HOME/.pygcam.cfg`` to be run.

Default values
^^^^^^^^^^^^^^^
The sytem default values are provided in the ``pygcam`` package in a file called
``pygcam/etc/system.cfg``, which is listed below.

In addition to these values, five values are set dynamically based on the operating
system being used, as shown in the table below.

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
| GCAM.JarFIle          | *see text below*                                     |
+-----------------------+------------+-----------------+------------+----------+

The variable ``GCAM.JarFile`` is set to ``%(GCAM.ModelInterface)s/ModelInterface.jar``
on all operating systems except on Mac OS X where it is set to
``%(GCAM.ModelInterface)s/ModelInterface.app/Contents/Resources/Java/ModelInterface.jar``.


  .. note::

    When de-referencing a variable in the config file, you must include the
    trailing 's' after the closing parenthesis, or a Python exception will be raised.


  .. literalinclude:: ../../pygcam/etc/system.cfg
     :language: cfg

API
---

.. automodule:: pygcam.config
   :members:
