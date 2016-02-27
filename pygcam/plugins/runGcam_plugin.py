from pygcam.plugin import PluginBase

class GcamCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(GcamCommand, self).__init__('gcam', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass

PluginClass = GcamCommand
