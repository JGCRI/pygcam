from pygcam.plugin import PluginBase

class ProjectCommand(PluginBase):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Help text'''}
        super(ProjectCommand, self).__init__('project', kwargs, subparsers)

    def addArgs(self):
        pass

    def run(self, args):
        pass

PluginClass = ProjectCommand
