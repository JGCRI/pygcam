from __future__ import print_function
from lxml import etree as ET
import os
import pkg_resources as pkg

from pygcam.config import getConfigDict, getParam, stringTrue
from pygcam.log import getLogger
from pygcam.error import XmlFormatError, PygcamException

_logger = getLogger(__name__)

CONDITIONAL = 'CONDITIONAL'
TEST = 'TEST'
THEN = 'THEN'
ELSE = 'ELSE'
OR   = 'OR'
AND  = 'AND'

_ops = {
    '=' : lambda a, b: a == b,
    '==': lambda a, b: a == b,
    '!=': lambda a, b: a != b,
    '<' : lambda a, b: a <  b,
    '<=': lambda a, b: a <= b,
    '>' : lambda a, b: a >  b,
    '>=': lambda a, b: a >= b,

    'eq': lambda a, b: a == b,
    'ne': lambda a, b: a != b,
    'lt': lambda a, b: a <  b,
    'le': lambda a, b: a <= b,
    'gt': lambda a, b: a >  b,
    'ge': lambda a, b: a >= b,
}

_types = {'str': str, 'int': int, 'float': float, 'bool': bool}

# TBD: Modified from version from mcs.XML

class XMLFile(object):
    """
    Stores information about an XML file; provides wrapper to parse and access
    the file tree, and handle "conditional XML".

    :param filename: (str) The pathname to the XML file
    :param load: (bool) If True, the file is loaded, otherwise, the instance is
       set up, but the file is not read.
    :param schemaPath: (str) If not None, the path relative to the root of the
       package to the .xsd (schema definition) file to use to validate the XML file.
    :param removeComments: (bool) If True, comments are discarded upon reading the file.
    :param conditionalXML: (bool) If True, the XML is processed using Conditional XML
       prior to validation.
    :param varDict: (dict) A dictionary to use in place of the configuration dictionary
       when processing Conditional XML.
    """
    def __init__(self, filename, load=True, schemaPath=None,
                 removeComments=True, conditionalXML=False, varDict=None):
        self.filename = filename
        self.tree = None
        self.conditionalXML = conditionalXML
        self.varDict = varDict or getConfigDict(section=getParam('GCAM.DefaultProject'))
        self.removeComments = removeComments

        self.schemaPath   = schemaPath
        self.schemaStream = None

        if filename and load:
            self.read()

    def getRoot(self):
        'Return the root node of the parse tree'
        return self.tree.getroot()

    def getTree(self):
        'Return XML parse tree.'
        return self.tree

    def getFilename(self):
        'Return the filename for this ``XMLFile``'
        return self.filename

    def read(self):
        """
        Read the XML file, and if validate if ``self.schemaFile`` is not None.
        """
        filename = self.filename

        _logger.debug("Reading '%s'", filename)
        parser = ET.XMLParser(remove_blank_text=True, remove_comments=self.removeComments)

        try:
            tree = self.tree = ET.parse(filename, parser)

        except Exception as e:
            raise XmlFormatError("Can't read XML file '%s': %s" % (filename, e))

        if self.conditionalXML:
            self.evaluateConditionals(tree.getroot())

        if self.removeComments:
            for elt in tree.iterfind('//comment'):
                parent = elt.getparent()
                if parent is not None:
                    parent.remove(elt)

        self.validate()

        return tree

    def validate(self, raiseOnError=True):
        """
        Validate a ParameterList against ``self.schemaFile``. Optionally raises an
        error on failure, else return boolean validity status. If no schema file
        is defined, return ``True``.
        """
        if not self.schemaPath:
            return True

        tree = self.tree

        # ensure that the entire directory has been extracted so that 'xs:include' works
        pkg.resource_filename('pygcam', os.path.dirname(self.schemaPath))
        abspath = pkg.resource_filename('pygcam', self.schemaPath)

        xsd = ET.parse(abspath)
        schema = ET.XMLSchema(xsd)

        if raiseOnError:
            try:
                schema.assertValid(tree)
                return True
            except ET.DocumentInvalid as e:
                raise XmlFormatError("Validation of '%s'\n  using schema '%s' failed:\n  %s" % (self.filename, self.schemaPath, e))
        else:
            valid = schema.validate(tree)
            return valid

    def evalTest(self, node):
        tag = node.tag

        if tag == TEST:
            varName  = node.get('var')
            op       = node.get('op', '==')      # defaults to equality
            value    = node.get('value')
            typeName = node.get('type', 'str')   # defaults to str comparison
            varValue = self.varDict.get(varName)
            typeFunc = stringTrue if typeName == 'bool' else _types[typeName]

            def coerce(value, func):
                try:
                    return func(value)
                except Exception:
                    raise XmlFormatError('Failed to convert variable "%s" value "%s" to %s', varName, value, func)

            value    = coerce(value, typeFunc)
            varValue = coerce(varValue, typeFunc)

            try:
                func = _ops[op]
            except KeyError:
                # Shouldn't happen if schema is correct
                raise XmlFormatError('Unknown comparison operator (%s) in conditional XML' % op)

            result = func(varValue, value)
            _logger.debug('<test $%s %s %r> -> %s' % (varName, op, value, result))
            return result

        if tag == AND:
            for child in node:
                if not self.evalTest(child):
                    _logger.debug('<AND> -> False')
                    return False
            _logger.debug('<AND> -> True')
            return True

        if tag == OR:
            for child in node:
                if self.evalTest(child):
                    _logger.debug('<OR> -> True')
                    return True
            _logger.debug('<OR> -> False')
            return False

        raise XmlFormatError('Expected one of %s; got %s' % ((TEST, AND, OR), tag))

    def chooseBranch(self, ifnode):
        tests = ifnode.xpath('%s|%s|%s' % (TEST, AND, OR))

        if len(tests) != 1:
            # Shouldn't happen if schema is correct
            raise XmlFormatError('Expected 1 test|and|or node, got %d' % len(tests))

        test = tests[0]

        result = self.evalTest(test)
        branch = ifnode.find(THEN if result else ELSE)
        return branch

    def evaluateConditionals(self, parent):
        for child in parent:
            if child.tag == CONDITIONAL:
                branch = self.chooseBranch(child)
                if branch is not None:          # test because <else> is optional
                    self.evaluateConditionals(branch)

                    last = child                # insert after the <conditional>
                    for elt in branch:
                        last.addnext(elt)
                        last = elt
                parent.remove(child)            # remove the <conditional>
            else:
                self.evaluateConditionals(child)


