from __future__ import print_function
from lxml import etree as ET

from pygcam.error import FileFormatError
from pygcam.log import getLogger

_logger = getLogger(__name__)

def dump(node):
    if node is None:
        print('None')
    else:
        ET.dump(node)
    print('')

def readConditionalFile(xmlFile, varDict, removeComments=True):
    """
    Read a conditional XML file, interpreting tests using the values in `varDict`,
    and returning the resulting XML tree after replacing conditional elements with
    the elements the expression evaluates to.

    :param xmlFile: (str) pathname of an XML file to read.
    :param varDict: (dict) values to use when interpreting <TEST> nodes
    :return: an XML tree
    """
    parser = ET.XMLParser(remove_blank_text=True, remove_comments=removeComments)
    tree = ET.parse(xmlFile, parser)

    root = tree.getroot()
    evaluateConditionals(root, varDict)
    return tree

_ops = {
    '=' : lambda a, b: a == b,
    '==': lambda a, b: a == b,
    '!=': lambda a, b: a != b,
    '<' : lambda a, b: a < b,
    '<=': lambda a, b: a <= b,
    '>' : lambda a, b: a > b,
    '>=': lambda a, b: a >= b,

    'eq': lambda a, b: a == b,
    'ne': lambda a, b: a != b,
    'lt': lambda a, b: a < b,
    'le': lambda a, b: a <= b,
    'gt': lambda a, b: a > b,
    'ge': lambda a, b: a >= b,
}

types = {'str': str, 'int': int, 'float': float, 'bool': bool}

def evalTest(ifnode, varDict):
    test = ifnode.find('test')      # add <AND>, <OR> later
    varName = test.get('var')
    op  = test.get('op', '==')      # defaults to test equality
    value = test.get('value')
    typeName  = test.get('type', 'str')

    # TBD: maybe have type={int, float, str, bool} and do conversions on both sides
    varValue = varDict.get(varName)
    typeFunc = types[typeName]

    def coerce(value, func):
        try:
            return func(value)
        except Exception:
            raise FileFormatError('Failed to convert variable "%s" value "%s" to %s', varName, value, func)

    value = coerce(value, typeFunc)
    varValue = coerce(varValue, typeFunc)

    try:
        func = _ops[op]
    except KeyError:
        # Shouldn't happen if schema is correct
        raise FileFormatError('Unknown comparison operator (%s) in conditional XML' % op)

    result = func(varValue, value)
    _logger.debug('<test $%s %s %r> -> %s' % (varName, op, value, result))

    branch = ifnode.find('then' if result else 'else')
    return branch

def evaluateConditionals(parent, varDict):
    for child in parent:
        if child.tag == 'if':
            branch = evalTest(child, varDict)
            if branch is not None:          # test because <ELSE> is optional
                evaluateConditionals(branch, varDict)

                last = child                # insert after the <IF>
                for elt in branch:
                    last.addnext(elt)
                    last = elt
            parent.remove(child)            # remove the <IF>
        else:
            evaluateConditionals(child, varDict)

if __name__ == '__main__':
    pathname = '/Users/rjp/Sync/Rich/xfer/Conditional.xml'

    varDict = {'bar': 'bar', 'foo': 'foo', 'baz': 20, 'mcsMode': True}

    tree = readConditionalFile(pathname, varDict)

    print("Result:")
    dump(tree.getroot())
