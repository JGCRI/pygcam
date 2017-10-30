``pygcam.subcommand``
================================

Gcamtool can be extended using plug-ins, i.e., python modules that
are loaded on demand into gcamtool. The ``subcommand`` module provides
the interface for subcommand plug-ins.

Each plug-in is implemented as a Python module in a file named
``{subcommand}_plugin.py``, where ``{subcommand}`` matches the
name of the sub-command specified in the ``__init__`` method,
described below.

The plug-in module must provides a class that
is a subclass of the abstract base class ``SubcommandABC``, and must
define define three methods: ``__init__``, ``addArgs``, and ``run``.

  - The ``__init__`` method should define keyword arguments that provide the
    text used when the help option is specified by the user.

  - The ``addArgs`` method should define command-line arguments specific
    to the sub-command, and return the parser instance, which allows Sphinx
    to  generate command-line documentation (i.e., these web pages.)

  - The  ``run`` method implements the desired plug-in functionality.

The plug-in file must also identify the plug-in class, either by defining the
variable ``PluginClass`` and assigning to it the class that implements the
sub-command, or by simply naming the class ``Plugin``, obviating the need to
assign to the PluginClass variable.

Plugins can be stored in any directory or directories that are on the
"plugin path" set using the config file parameter ``GCAM.PluginPath``. For
example, you might create a file ``foo_plugin.py`` in the directory ``~/plugins``.
You would then set ``GCAM.PluginPath = %(Home)s/plugins`` in the ``~/.pygcam.cfg``
configuration file.

Plugins are loaded by ``gt`` on demand, i.e., when the plugin is referenced
on the ``gt`` command-line, or implicitly when all steps are run. They are
also loaded when the help (``--help`` or ``-h``) options are specified, so
that the plugins appear in the generated documentation.

The following template can be used to create new sub-commands. See also
``pygcam/etc/pluginTemplate.py``, which contains the code shown here.

.. literalinclude:: ../../pygcam/etc/pluginTemplate.py
   :language: python

API
---

.. automodule:: pygcam.subcommand
   :members:

