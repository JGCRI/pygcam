'''
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from abc import ABCMeta, abstractmethod

class SubcommandABC(object):
    """
    Abstract base class for sub-commands. Defines the protocol expected by ``gt``
    for defining sub-commands. Plugin files should be named ``'*_plugin.py'`` and must
    define a subclass of ``SubcommandABC``. To allow the class to be identified, it can be
    named ``Plugin`` or the global variable ``PluginClass`` can identify the class.

    :param name: (str) the name of the sub-command
    :param kwargs: (dict) keywords to pass to the the call to argparse's
       ``subparsers.add_parser(name, **kwargs)``, e.g., to pass `help` or
       `documentation` strings.
    :param subparsers: an object returned by argparse's ``parser.add_subparsers()``
    """
    __metaclass__ = ABCMeta

    Parsers = {}

    @classmethod
    def getParser(cls, name):
        return cls.Parsers[name]

    def __init__(self, name, subparsers, kwargs):
        self.name = name
        self.parser = parser = subparsers.add_parser(self.name, **kwargs)
        self.Parsers[self.name] = parser
        self.addArgs(parser)

    @abstractmethod
    def addArgs(self, parser):
        """
        Add command-line arguments to the given `parser`. (This is an
        abstract method that must be implemented in the subclass.)

        :param parser: the sub-parser associated with this sub-command.

        :return: the populated parser
        """
        pass

    @abstractmethod
    def run(self, args, tool):
        """
        Perform the function intended by the ``SubcommandABC`` subclass. This function
        is invoked by ``gt`` on the ``SubcommandABC`` instance whose name matches the
        given sub-command. (This is an  abstract method that must be implemented in
        the subclass.)

        :param args: the argument dictionary
        :param tool: the GcamTool instance for the main command
        :return: nothing
        """
        pass
