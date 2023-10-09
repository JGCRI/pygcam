"""
.. Copyright (c) 2016-2023 Richard Plevin

   See the https://opensource.org/licenses/MIT for license details.
"""
import os
import re
from lxml import etree as ET

from .error import SetupException, PygcamException
from .gcam_path import GcamPath
from .log import getLogger

AttributePattern = re.compile(r'(.*)/@([-\w]*)$')

_logger = getLogger(__name__)

def expandYearRanges(seq):
    """
    Expand a sequence of (year, value) tuples, or a dict keyed by
    year, where the year argument may be a string containing identifying
    range of values with an optional "step" value indicated after a ":".
    The default step is 5 years. For example, "2015-2030" expands to
    (2015, 2020, 2025, 2030), and "2015-2020:1" expands to
    (2015, 2016, 2017, 2018, 2019, 2020). When a range is given, the
    tuple is replaced with a sequence of tuples naming each year explicitly.
    Typical usage is ``for year, price in expandYearRanges(values): ...``.

    :param seq: (tuple, list, dict) The sequence of (year, value) tuples,
        or any object with an items() method that returns (year, value) pairs.
    :return:
        A list of tuples with the expanded sequence.
    """
    result = []
    try:
        seq = list(seq.items())     # convert dict or Series to list of pairs
    except:                         # or quietly fail, and just use 'seq' as is
        pass

    for year, value in seq:
        value = float(value)
        if isinstance(year, str) and '-' in year:
            m = re.search('^(\d{4})-(\d{4})(:(\d+))?$', year)
            if not m:
                raise SetupException(f'Unrecognized year range specification: {year}')

            startYear = int(m.group(1))
            endYear   = int(m.group(2))
            stepStr = m.group(4)
            step = int(stepStr) if stepStr else 5
            expanded = [[y, value] for y in range(startYear, endYear+step, step)]
            result.extend(expanded)
        else:
            result.append((int(year), value))

    return result


class CachedFile(object):
    parser = ET.XMLParser(remove_blank_text=True)

    # Store parsed XML trees here and use with xmlSel/xmlEdit if useCache is True
    cache = {}

    def __init__(self, filename):
        self.filename = filename = os.path.realpath(filename)
        self.edited = False

        _logger.debug("CachedFile: reading '%s'", filename)
        self.tree = ET.parse(filename, self.parser)
        self.cache[filename] = self

    @classmethod
    def getFile(cls, obj):
        if isinstance(obj, CachedFile):
            return obj

        # realpath => operate on canonical pathnames
        filename = os.path.realpath(obj.abs if isinstance(obj, GcamPath) else obj)

        try:
            item = cls.cache[filename]
        except KeyError:
            item = CachedFile(filename)

        return item

    def setEdited(self):
        self.edited = True

    def write(self):
        _logger.info("CachedFile: writing '%s'", self.filename)
        self.tree.write(self.filename, xml_declaration=True, encoding='utf-8', pretty_print=True)
        self.edited = False

    def decache(self):
        if self.edited:
            self.write()

    @classmethod
    def decacheAll(cls):
        for item in cls.cache.values():
            item.decache()

    def __str__(self):
        return f"<CachedFile '{self.filename}' edited:{self.edited}>"

def xmlSel(obj, xpath, asText=False):
    """
    Return True if the XML component identified by the xpath argument
    exists in `filename`. Useful for deciding whether to edit or
    insert an XML element.

    :param obj: (CachedFile, GcamPath, or str) the file to edit
    :param xpath: (str) the xml element(s) to search for
    :param asText: (str) if True, return the text of the node, if found, else None
    :return: (bool) True if found, False otherwise. (see asText)
    """
    item = CachedFile.getFile(obj)

    result = item.tree.find(xpath)
    if asText:
        return result.text if result is not None else None

    return (result is not None)

def xmlIns(obj, xpath, elt):
    """
    Insert the element `elt` as a child to the node found with `xpath`.

    :param obj: (CachedFile, GcamPath, or str) the file to edit
    :param xpath: (str) the xml element(s) to search for
    :param elt: (etree.Element) the node to insert
    :return: none
    """
    item = CachedFile.getFile(obj)
    item.setEdited()

    parentElt = item.tree.find(xpath)
    if parentElt is None:
        raise SetupException(f"xmlIns: failed to find parent element at {xpath} in {item.filename}")

    parentElt.append(elt)

#
# xmlEdit can set a value, multiply a value in the XML by a constant,
# or add a constant to the value in the XML. These funcs handle each
# operation, allowing the logic to be outside the loop, which might
# iterate over thousands of elements.
#
def _set(elt, value):
    elt.text = str(value)

def _multiply(elt, value):
    elt.text = str(float(elt.text) * value)

def _add(elt, value):
    elt.text = str(float(elt.text) + value)

_editFunc = {'set'      : _set,
             'multiply' : _multiply,
             'add'      : _add}

# TBD: Allow first arg to be a CachedFile to skip additional lookup step?
def xmlEdit(obj, pairs, op='set', useCache=True):
    """
    Edit the XML file `filename` in place, applying the values to the given xpaths
    in the list of pairs.

    :param obj: (CachedFile, GcamPath, or str) the file to edit
    :param pairs: (iterable of (xpath, value) pairs) In each pair, the xpath selects
      elements or attributes to update with the given values.
    :param op: (str) Operation to perform. Must be in ('set', 'multiply', 'add').
      Note that 'multiply' and 'add' are *not* available for xpaths selecting
      attributes rather than node values. For 'multiply'  and 'add', the value
      should be passed as a float. For 'set', it can be a float or a string.
    :param useCache: (bool) if True, the etree is sought first in the XmlCache. This
      avoids repeated parsing, but the file is always written (eventually) if updated
      by this function.
    :return: True on success, else False
    """
    legalOps = _editFunc.keys()

    if op not in legalOps:
        raise PygcamException(f'xmlEdit: unknown operation "{op}". Must be one of {legalOps}')

    modFunc = _editFunc[op]

    item = CachedFile.getFile(obj)
    tree = item.tree

    updated = False

    # if at least one xpath is found, update and write file
    for xpath, value in pairs:
        attr = None

        # If it's an attribute update, extract the attribute
        # and use the rest of the xpath to select the elements.
        match = re.match(AttributePattern, xpath)
        if match:
            attr = match.group(2)
            xpath = match.group(1)

        elts = tree.xpath(xpath)
        if len(elts):
            updated = True
            if attr:                # conditional outside loop since there may be many elements
                value = str(value)
                for elt in elts:
                    elt.set(attr, value)
            else:
                for elt in elts:
                    modFunc(elt, value)

    if updated:
        if useCache:
            item.setEdited()
        else:
            item.write()

    return updated
