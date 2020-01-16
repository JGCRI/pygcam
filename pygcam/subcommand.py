'''
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from abc import ABCMeta, abstractmethod

# Fixes help strings to display properly with sphinx-argparse
def clean_help(s):
    lines = s.splitlines()
    return ' '.join(map(lambda s: s.strip(), lines))

# class OptionInfo(object):
#     """
#     Stores information about a single sub-command option that is used to
#     construct the web-based GUI for the sub-command.
#     """
#     def __init__(self, display=True, choiceFunc=None, multiple=False):
#         """
#         Initialize an OptionInfo instance.
#
#         :param display: (bool) whether this option should be displayed in the GUI
#         :param choiceFunc: (callable) function to return a list of options to display
#         :param multiple: (bool) whether multiple values can be returned
#         :param commaList: (bool) whether values should be returned as a comma-delimited string
#         """
#         self.display = display
#         self.choiceFunc = choiceFunc
#         self.multiple = multiple

class SubcommandABC(object):
    """
    Abstract base class for sub-commands. Defines the protocol expected by ``gt``
    for defining sub-commands. Plugin files should be named ``'*_plugin.py'`` and must
    define a subclass of ``SubcommandABC``. To allow the class to be identified, it can be
    named ``Plugin`` or the global variable ``PluginClass`` can identify the class.

    :param name: (str) the name of the sub-command
    :param subparsers: an object returned by argparse's ``parser.add_subparsers()``
    :param kwargs: (dict) keywords to pass to the the call to argparse's
       ``subparsers.add_parser(name, **kwargs)``, e.g., to pass `help` or
       `documentation` strings.
    :param group: (str) the name of the GUI group to assign this plug-in to.
    :param label: (str) the label to use on the GUI to reference this plug-in.
       Defaults to the sub-command name, capitalized.
    :param guiSuppress: (bool) if True, do not display this sub-command in the GUI.
    """
    __metaclass__ = ABCMeta

    Instances = {}  # SubCommand instances keyed by name
    Parsers = {}    # SubCommand parsers keyed by name

    @classmethod
    def getInstance(cls, name):
        return SubcommandABC.Instances.get(name)

    # Deprecated?
    @classmethod
    def getParser(cls, name):
        obj = cls.getInstance(name)
        return obj.parser

    def __init__(self, name, subparsers, kwargs, group=None, label=None,
                 guiSuppress=False):
        self.name = name
        self.label = label or name.capitalize()  # label to display in GUI
        self.parser = parser = subparsers.add_parser(self.name, **kwargs)
        self.Instances[self.name] = self

        self.optionInfo = {}    # OptionInfo instances keyed by option name
        self.guiSuppress = guiSuppress

        # For grouping commands in the GUI. Set this in subclass' addArgs().
        # Set to None if the command should not be presented in the GUI.
        # Note: 'group' can be set as standalone var or in guiInfo['group'].
        self.group = group or 'main'
        #self.group = group or (guiInfo.get('group') if guiInfo else 'main')

        self.addArgs(parser)

    def __str__(self):
        clsName = type(self).__name__
        return "<%s name=%s group=%s>" % (clsName, self.name, self.group)

    def getOptionInfo(self, name):
        return self.optionInfo.get(name)

    def setOptionInfo(self, name, optionInfo):
        self.optionInfo[name] = optionInfo

    def getGroup(self):
        return self.group

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
