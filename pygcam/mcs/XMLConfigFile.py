# Copyright (c) 2015-2023 Richard Plevin. See the file COPYRIGHT.txt for details.

import os
from lxml import etree as ET
import shutil

from ..config import getParam, mkdirs
from ..log import getLogger
from .sim_file_mapper import SimFileMapper
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

    def __init__(self, mapper : SimFileMapper, useCopy=False):
        '''
        Read and cache a GCAM configuration file in self.tree.
        '''
        self.writePath = None
        #self.context = copy(mapper.context)   # TBD: any need to copy this?

        ctx = mapper.context

        # TBD
        #  If config.xml is not found in expected location, copy it from
        #  either (i) the baseline's config file (error if not found) if
        #  not a baseline scenario, otherwise (ii) a defined parent scenario,
        #  or (iii) the reference config file if no parent was identified.
        #  (Note that 'parent' logic is not currently implemented.)

        config_path = mapper.scenario_config_file(ctx.scenario)

        if not os.path.exists(config_path):

            if ctx.is_baseline():
                copy_from = getParam('GCAM.RefConfigFile')
            else:
                # TBD: scenario "parent" is not passed through. Read from scenarios.xml?
                copy_from = mapper.scenario_config_file(ctx.baseline)

            _logger.debug(f"XMLConfig copying '{copy_from}' to '{config_path}'")
            shutil.copy2(copy_from, config_path)

        # TBD: unclear if this is still needed
        # If no backup, or it's outdated, make a copy of the config file for use by runsim
        backup_path = self.copyOriginal(config_path)

        path = backup_path if useCopy else config_path

        # Default writePath is where we were read from.
        self.writePath = path

        super(XMLConfigFile, self).__init__(path)

    @classmethod
    def decache(cls):
        cls.instances = {}

    @classmethod
    def configForScenario(cls, mapper, scenario, useCopy=False):
        '''
        Return the path to the run-tree version of the config file
        for the given scenario.
        '''
        key = (scenario, useCopy)
        try:
            return cls.instances[key]

        except KeyError:
            obj = XMLConfigFile(mapper, useCopy=useCopy)
            cls.instances[key] = obj
            return obj

    @classmethod
    def writeAll(cls, mapper : SimFileMapper):
        """
        Write all configuration files to disk.
        """
        for cfg in cls.instances.values():
            config_path = mapper.scenario_config_file(cfg.context.scenario)
            cfg.write(path=config_path)

    def copyOriginal(self, config_path):
        '''
        Copy config file to xxx/config-original.xml if config.xml is
        newer, so runsim can use the original to generate XML files.
        '''
        if not os.path.exists(config_path):
            raise PygcamMcsSystemError(f"XMLConfigFile: file '{config_path}' does not exist.")

        backup_path = self.getBackupPath(config_path)

        # Copy only if the backupPath doesn't exist or is older than config_path
        if (not os.path.exists(backup_path) or
            os.path.getctime(backup_path) < os.path.getctime(config_path)):
            _logger.debug('Copying to %s', backup_path)
            shutil.copy2(config_path, backup_path)

        return backup_path

    def getBackupPath(self, config_path):
        basename, ext = os.path.splitext(config_path)
        return basename + '-original' + ext       # i.e., [path...]/config-original.xml

    def write(self, path=None):
        """
        Write out the modified configuration file tree to the
        same path that it was read from, or to the given path.

        :param path: (str) pathname to write to
        :return:  none
        """
        if path:
            self.writePath = path           # remember the new path if one is given
            mkdirs(os.path.dirname(path))   # make sure directory exists
        else:
            path = self.writePath

        if os.path.exists(path):        # remove it since it might be a symlink and
            os.unlink(path)             # we don't want to write through to the src

        _logger.debug("XMLConfigFile writing '%s'", path)
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
