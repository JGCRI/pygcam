from pygcam.plugin import PluginBase

class DiffCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(DiffCommand, self).__init__('diff', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass


PluginClass = DiffCommand
