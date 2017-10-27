from lxml import etree as ET
from .log import getLogger
from .error import XmlF

_logger = getLogger(__name__)

# TBD: Version from mcs.XML

class XMLFileFromMCS(object):
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
            raise XmlFormatError("Can't read XML file '%s': %s" % (self.filename, e))

        if removeComments:
            for elt in self.tree.iterfind('//comment'):
                parent = elt.getparent()
                if parent is not None:
                    parent.remove(elt)

        schemaFile = self.getSchemaFile()       # subclasses can set
        if schemaFile:
            self.validateXML(schemaFile)

        return self.tree

    # Deprecated
    # def getDTD(self):
    #     """
    #     Subclasses can implement this to return a string containing the DTD,
    #     which causes the XML file to be validated in the read() method.
    #     """
    #     return None

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
