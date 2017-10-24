from __future__ import print_function

from lxml import etree as ET

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
    elts = evaluateConditional(root, varDict)
    return root.gettree()

_ops = {
    '=' : lambda a, b: a == b,
    '==': lambda a, b: a == b,
    '!=': lambda a, b: a != b,
    '<' : lambda a, b: a < b,
    '<=': lambda a, b: a <= b,
    '>' : lambda a, b: a > b,
    '>=': lambda a, b: a >= b,
}

def replaceConditional(elt, varDict):
    print("replaceConditional for:")
    ET.dump(elt)

    replacements = evaluateConditional(elt, varDict)
    last = elt
    for replacement in replacements:
        last.addnext(replacement)
        last = replacement

    # After adding replacement nodes, remove the conditional
    parent = elt.getparent
    parent.remove(elt)

def evaluateConditional(elt, varDict):
    print("\nevaluateConditional for:")
    ET.dump(elt)

    nodes = elt.findall('IF')
    if not nodes:
        return [elt]

    resultList = []

    # If there are IF nodes, evaluate them and return their results
    for ifnode in nodes:
        result = True
        for test in ifnode.findall('TEST'):
            var   = test.get('var')
            op    = test.get('op')
            value = test.get('value')

            func = _ops[op]
            funcReturn = func(varDict.get(var), value)
            print('<TEST %s %s %s> -> %s' % (var, op, value, funcReturn))

            # If multiple tests, implictly combine with 'AND'
            result = result and funcReturn
            if not result:
                # stop on first failure
                break

        branchName = 'THEN' if result else 'ELSE'

        # Replace the IF element with what it evaluated to
        branch = elt.find(branchName)

        for branchElt in list(branch):
            branchEvaled = evaluateConditional(branchElt, varDict)
            print('branchEvaled: ', branchEvaled)
            if branchEvaled is not None:
                resultList.extend(branchEvaled)

        # return the children of the THEN or ELSE branch. Might not have an else branch.
        replaceConditional(ifnode, resultList)
        return resultList

if __name__ == '__main__':
    pathname = '/Users/rjp/Downloads/Conditional.xml'

    varDict = {'bar': 'bar', 'foo': 'bar'}

    tree = readConditionalFile(pathname, varDict)

    ET.dump(tree.getroot())
