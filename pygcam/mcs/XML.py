# Created on July 5, 2013
#
# @author: Richard Plevin
#
# Copyright (c) 2014. The Regents of the University of California (Regents).
# See the file COPYRIGHT.txt for details.
#
# Note: Useful doc: http://infohost.nmt.edu/tcc/help/pubs/pylxml/web/index.html

from lxml import etree as ET
from pygcam.log import getLogger
from .error import PygcamMcsUserError, PygcamMcsSystemError

_logger = getLogger(__name__)

def pprint(elt):
    ET.tostring(elt, pretty_print=True)

def findAndSave(elt, eltName, cls, myDict, tree=None, testFunc=None, parent=None):
    '''
    Simple helper function to find elements with a given name, create
    a wrapper instance and store them in the given dictionary.
    '''
    for node in elt.iterfind(eltName):
        name = node.get('name')
        obj  = cls(node, tree) if tree else cls(node)

        if parent:
            try:
                obj.setParent(parent)
            except Exception as e:
                raise PygcamMcsSystemError("Call to setParent(%s) on %s failed" % (parent, obj))

        if name in myDict:
            raise PygcamMcsUserError("Attempt to save %s instance with duplicate name '%s'" \
                                     % (eltName, name))

        if testFunc is None or testFunc(obj):
            myDict[name] = obj


class XMLWrapper(object):
    '''
    A simple wrapper around any ElementTree element.
    '''
    def __init__(self, element):
        self.element = element
        self.name    = element.get('name') if element is not None else None

    def getElement(self):
        return self.element

    def getName(self):
        return self.name


class XMLFile(object):
    '''
    Stores information about an XML file. Provide wrapper to parse and access
    the file tree.
    '''
    def __init__(self, filename, load=True, removeComments=True):
        self.filename = filename
        self.tree = None

        if filename and load:
            self.read(removeComments=removeComments)

    def getRoot(self):
        return self.tree.getroot()

    def getTree(self):
        'Returns XML parse tree.'
        return self.tree

    def getFilename(self):
        return self.filename

    def getSchemaFile(self): # subclass can define this to allow validation via XMLSchema file
        return None

    def read(self, filename=None, removeComments=True):
        """
        Read the XML file, and if validate is not False and getDTD()
        returns a non-False value, validate the XML against the returned DTD.
        """
        if filename:
            self.filename = filename

        _logger.info("Reading '%s'", self.filename)
        parser = ET.XMLParser(remove_blank_text=True, remove_comments=removeComments)

        try:
            self.tree = ET.parse(self.filename, parser)

        except Exception as e:
            raise PygcamMcsSystemError("Can't read XML file '%s': %s" % (self.filename, e))

        if removeComments:
            for elt in self.tree.iterfind('//comment'):
                parent = elt.getparent()
                if parent is not None:
                    parent.remove(elt)

        schemaFile = self.getSchemaFile()       # subclasses can set
        if schemaFile:
            self.validateXML(schemaFile)

        return self.tree

    def getDTD(self):
        """
        Subclasses can implement this to return a string containing the DTD,
        which causes the XML file to be validated in the read() method.
        """
        return None

    def getXSD(self):
        """
        Subclasses can implement this to return a string containing the XMLSchema file,
        which causes the XML file to be validated in the read() method.
        """
        return None

    def validateXML(self, schemaFile, raiseOnError=True):
        """
        Validate a ParameterList against `schemaFile`. Optionally raises an
        error on failure, else return boolean validity status.
        """
        root = self.getRoot()

        schemaDoc = ET.parse(schemaFile)
        schema = ET.XMLSchema(schemaDoc)
        valid = schema.validate(root)

        if raiseOnError and not valid:
            raise PygcamMcsUserError(schema.error_log.filter_from_errors()[0])

        return valid

