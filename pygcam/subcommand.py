from abc import ABCMeta, abstractmethod

class SubcommandABC(object):
    """
    Abstract base class for sub-commands. Defines the protocol expected by ``gcamtool``
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
        self.parser = subparsers.add_parser(self.name, **kwargs)
        self.Parsers[self.name] = self.parser
        self.addArgs(self.parser)

    @abstractmethod
    def addArgs(self, parser):
        pass

    @abstractmethod
    def run(self, args):
        """
        Perform the function intended by the ``SubcommandABC`` subclass. This function
        is invoked by ``gcamtool`` on the ``SubcommandABC`` instance whose name matches the
        given sub-command.

        :param args: the argument dictionary
        :return: nothing
        """
        pass
