``pygcam.subcommand``
================================

The ``subcommand`` module provides the interface for subcommand plug-ins.
Each plugin must provide a class that is a subclass of SubcommandABC, which
is an abstract base class. The plugin class must define an ``__init__``
and ``run`` methods, as described below.

Plugins can be stored in any directory or directories that are on the
"plugin path" set using the config file parameter ``GCAM.PluginPath``. For
example, you might create a file ``foo_plugin.py`` in the directory ``~/plugins``.
You would then set ``GCAM.PluginPath = %(Home)s/plugins`` in the ``~/.pygcam.cfg``
configuration file.

API
---

.. automodule:: pygcam.subcommand
   :members:

