'''
.. Plug-in management system for sub-commands to gcamtool

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
from glob import glob
from abc import ABCMeta, abstractmethod
from pygcam.common import loadModuleFromPath
from pygcam.error import PygcamException

class PluginBase(object):
    """
    Abstract base class for sub-commands. Defines the protocol expected by gcamtool
    for defining sub-commands.
    """
    __metaclass__ = ABCMeta

    Instances = {}

    @classmethod
    def getInstance(cls, name):
        return cls.Instances[name]

    def __init__(self, name, kwargs, subparsers):
        self.name = name
        self.parser = subparsers.add_parser(self.name, **kwargs)
        self.Instances[self.name] = self.parser
        self.addArgs()

    @abstractmethod
    def addArgs(self):
        pass

    @abstractmethod
    def run(self, args):
        """
        This is the function invoked by this SubCommand instance.

        :param args: the argument dictionary
        :return: nothing
        """
        pass


class PluginManager(object):
    def __init__(self, dirs=[], path=None):
        items = path.split(';') if path else []

        moduleDir = os.path.dirname(os.path.abspath(__file__))
        pluginDir = os.path.join(moduleDir, 'plugins')

        self.pluginDirs = dirs + items + [pluginDir]
        self.plugins = None

    def loadPlugin(self, path):
        """
        Load the plugin at `path`.

        :return: the PluginBase subclass defined in `path`
        """
        def getModObj(mod, name):
            return getattr(mod, name) if name in mod.__dict__ else None

        mod = loadModuleFromPath(path)
        pluginClass = getModObj(mod, 'PluginClass') or getModObj(mod, 'Plugin')
        if not pluginClass:
            raise PygcamException('Neither PluginClass nor class Plugin are defined in %s' % path)

        return pluginClass

    def loadPlugins(self):
        """
        Load plugins from the list of directories calculated in ``__init__``.

        :return: a list of loaded (but not instantiated) BasePlugin subclasses
        """
        plugins = []
        for d in self.pluginDirs:
            pattern = os.path.join(d, '*_plugin.py')
            plugins += map(self.loadPlugin, glob(pattern))

        self.plugins = plugins
        return plugins


if __name__ == '__main__':
    from pygcam.config import getParam, getConfig
    getConfig('DEFAULT')

    pluginPath = getParam('GCAM.PluginPath')
    mgr = PluginManager(path=pluginPath)
    classes = mgr.loadPlugins()
    print("Plugin classes: %s" % classes)
