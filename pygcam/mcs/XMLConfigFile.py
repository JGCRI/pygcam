# Copyright (c) 2015-2023 Richard Plevin. See the file COPYRIGHT.txt for details.

import os
from lxml import etree as ET

from ..config import mkdirs
from ..log import getLogger
from ..XMLFile import XMLFile
from .error import PygcamMcsUserError

_logger = getLogger(__name__)

# The pre-defined sections of GCAM configuration files
COMPONENTS_GROUP = 'ScenarioComponents'
FILES_GROUP   = 'Files'
STRINGS_GROUP = 'Strings'
INTS_GROUP    = 'Ints'
BOOLS_GROUP   = 'Bools'
DOUBLES_GROUP = 'Doubles'

# TBD: Note that the functions here seem to duplicate some of XMLEditor.
#  This class is used only in XMLParameterFile.py and gcamdata.py, i.e., for MCS only.
#  Have this class do only:
#  - caching of config file instances (with parsed XML) keyed by normed, abspath
#  - finding / modifying / deleting elements from the etree structure
#  - writing modified tree to original (or different) pathname
class XMLConfigFile(XMLFile):
    '''
    Stores information about a GCAM config.xml file
    '''
    instances = {}  # XMLConfigFile instances keyed by scenario name

    def __init__(self, config_path):
        """
        Read and cache a GCAM configuration file in self.tree.
        """
        # Default writePath is where we were read from, but can be changed.
        self.writePath = config_path

        super(XMLConfigFile, self).__init__(config_path)

    @classmethod
    def decache(cls):
        cls.instances = {}

    @classmethod
    def get_instance(cls, cfg_path):
        '''
        Return a parsed version of the given config file.
        '''
        key = os.path.abspath(os.path.normpath(cfg_path))
        try:
            return cls.instances[key]

        except KeyError:
            cls.instances[key] = obj = XMLConfigFile(cfg_path)
            return obj

    # Deprecated
    # def copyOriginal(self, config_path):
    #     '''
    #     Copy config file to xxx/config-original.xml if config.xml is
    #     newer, so runsim can use the original to generate XML files.
    #     '''
    #     if not os.path.exists(config_path):
    #         raise PygcamMcsSystemError(f"XMLConfigFile: file '{config_path}' does not exist.")
    #
    #     basename, ext = os.path.splitext(config_path)
    #     backup_path = f"{basename}-original{ext}"
    #
    #     # Copy only if the backupPath doesn't exist or is older than config_path
    #     if (not os.path.exists(backup_path) or
    #         os.path.getctime(backup_path) < os.path.getctime(config_path)):
    #         _logger.debug('Copying to %s', backup_path)
    #         shutil.copy2(config_path, backup_path)
    #
    #     return backup_path

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

    def get_config_element(self, name, group):
        '''
        Find the config file component with the specified tag and return
        the corresponding Element.
        '''
        xpath = f'//Configuration/{group}/Value[@name="{name}"]'
        found = self.tree.xpath(xpath)
        return None if len(found) == 0 else found[0]

    def get_config_value(self, name, group):
        elt = self.get_config_element(name, group)
        return None if elt is None else elt.text

    def get_config_group(self, group):
        groupElt = self.tree.xpath(f'//Configuration/{group}')
        if groupElt is None or len(groupElt) == 0:
            raise PygcamMcsUserError(f'get_config_group: group "{group}" was not found')

        return groupElt[0]

    def get_component_dict(self):
        file_refs = self.tree.xpath('//ScenarioComponents/Value')
        d = {os.path.basename(elt.text): (elt.attrib['name'], elt.text) for elt in file_refs}
        return d

    def update_config_element(self, name, group, newName=None, newValue=None):
        '''
        Update the name attribute, the value (element text), or both for the named config element.
        '''
        if not (newValue or newName):
            raise PygcamMcsUserError('update_config_element: must provide newTag or text, or both')

        elt = self.get_config_element(name, group)
        if elt is None:
            raise PygcamMcsUserError(f'update_config_element: element "{name}" was not found in group {group}')

        if newName:
            elt.set('name', newName)

        if newValue:
            elt.text = str(newValue)    # in case it was passed as numeric or bool

    # TBD: used only by unused addComponent, below
    def add_config_element(self, name, group, value):
        '''
        Append a new element with the given name and value to the given group.
        '''
        groupElt = self.get_config_group(group)
        elt = ET.SubElement(groupElt, 'Value', name=name)
        elt.text = value
        return elt

    # TBD: used only by unused delete_component, below
    def delete_config_element(self, name, group):
        '''
        Remove the Value element with the given name from the given group
        '''
        groupElt = self.get_config_group(group)
        elt = self.get_config_element(name, group)
        if elt is None:
            raise PygcamMcsUserError(f'delete_config_element: element "{name}" was not found in group {group}')

        groupElt.remove(elt)

    def get_component_pathname(self, name):
        pathname = self.get_config_value(name, COMPONENTS_GROUP)
        if not pathname:
            raise PygcamMcsUserError(f'get_component_pathname: a file with tag "{name}" was not found')
        return pathname

    def update_component_pathname(self, name, pathname):
        self.update_config_element(name, COMPONENTS_GROUP, newValue=pathname)

    # TBD: unused except test
    def add_component_pathname(self, name, pathname):
        return self.add_config_element(name, COMPONENTS_GROUP, pathname)

    # TBD: unused
    def insert_component_pathname(self, name, pathname, after):
        groupElt = self.get_config_group(COMPONENTS_GROUP)

        afterNode = groupElt.find(f'Value[@name="{after}"]')
        if afterNode is None:
            raise PygcamMcsUserError(f"Can't insert {name} after {after}, as the latter doesn't exist")

        index = groupElt.index(afterNode) + 1

        node = ET.Element('Value')
        node.set('name', name)
        node.text = pathname
        groupElt.insert(index, node)

    # TBD: unused
    def delete_component(self, name):
        return self.delete_config_element(name, COMPONENTS_GROUP)
