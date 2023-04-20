# Copyright (c) 2015 Richard Plevin. See the file COPYRIGHT.txt for details.

from copy import copy
import os
from lxml import etree as ET

from ..config import getParam
from ..log import getLogger
from .simulation import Simulation
from ..XMLFile import XMLFile
from .error import PygcamMcsUserError, PygcamMcsSystemError

_logger = getLogger(__name__)

# The pre-defined sections of GCAM configuration files
COMPONENTS_GROUP = 'ScenarioComponents'
FILES_GROUP   = 'Files'
STRINGS_GROUP = 'Strings'
INTS_GROUP    = 'Ints'
BOOLS_GROUP   = 'Bools'
DOUBLES_GROUP = 'Doubles'

# TBD: Create a version of this that works for non-MCS cases? Could
#   have a superclass for non-MCS with a subclass, say McsConfigFile,
#   that adds stuff for MCS case.
#  class ConfigFile(XMLFile):
#     ivars: project name, scenario name, baseline name, group name, use_group_dir
#  class McsConfigFile(ConfigFile):
#     adds ivars: run_id, sim_id, trial_num, and status
#     adds sim-specific methods
#
# TBD: Note that the functions here seem to duplicate some of XMLEditor. Why?
#
# TBD: create interface to load "most local" version of config file.
class XMLConfigFile(XMLFile):
    '''
    Stores information about a GCAM config.xml file
    '''
    instances = {}  # XMLConfigFile instances keyed by scenario name

    def __init__(self, sim, useCopy=False, useRefConfig=False):
        '''
        Read and cache a GCAM configuration file in self.tree.
        '''
        self.writePath = None
        #self.context = copy(sim.context)   # TBD: any need to copy this?
        self.sim = sim

        original_path = (getParam('GCAM.RefConfigFile') if useRefConfig
                         else sim.scenario_config_file(self.sim.context))

        backup_path = self.getBackupPath()

        # If no backup, or it's outdated, make a copy of the config file for use by runsim
        self.copyOriginal(original_path)

        path = backup_path if useCopy else original_path

        # Default writePath is where we were read from.
        self.writePath = path

        super(XMLConfigFile, self).__init__(path)

    @classmethod
    def decache(cls):
        cls.instances = {}

    @classmethod
    def getConfigForScenario(cls, sim, scenario, useCopy=False):
        '''
        Return the path to the run-tree version of the config file
        for the given scenario.
        '''
        key = (scenario, useCopy)
        try:
            return cls.instances[key]

        except KeyError:
            obj = XMLConfigFile(sim, useCopy=useCopy)
            cls.instances[key] = obj
            return obj

    @classmethod
    def writeAll(cls, sim):
        """
        Write all configuration files to disk.
        """
        for cfg in cls.instances.values():
            configPath = sim.scenario_config_file(cfg.context)
            cfg.write(path=configPath)

    def copyOriginal(self, configPath):
        '''
        Copy config file to xxx/config-original.xml if config.xml is
        newer, so runsim can use the original to generate XML files.
        '''
        import shutil

        if not os.path.exists(configPath):
            raise PygcamMcsSystemError(f"XMLConfigFile: file '{configPath}' does not exist.")

        backupPath = self.getBackupPath()

        # Copy only if the backupPath doesn't exist or is older than configPath
        if (not os.path.exists(backupPath) or
            os.path.getctime(backupPath) < os.path.getctime(configPath)):
            _logger.debug('Copying to %s', backupPath)
            shutil.copy2(configPath, backupPath)

    def getBackupPath(self):
        pathname = self.sim.scenario_config_file(self.sim.context)
        basename, ext = os.path.splitext(pathname)
        return basename + '-original' + ext       # i.e., [path...]/config-original.xml

    def write(self, path=None):
        """
        Write out the modified configuration file tree to the
        same path that it was read from, or to the given path.

        :param path: (str) pathname to write to
        :return:  none
        """
        if path:
            self.writePath = path       # remember the new path if one is given
        else:
            path = self.writePath

        if os.path.exists(path):        # remove it since it might be a symlink and
            os.unlink(path)             # we don't want to write through to the src

        _logger.debug("XMLConfigFile writing %s", path)
        self.tree.write(path, xml_declaration=True, pretty_print=True)

    def getConfigElement(self, name, group):
        '''
        Find the config file component with the specified tag and return
        the corresponding Element.
        '''
        xpath = f'//Configuration/{group}/Value[@name="{name}"]'
        found = self.tree.xpath(xpath)
        return None if len(found) == 0 else found[0]

    def getConfigValue(self, name, group):
        elt = self.getConfigElement(name, group)
        return None if elt is None else elt.text

    def getConfigGroup(self, group):
        groupElt = self.tree.xpath(f'//Configuration/{group}')
        if groupElt is None:
            raise PygcamMcsUserError(f'getConfigGroup: group "{group}" was not found')

        return groupElt[0]

    def updateConfigElement(self, name, group, newName=None, newValue=None):
        '''
        Update the name attribute, the value (element text), or both for the named config element.
        '''
        if not (newValue or newName):
            raise PygcamMcsUserError('updateConfigElement: must provide newTag or text, or both')

        elt = self.getConfigElement(name, group)
        if elt is None:
            raise PygcamMcsUserError(f'updateConfigElement: element "{name}" was not found in group {group}')

        if newName:
            elt.set('Name', newName)

        if newValue:
            elt.text = str(newValue)    # in case it was passed as numeric or bool

    def addConfigElement(self, name, group, value):
        '''
        Append a new element with the given name and value to the given group.
        '''
        groupElt = self.getConfigGroup(group)
        elt = ET.SubElement(groupElt, 'Value', name=name)
        elt.text = value
        return elt

    def deleteConfigElement(self, name, group):
        '''
        Remove the Value element with the given name from the given group
        '''
        groupElt = self.getConfigGroup(group)
        elt = self.getConfigElement(name, group)
        if elt is None:
            raise PygcamMcsUserError(f'deleteConfigElement: element "{name}" was not found in group {group}')

        groupElt.remove(elt)

    def getComponentPathname(self, name):
        pathname = self.getConfigValue(name, COMPONENTS_GROUP)
        if not pathname:
            raise PygcamMcsUserError(f'getComponentPathname: a file with tag "{name}" was not found')
        return pathname

    def updateComponentPathname(self, name, pathname):
        self.updateConfigElement(name, COMPONENTS_GROUP, newValue=pathname)

    def addComponentPathname(self, name, pathname):
        return self.addConfigElement(name, COMPONENTS_GROUP, pathname)

    def insertComponentPathname(self, name, pathname, after):
        groupElt = self.getConfigGroup(COMPONENTS_GROUP)

        afterNode = groupElt.find(f'Value[@name="{after}"]')
        if afterNode is None:
            raise PygcamMcsUserError(f"Can't insert {name} after {after}, as the latter doesn't exist")

        index = groupElt.index(afterNode) + 1

        node = ET.Element('Value')
        node.set('name', name)
        node.text = pathname
        groupElt.insert(index, node)

    def deleteComponent(self, name):
        return self.deleteConfigElement(name, COMPONENTS_GROUP)