class McsValues(XMLFile):
    def __init__(self, filename):
        """
        Reads an XML file of numeric values for named parameters by region.
        This allows the Monte Carlo simulation machinery to modify these
        values. Note that the file's contents are ignored if read by GCAM.

        :param filename: (str) the name of an XML file adhering to mcsValues-schema.xsd.
        """
        from collections import defaultdict

        _logger.debug('Reading MCS values from %s', filename)
        super(McsValues, self).__init__(filename, schemaPath='etc/mcsValues-schema.xsd')

        self.regionMap = defaultdict(dict)
        for regNode in self.tree.iterfind('//region'):
            region = regNode.get('name')
            valueMap = self.regionMap[region]
            for valNode in regNode.iterfind('.//value'):
                name = valNode.get('name')
                valueMap[name] = float(valNode.text)    # xml schema requires numeric value here

    def regions(self):
        """
        Get the regions used in this file.

        :return: (list of str) region names
        """
        return self.regionMap.keys()

    def values(self, region):
        """
        Get the values associated with the `region`.

        :param region: (str) the name of a GCAM region
        :return: (dict) keys are names of value elements and values are floats.
           Returns None if the region is not found
        """
        return self.regionMap.get(region, None)

    def valueForRegion(self, paramName, region, default=None, raiseError=True):
        regionMap = self.values(region)
        if regionMap is None:
            if raiseError:
                raise PygcamException('Region "%s" is not defined in %s' % (region, self.filename))
            return None

        return regionMap.get(paramName, default)

if __name__ == '__main__':
    pathname = '../tests/data/xml/Conditional.xml'
    pathname = '/Users/rjp/bitbucket/paper1/etc/project.xml'
    varDict  = {'bar': 'bar', 'foo': 'foo', 'baz': 20, 'mcsMode': True}
    _logger.setLevel('INFO')

    print('varDict=%s' % varDict)

    xml = XMLFile(pathname, varDict=varDict, schemaPath='etc/project-schema.xsd')
    root = xml.getRoot()

    xml.evaluateConditionals(root)

    print("Result:")
    ET.dump(root)
