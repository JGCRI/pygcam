``pygcam.subcommand``
================================

The ``subcommand`` module provides the interface for subcommand plug-ins.
Each plugin must provide a class that is a subclass of ``SubcommandABC``, which
is an abstract base class. The plugin class must define an ``__init__``
and ``run`` methods, as described below.

Plugins can be stored in any directory or directories that are on the
"plugin path" set using the config file parameter ``GCAM.PluginPath``. For
example, you might create a file ``foo_plugin.py`` in the directory ``~/plugins``.
You would then set ``GCAM.PluginPath = %(Home)s/plugins`` in the ``~/.pygcam.cfg``
configuration file.

The following template can be used to create new sub-commands. (See also
``pygcam.pluginTemplate.py``, which contains the code shown here.)

  .. code-block:: python

     from pygcam.subcommand import SubcommandABC
     from pygcam.log import getLogger

     _logger = getLogger(__name__)
     VERSION = "0.0"

     class MyNewCommand(SubcommandABC):
         def __init__(self, subparsers):
             kwargs = {'help' : '''Short help text for main driver'''}

             # The first argument is the name of the new sub-command
             super(MyNewCommand, self).__init__('XXX', subparsers, kwargs)

         # process command-line arguments for this sub-command
         def addArgs(self):
             parser = self.parser

             parser.add_argument('-n', '--number', type=int, default=0,
                                 help='''A number to demonstrate a command line arg''')

             parser.add_argument('-V', '--version', action='version',
                                 version='%(prog)s ' + VERSION)

             return parser

         def run(self, args, tool):
            # implement the sub-command here
             pass

      # An alternative to naming the class 'Plugin' is to assign the class to PluginClass
      PluginClass = MyNewCommand


API
---

.. automodule:: pygcam.subcommand
   :members:

