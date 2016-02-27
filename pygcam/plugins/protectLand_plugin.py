from pygcam.plugin import PluginBase

class ProtectCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(ProtectCommand, self).__init__('protect', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        print 'Run "protect"'

PluginClass = ProtectCommand
