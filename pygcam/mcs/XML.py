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
