from pygcam.plugin import PluginBase


class SetupCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(SetupCommand, self).__init__('setup', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass


PluginClass = SetupCommand
