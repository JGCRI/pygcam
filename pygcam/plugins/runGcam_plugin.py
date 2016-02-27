from pygcam.plugin import PluginBase

class GcamCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Run the GCAM executable''',
                  'description' : '''A more detailed description'''}
        super(GcamCommand, self).__init__('gcam', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass

PluginClass = GcamCommand
