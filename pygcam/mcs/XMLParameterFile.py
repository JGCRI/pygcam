# Created on July 5, 2013
#
# Copyright (c) 2013-2022. The Regents of the University of California (Regents)
# and Richard Plevin.
# See the file COPYRIGHT.txt for details.

from collections import OrderedDict, defaultdict
from lxml import etree as ET
from math import ceil
import numpy as np
import os
import pandas as pd

from ..config import getParam, mkdirs, pathjoin
from ..constants import TRIAL_XML_NAME, FileVersions
from ..xml_edit import CachedFile
from ..log import getLogger
from ..utils import importFromDotSpec
from ..XMLConfigFile import XMLConfigFile
from ..XMLFile import XMLFile

from .database import getDatabase
from .distro import DistroGen
from .error import PygcamMcsUserError, PygcamMcsSystemError, DistributionSpecError
from .sim_file_mapper import SimFileMapper
from .util import loadObjectFromPath
from .XML import XMLWrapper, findAndSave, getBooleanXML
from .XMLResultFile import XMLColumn, XMLConstraint, CONSTRAINT_ELT_NAME

_logger = getLogger(__name__)

# XML parameter file element tags
INFILE_ELT_NAME      = 'InputFile'
PARAMLIST_ELT_NAME   = 'ParameterList'
PARAM_ELT_NAME       = 'Parameter'
QUERY_ELT_NAME       = 'Query'
CSV_QUERY_ELT_NAME   = 'CsvQuery'
DESC_ELT_NAME        = 'Description'
CATEGORY_ELT_NAME    = 'Category'
NOTES_ELT_NAME       = 'Notes'
EVIDENCE_ELT_NAME    = 'Evidence'
RATIONALE_ELT_NAME   = 'Rationale'
CORRELATION_ELT_NAME = 'Correlation'
WITH_ELT_NAME        = 'With'
DISTRO_ELT_NAME      = 'Distribution'
DATAFILE_ELT         = 'DataFile'
PYTHON_FUNC_ELT      = 'PythonFunc'
WRITE_FUNC_ELT       = 'WriteFunc'

# TBD: test these
# These attributes of a <Distribution> element are not parameters to the
# random variable distribution itself, so we exclude these from the
# list we pass when creating the RV.
#DISTRO_META_ATTRS     = ['name', 'type', 'apply']
DISTRO_MODIF_ATTRS    = ['lowbound', 'highbound'] # , 'updatezero']


class XMLCorrelation(XMLWrapper):
    """
    Store information from a <Correlation> element
    """
    instances = []

    @classmethod
    def createCorrelations(cls, element, param):
        """
        A <Correlation> element can have 1 or more "With" elements specifying
        what to correlate with, e.g., <With name="otherParam">0.6</With>
        """
        targets = element.findall(WITH_ELT_NAME)
        for target in targets:
            obj = XMLCorrelation(element, param, target)
            cls.instances.append(obj)

    @classmethod
    def decache(cls):
        cls.instances = []

    def __init__(self, element, param, target):
        super().__init__(element)
        self.param = param
        self.paramName = self.param.getName()
        self.otherName = target.get('name')

        try:
            self.value = float(target.text)

        except ValueError:
            raise PygcamMcsUserError("In parameter %s, the value of a Correlation element (%s) is not numeric"
                                     % (self.paramName, element.text))

        _logger.debug('Defined correlation of %.3f between %s and %s',
                       self.value, self.paramName, self.otherName)

    @classmethod
    def corrMatrix(cls):
        """
        Generate a correlation matrix representing the correlation definitions,
        or None if no Correlation definitions were found.
        """
        if not cls.instances:
            return None

        params = XMLParameter.getInstances()
        count  = len(params)

        corrMat = np.zeros((count, count), dtype=float)

        for i in range(count):
            corrMat[i][i] = 1.0  # diagonal must be 1

        for corr in cls.instances:
            p1 = corr.param
            p2 = corr.other
            coef = corr.value

            src1 = p1.getDataSrc()
            src2 = p2.getDataSrc()

            # TBD: Restrict correlation to Distribution, or ok with PythonFunc or DataFile?

            if src1.isShared() != src2.isShared():
                raise PygcamMcsUserError('''
    Parameters '%s' and '%s' cannot be correlated because
    one is 'shared' and the other is 'independent'.''' % (corr.paramName, corr.otherName))

            if src1.isShared():
                varNum1 = p1.rv.getVarNum()
                varNum2 = p2.rv.getVarNum()

                if varNum1 == varNum2:
                    raise PygcamMcsUserError('''
    Parameter '%s' has a single (shared) random variable; it cannot be self-correlated.''' % corr.paramName)
                corrMat[varNum1][varNum2] = corrMat[varNum2][varNum1] = coef

            else:
                # If the parameters have independent RVs per XML element, two parameters
                # can be correlated if they have the same number of RVs, and the RVs of
                # a single param can be correlated pairwise amongst themselves.
                if p1 == p2:
                    raise PygcamMcsUserError('''
    Parameter '%s' has %d independent random variables; it cannot be self-correlated.''' % (corr.paramName, len(p1.getVars())))
                    # Create pairwise correlations among the RVs. This is probably a bad idea if
                    # the query returns more than a few dozen elements, as is usually the case.
                    # vars = p1.getVars()
                    #
                    # from itertools import permutations
                    # # create all unique pairwise combinations of parameters
                    # # and then map these to pairwise combinations of var nums
                    # varNumPairs = map(lambda pair: (pair[0].rv.getVarNum(),
                    #                                 pair[1].rv.getVarNum()),
                    #                   permutations(vars))
                else:
                    # Two different parameters with independent RVs.
                    p1Vars = p1.getVars()
                    p2Vars = p2.getVars()

                    if len(p1Vars) != len(p2Vars):
                        raise PygcamMcsUserError('''
    Parameters '%s' and '%s' cannot be correlated because
    they have a different number of random variables.''' % (corr.paramName, corr.otherName))

                    varNumPairs = [(pair[0].rv.getVarNum(), pair[1].rv.getVarNum()) for pair in zip(p1Vars, p2Vars)]

                # In either case, use the pairs of varNums to set up the matrix
                for i, j in varNumPairs:
                    corrMat[i][j] = corrMat[j][i] = coef

        return corrMat

    @classmethod
    def finishSetup(cls):
        for obj in cls.instances:
            obj.other = XMLParameter.getInstance(obj.otherName)
            if obj.other is None:
                raise PygcamMcsUserError('Unknown parameter "%s" in Correlation for %s' % (obj.otherName, obj.paramName))


class XMLQuery(XMLWrapper):
    """Wraps a <Query> element, which holds an xpath expression."""
    def __init__(self, element):
        super().__init__(element)
        self.xpath = element.text.strip()

    def getXPath(self):
        return self.xpath

    def runQuery(self, tree):
        """
        Run an XPath query on the given tree and return a list of the elements found.
        """
        xpath = self.getXPath()
        found = tree.xpath(xpath)
        return found


class CSVQuery(XMLWrapper):
    """Wraps a <CsvQuery> element, which holds CSV query information."""
    def __init__(self, element):
        super().__init__(element)

        columnElt = element.find('Column')  # required by schema
        self.column = XMLColumn(columnElt)

        # Create the "where" clause to use with a DataFrame.query() on the results we'll read in
        self.constraints = [XMLConstraint(item) for item in element.iterfind(CONSTRAINT_ELT_NAME)]
        constraintStrings = list(filter(None, map(XMLConstraint.asString, self.constraints)))
        self.whereClause = ' and '.join(constraintStrings)
        self.matchConstraints = list(filter(lambda constraint: constraint.op in XMLConstraint.strMatch, self.constraints))

    def stringMatch(self, df):
        """
        Handle any string matching constraints since these can't be handled in a df.query()
        """
        for constraint in self.matchConstraints:
            df = constraint.stringMatch(df)

        return df

    def select_indices(self, item_name, df):
        # apply (in)equality constraints
        selected = df.query(self.whereClause) if self.whereClause else df

        # apply string matching constraints
        selected = self.stringMatch(selected)

        count = len(selected)
        if count == 0:
            raise PygcamMcsUserError(f"DataFrame query for '{item_name}' matched no items")

        _logger.debug(f"Matched {count} rows from DataFrame for '{item_name}'")
        return selected.index

    def runQuery(self, tree):
        """
        Run a query on a CSV file to find the element in the given column that
        meets the given constraints.
        """
        xpath = self.getXPath()
        found = tree.xpath(xpath)
        return found

class XMLTrialData(XMLWrapper):
    """
    An abstract class that provides the protocol required of classes that can produce
    trial data, i.e., XMLDistribution, XMLDataFile, or XMLPythonFunc
    """
    def __init__(self, element, param):
        super().__init__(element)
        self.param = param
        self.rv    = None

    def getMode(self):
        """
        Get the containing parameter mode, one of {'direct', 'shared', 'independent'}
        """
        return self.param.getMode()

    def isShared(self, mode=None):
        if not mode:
            mode = self.getMode()
        return mode == 'shared'

    def getApply(self):
        """
        Default distro application is 'direct', i.e., directly set the element value.
        """
        s = self.element.get('apply', 'direct')
        return s.lower()

    def isDirect(self, applyAs=None):
        if not applyAs:
            applyAs = self.getApply()
        return applyAs in ('direct', 'replace')     # synonyms, though "direct" might be deprecated

    def isFactor(self, applyAs=None):
        if not applyAs:
            applyAs = self.getApply()
        return applyAs in ('mult', 'multiply')

    def isDelta(self, applyAs=None):
        if not applyAs:
            applyAs = self.getApply()
        return applyAs == 'add'

    def isTrialFunc(self):      # overridden in XMLDistribution when apply is a func reference
        return False

    def isLinked(self):         # overridden in XMLDistribution
        return False

    def ppf(self, *args):
        raise PygcamMcsSystemError('Called abstract "ppf" method of %s' % self.___class__.name)


class XMLDistribution(XMLTrialData):
    """
    A wrapper around a <Distribution> element to provide some
    convenience functions.
    """
    trialFuncDir = None

    @classmethod
    def decache(cls):
        cls.trialFuncDir = None

    def __init__(self, element, param):
        super().__init__(element, param)

        self.argDict  = {}
        self.modDict = defaultdict(lambda: None)
        self.modDict['apply'] = 'direct'    # set default value

        # Distribution attributes are {apply, highbound, lowbound}, enforced by XSD file
        for key, val in element.items():
            self.modDict[key] = float(val) if key in DISTRO_MODIF_ATTRS else val

        # Load trial function, if defined (i.e., if there's a '.' in the value of the "apply" attribute.)
        self.trialFunc = self.loadTrialFunc()

        self.otherArgs = None
        if self.trialFunc:
            elt = self.element.find('OtherArgs')
            if elt is not None and elt.text:
                codeStr = "dict({})".format(elt.text)
                try:
                    self.otherArgs = eval(codeStr)

                except SyntaxError as e:
                    raise DistributionSpecError(f"XMLDistribution: failed to evaluate expression {codeStr}: {e}")

        self.child = element[0]
        self.distroName = self.child.tag.lower()

        # TBD: hack alert to deal with non-float attribute. Fix this in the rewrite.
        # TBD: Might be cleaner to have something that isn't confused with a distribution?
        self._isLinked = self.child.tag == 'Linked'
        if self._isLinked:
            attr = 'parameter'
            self.argDict[attr] = self.child.get(attr)

        elif self.distroName == 'sequence':
            for key, val in self.child.items():
                self.argDict[key] = val           # don't convert to float

        else:
            for key, val in self.child.items():
                self.argDict[key] = float(val)    # these form the signature that identifies the distroElt function

        sig = DistroGen.signature(self.distroName, self.argDict.keys())
        _logger.debug(f"Param: {param.name} <Distribution %s, %s>", ' '.join(map(lambda pair: '%s="%s"' % pair, element.items())), sig)

        gen = DistroGen.generator(sig)
        if gen is None:
            raise DistributionSpecError("Unknown distribution signature %s" % str(sig))

        self.rv = gen.makeRV(self.argDict)  # generate a frozen RV with the specified arguments

    def getKeys(self):
        return self.child.keys()

    def isTrialFunc(self):
        return bool(self.trialFunc)

    def isLinked(self):
        return self._isLinked

    def linkedParameter(self):
        return self.argDict['parameter'] if self._isLinked else None

    def ppf(self, *args):
        """
        ppf() takes a first arg that can be a scalar value (percentile) or a list
        of percentiles, which is how we use it in this application.
        """
        return self.rv.ppf(*args)

    def loadTrialFunc(self):

        funcRef = self.modDict['apply']
        if not '.' in funcRef:
            return None

        if not self.trialFuncDir:
            self.trialFuncDir = getParam('MCS.TrialFuncDir')

        modname, objname = funcRef.rsplit('.', 1)
        modulePath = pathjoin(self.trialFuncDir, modname + '.py')
        try:
            trialFunc = loadObjectFromPath(objname, modulePath)
        except Exception as e:
            raise PygcamMcsUserError("Failed to load trial function '{}': {}".format(funcRef, e))

        return trialFunc

class XMLPythonFunc(XMLTrialData):
    """
    Implements user-defined Python function to be called to generate a series of
    values. The func can access parameters by calling XMLParameter.getInstances(),
    or XMLParameter.getInstance(name) to get one by name.

    The XMLSchema ensures the format is pkg.mod.submod.func or a legal variant.
    """
    def __init__(self, element, param):
        super().__init__(element, param)
        self.func = importFromDotSpec(element.text)

    def ppf(self, *args):
        """
        Call the function specified in the XML file, passing in the arguments to
        the ppf(), which should be a list of percentile values for which to return
        values from whatever underlies this Python function.

        :param args: the list of percentile values for which to return values. These
          can be ignored, e.g., if the function computes some values based on other
          trial data.
        :return: array-like
        """
        return self.func(self.param, *args)


class XMLDataFile(XMLTrialData):
    """
    Holds DataFrames representing files already loaded, keyed by abs pathname.
    A single data file can hold vectors of values for multiple Parameters; this
    way the file is loaded only once. This can be used to load pre-generated
    trial data, e.g. exported from other software.

    Two different file formats are recognized. If the filename ends in '.tsv',
    the file is assumed to be tab-delimited and the first column is treated as the
    index, though the numbering is reset. If the filename doesn't end in '.tsv',
    it's assumed to be a CSV file with no index present, just data columns.

    The reason for this difference is to support the legacy approach (.tsv) as
    well as a new approach.
    """
    cache = OrderedDict()

    @classmethod
    def getData(cls, pathname):
        """
        Return the DataFrame created by loading the file at pathname. Read the
        file if it's not already in the cache, otherwise, just return the stored DF.
        """
        pathname = os.path.abspath(pathname)    # use canonical name for cache

        if pathname in cls.cache:
            return cls.cache[pathname]

        if pathname.endswith('.tsv'):
            df = pd.read_table(pathname, sep='\t', index_col=0)
            df.reset_index(inplace=True)
        else:
            df = pd.read_csv(pathname, index_col=False)
        cls.cache[pathname] = df
        return df

    @classmethod
    def decache(cls):
        cls.cache = OrderedDict()

    def __init__(self, element, param):
        super().__init__(element, param)
        self.filename = filename = self.getFilename()
        self.df  = self.getData(filename)

    def getFilename(self):
        return os.path.expanduser(self.element.text)

    def ppf(self, *args):
        'Pseudo-ppf that just returns a column of data from the cached dataframe.'
        name   = self.param.getName()
        count  = len(args[0])

        if name not in self.df:
            filename = self.getFilename()
            raise PygcamMcsUserError(f"Variable '{name}' was not found in '{filename}'")

        vector = self.df[name]

        if len(vector) < count:
            # get the smallest integer number of repeats of the
            # vector to meet or exceed the desired count
            repeats = int(ceil(float(count)/len(vector)))
            vector  = np.array(list(vector) * repeats)

        return vector[:count]


class XMLVariable(XMLWrapper):
    """
    Simple variable that wraps an Element and provides methods to get, set,
    cache, and restore Element values. This is subclassed by XMLRandomVar
    to provide a ppf() function for generating samples.
    """
    def __init__(self, element, param, varNum=None):
        super().__init__(element)
        self.param       = param
        self.paramPath   = None
        self.storedValue = None      # cached float value

        # N.B. "is not None" is required because "not element" isn't guaranteed to work.
        if element is not None:      # For shared RVs, XMLParameter creates XMLRandomVar with element=None
            self.storeFloatValue()   # We refer to stored value when updating the XML tree for each trial

        # Save the column in the trailMatrix with our values. This is passed
        # in when XMLVariables are instantiated directly (for shared variables)
        # and set automatically during initialization of XMLRandomVariables.
        self.varNum = varNum

    def getParameter(self):
        return self.param

    def getVarNum(self):
        return self.varNum

    def setVarNum(self, varNum):
        self.varNum = varNum

    def getValue(self):
        return self.element.text

    def setValue(self, value):
        """
        Set the value of the element stored in an XMLVariable.
        """
        elt = self.getElement()
        elt.text = str(value)

    def storeFloatValue(self):
        """
        Store the current value as a float
        """
        value = self.getValue()
        try:
            self.storedValue = float(value)
        except Exception:
            name = self.param.getName()
            raise PygcamMcsSystemError("Value '%s' for parameter %s is not a float" % (value, name))

    def getFloatValue(self):
        return self.storedValue


class XMLRandomVar(XMLVariable):
    """
    Stores pointer to an XMLDistribution (unless this is a shared RV).
    Provides access to values by trial number via valueFunc.
    """
    instances = []

    @classmethod
    def saveInstance(cls, obj):
        # Our position in the RV list identifies our column in the trial matrix
        obj.setVarNum(len(cls.instances))
        cls.instances.append(obj)

    @classmethod
    def getInstances(cls):
        return cls.instances

    @classmethod
    def decache(cls):
        cls.instances = []

    def __init__(self, element, param):
        super().__init__(element, param)
        self.saveInstance(self)

    def ppf(self, *args):
        """
        Pass-thru to the Distribution's ppf() method. Called by LHS.
        """
        dataSrc = self.param.getDataSrc()
        assert dataSrc, 'Called ppf on shared XMLRandomVar (dataSrc is None)'
        return dataSrc.ppf(*args)

class XMLParameter(XMLWrapper):
    """
    Stores information for a single parameter definition, whether a distribution,
    exogenous data, or a Python function. For <Distribution> and <DataFile>, there
    must be an accompanying <Query> node with an xpath expression.
    """

    # Store a list of all parameter instances for use in generating distributions
    instances = OrderedDict()

    def __init__(self, element, tree=None):
        super().__init__(element)
        self.tree = tree
        self.active = getBooleanXML(element.get('active', '1'))

        if not self.active:
            return              # nothing else to do

        XMLParameter.saveInstance(self)

        self.vars    = []    # the list of XMLVariable or XMLRandomVar wrapping Elements from query
        self.rv      = None  # stored here only if the distro is shared across Elements from query
        self.query   = None  # XMLQuery instance
        self.dataSrc = None  # A subclass of XMLTrialData instance
        self.parent  = None

        # documentation fields
        self.desc      = ''
        self.evidence  = ''
        self.rationale = ''
        self.category  = ''
        self.notes     = ''

        children = [elt for elt in element.getchildren() if elt.tag is not ET.Comment]

        for elt in children:
            tag = elt.tag
            text = elt.text

            if tag == QUERY_ELT_NAME:
                self.query = XMLQuery(elt)

            elif tag == DESC_ELT_NAME:
                self.desc = text

            elif tag == EVIDENCE_ELT_NAME:
                self.evidence = text

            elif tag == RATIONALE_ELT_NAME:
                self.rationale = text

            elif tag == CATEGORY_ELT_NAME:
                self.category = text

            elif tag == NOTES_ELT_NAME:
                self.notes = text

            elif tag == CORRELATION_ELT_NAME:
                XMLCorrelation.createCorrelations(elt, self)

            elif tag == DISTRO_ELT_NAME:
                self.child = elt[0]
                childName = self.child.tag

                src_elt = elt # for all but XMLDataFile

                # Handle the two special cases:
                if childName == PYTHON_FUNC_ELT:
                    cls = XMLPythonFunc
                elif childName == DATAFILE_ELT:
                    cls = XMLDataFile
                    src_elt = self.child
                else:
                    cls = XMLDistribution   # child provides distro parameters

                self.dataSrc = cls(src_elt, self)

            elif tag == CSV_QUERY_ELT_NAME:
                self.query = CSVQuery(elt)

            else:
                # Schema validation should prevent this; just an extra precaution.
                raise PygcamMcsUserError(f"Unexpected sub-element of <Parameter>: <{tag}>")

    @classmethod
    def saveInstance(cls, obj):
        name = obj.getName()
        if name in cls.instances:
            raise PygcamMcsUserError(f"Error: attempt to redefine parameter '{name}'")

        cls.instances[name] = obj

    @classmethod
    def getInstances(cls):
        """
        Return a list of the stored XMLParameter objects
        """
        return cls.instances.values()

    @classmethod
    def decache(cls):
        cls.instances = OrderedDict()

    @classmethod
    def getParameterLinks(cls):
        linkedParams = filter(lambda param: param.dataSrc.isLinked(), cls.getInstances())
        linkPairs = [(obj.getName(), obj.dataSrc.linkedParameter()) for obj in linkedParams]
        return linkPairs

    @classmethod
    def getInstance(cls, name):
        """
        Find an XMLParameter instance by name
        """
        return cls.instances.get(name, None)

    @classmethod
    def applyTrial(cls, simId, trialNum, df):
        """
        Copy random values for the given trial from the DataFrame df
        into this parameter's elements.
        """
        instances = cls.getInstances()
        for param in instances:
            if isinstance(param.parent, XMLInputFile) and param.parent.fileType != 'xml':
                _logger.debug(f"Skipping parameter {param.name} (non-XML file)")
                continue

            param.updateElements(simId, trialNum, df)

    def getMode(self):
        s = self.element.get('mode', 'shared')
        return s.lower()

    def isActive(self):
        return self.active

    def hasPythonFunc(self):
        return self.child.tag == PYTHON_FUNC_ELT

    def getDataSrc(self):
        return self.dataSrc

    def getQuery(self):
        return self.query

    # def setTree(self, tree):
    #     self.tree = tree

    def getTree(self):
        return self.tree

    def getVars(self):
        return self.vars

    def setParent(self, parent):
        self.parent = parent

    def runQuery(self, tree):
        """
        Run the XPath query defined for a parameter, save the set of elements found.
        If `tree` is None, the XMLRandomVars are created, but the query isn't run.
        This is used by "gensim" to create the CSV file holding the trial data.
        """
        if not self.query:
            if tree is not None and not self.dataSrc.isTrialFunc():
                raise PygcamMcsUserError("XMLParameter %s has no <Query> and no trial function" % self.getName())

            # trial functions are handled in updateElements()
            self.rv = XMLRandomVar(None, self)
            return

        if tree is None:
            elements = []
        else:
            # Query returns a list of Element instances or None
            elements = self.query.runQuery(tree)
            name = self.getName()

            if elements is None or len(elements) == 0:
                xpath = self.query.getXPath()
                raise PygcamMcsUserError(f"XPath query '{xpath}' returned nothing for parameter {name}")

            _logger.debug(f"Param {name}: {len(elements)} elements found")

        if self.dataSrc.isShared():
            self.rv = XMLRandomVar(None, self)   # Allocate an RV and have all variables share its varNum
            varNum = self.rv.getVarNum()
            vars = [XMLVariable(elt, self, varNum=varNum) for elt in elements]
        else:
            # TBD: this won't work without running the query, but it's not used for now...
            _logger.warn("Called XMLParameter.runQuery without 'tree' for independent element RVs")
            # XMLRandomVar assigns varNum directly
            vars = [XMLRandomVar(elt, self) for elt in elements]

        # Add these to the list since we might be called for multiple scenarios
        self.vars.extend(vars)

    def updateElements(self, simId, trialNum, df):
        """
        Update an element's text (assuming it's a number) by multiplying
        it by a factor, adding a delta, or substituting a given value.
        """
        dataSrc = self.dataSrc
        if dataSrc.isTrialFunc():
            otherArgs = dataSrc.otherArgs or {}
            dataSrc.trialFunc(self, simId, trialNum, df, **otherArgs)
            return

        if not self.vars:
            raise PygcamMcsSystemError("Called updateElements with no variables defined in self.vars")

        isFactor = dataSrc.isFactor()
        isDelta  = dataSrc.isDelta()

        # Update all elements referenced by our list of XMLVariables (or of their subclass, XMLRandomVar)
        for var in self.vars:
            if var.getElement() is None:    # Skip shared RVs, which don't point to an XML element
                _logger.debug(f"Skipping shared element for {var}")
                continue

            originalValue = var.getFloatValue()  # apply factor and delta to cached, original value

            varName = var.getParameter().getName()
            randomValue = df.loc[trialNum, varName]

            newValue = randomValue * originalValue if isFactor else \
                ((randomValue + originalValue) if isDelta else randomValue)

            if hasattr(dataSrc, 'modDict'):
                modDict = dataSrc.modDict
                if modDict['lowbound'] is not None:
                    newValue = max(newValue, modDict['lowbound'])

                if modDict['highbound'] is not None:
                    newValue = min(newValue, modDict['highbound'])

            # Set the value in the cached tree so it can be written to trial's local-xml dir
            var.setValue(newValue)


class XMLRelFile(XMLFile):
    """
    A minor extension to XMLFile to store the original relative pathname
    that was indicated in the config file identifying this file.
    """
    def __init__(self, mapper : SimFileMapper, inputFile, rel_path):
        self.inputFile = inputFile
        self.relPath = rel_path

        # TBD Not sure how the following ever worked. (Did it?)
        # if relPath.startswith('../input') or relPath.startswith('../../trial-xml'):
        #     absPathRoot = mapper.sandbox_exe_dir
        #     #trial_dir = mapper.trial_dir()
        # else:
        #     absPathRoot = mapper.get_sim_local_xml()
        #
        # absPath = pathjoin(absPathRoot, relPath, abspath=True)

        abs_path = pathjoin(mapper.sandbox_exe_dir, rel_path, abspath=True)
        super().__init__(abs_path)

    def getRelPath(self):
        return self.relPath

    def getAbsPath(self):
        return self.getFilename()

    # def saveSomewhere(self):
    #     # Save the modified file somewhere for each trial. Maybe in trial-xml?
    #     pass


class XMLInputFile(XMLWrapper):
    """
    <InputFile> abstraction that represents the XML input file(s) that are associated
    with a given <ScenarioComponent> name. This is necessary because there may be
    different versions of the file for this name in different scenarios. Each instance
    of XMLInputFile holds a set of XMLRelFile instances which each represent an actual
    GCAM input file. Each of these may be referenced from multiple scenarios.

    Also supports generating trial data to be used with CSV files in the GCAM data system.
    In this case use <InputFile name="whatever" type="csv">
    """

    # Maps a relative filename to an XMLRelFile objects that holds the parsed XML.
    # Exists to ensure that each file is read only once. This is a class variable
    # because the same XML file may be referenced by multiple scenarios and we want
    # to edit each only once.
    xmlFileMap = OrderedDict()

    @classmethod
    def getModifiedXMLFiles(cls):
        return cls.xmlFileMap.values()

    @classmethod
    def decache(cls):
        cls.xmlFileMap.clear()

    def __init__(self, element):
        super().__init__(element)
        self.parameters = OrderedDict()
        self.element = element
        self.pathMap = defaultdict(set)
        self.xmlFiles = []
        self.writeFuncs = OrderedDict()    # keyed by funcRef; values are loaded fn objects
        self.writeFuncDir = None
        self.fileType = element.get('type', 'xml')

        # User can define functions to call before writing modified XML files.
        # Write function specification is of the form "myPackage.myModule.myFunc".
        # The function must take 1 argument: the XMLInputFile instance. It can make
        # any desired modifications to the XML tree prior to writing it for each trial.
        writeFuncSpec = element.findtext(WRITE_FUNC_ELT, default=[])
        self.loadWriteFunc(writeFuncSpec)

        # Parameters are described once here, but may be applied to multiple files
        self.findAndSaveParams(element)

    def loadWriteFunc(self, funcRef):
        if not funcRef or '.' not in funcRef or funcRef in self.writeFuncs:
            return None

        if not self.writeFuncDir:
            self.writeFuncDir = getParam('MCS.WriteFuncDir')

        modname, objname = funcRef.rsplit('.', 1)
        modulePath = pathjoin(self.writeFuncDir, modname + '.py')
        try:
            fn = loadObjectFromPath(objname, modulePath)
        except Exception as e:
            raise PygcamMcsUserError(f"Failed to load trial function '{funcRef}': {e}")

        self.writeFuncs[funcRef] = fn

    def findAndSaveParams(self, element):
       findAndSave(element, PARAM_ELT_NAME, XMLParameter, self.parameters,
                   testFunc=XMLParameter.isActive, parent=self)

    def getComponentName(self):
        """
        Return the name attribute of the element for this <InputFile>, which is a
        unique tag identifying a "logical" file, which may appear in different versions
        in various scenarios, depending on what those scenarios needed to modify.
        """
        name = self.element.get('name')
        return name

    def mergeParameters(self, element):
        """
        Save the parameters associated with the given <InputFile> element within
        self since it holds additional definitions for the same file. This allows
        a single input file to be referenced by multiple groups of parameters.
        """
        eltName = element.get('name')
        compName = self.getComponentName()
        assert compName == eltName, f"mergeParameters: InputFile name mismatch: {compName} and {eltName}"

        self.findAndSaveParams(element)

    def loadFiles(self, mapper: SimFileMapper):
        """
        Find the distinct pathnames associated with our component name. Each scenario
        that refers to this path is stored in a set in self.inputFiles, keyed by pathname.
        The point is to read and update the target file only once, even if referred to
        multiple times.
        """
        import copy

        if self.fileType != 'xml':
            return

        if not mapper.is_baseline:
            _logger.debug(f"loadFiles: not loading files for non-baseline scenario {mapper.scenario}")
            return

        # Parameter component name identifies element in the config file, e.g., "land2"
        compName = self.getComponentName()
        _logger.info(f"loadFiles: loading files for component {compName}")

        ctx = copy.copy(mapper.context)  # TBD: not sure this is necessary
        mapper.set_context(ctx)

        scenario_name = mapper.scenario
        ctx.setVars(scenario=scenario_name)

        config_path = mapper.get_config_version(version=FileVersions.TRIAL_XML)
        # config_path = mapper.copy_config_version(FileVersions.LOCAL_XML, FileVersions.TRIAL_XML)
        config_file = XMLConfigFile.get_instance(config_path)

        # If compName ends in '.xml', assume its value is the full relative path, with
        # substitution for {scenario}, e.g., "../../trial-xml/{scenario}/mcsValues.xml"
        isXML = compName.lower().endswith('.xml')
        rel_path = compName if isXML else config_file.get_component_pathname(compName)

        # If another scenario "registered" this XML file, we don't do so again.
        if not rel_path in self.xmlFileMap:
            xmlFile = XMLRelFile(mapper, self, rel_path)
            self.xmlFileMap[rel_path] = xmlFile  # unique for all scenarios so we read once
            self.xmlFiles.append(xmlFile)        # per input file in one scenario

    def runQueries(self):
        """
        Run the queries for all the parameters in this <InputFile> on each of
        the physical XMLRelFiles associated with this XMLInputFile.
        """
        if self.fileType != 'xml':
            return

        for param in self.parameters.values():
            if not param.isActive():
                continue

            # Run the query on all the files associated with this abstract InputFile
            for xmlFile in self.xmlFiles:
                tree = xmlFile.getTree()
                param.runQuery(tree)        # accumulates elements from multiple files

    def generateRandomVars(self):
        """
        Called during 'gensim' to generate XMLRandomVars, save variable names to
        the DB, and save the CSV file with all trial data. No need to actually
        run the queries at this point.
        """
        tuples = []

        for param in self.parameters.values():
            if param.isActive():
                pname = param.getName()
                desc  = 'Auto-generated parameter'
                tuples.append((pname, desc))
                param.runQuery(None)    # side-effect is to generate XML RVs

        # If a file (e.g., protected land) has only a writeFunc defined, there will be no parameters
        if tuples:
            #_logger.debug("Saving tuples to db: %s", tuples)
            db = getDatabase()
            db.saveParameterNames(tuples)

    def callFileFunctions(self, xmlFile, trialDir):
        """
        Call any defined per-input-file functions to allow arbitrary
        manipulation of XML after applying all distributions.

        :param xmlFile: (XMLFile or subclass) container for file being operated on
        :param trialDir: (str) this trial's trial-dir
        """
        # TBD: allow fn spec in elt.text or as name attribute, in which case, pass kwargs
        # TBD: specified in elt.text as writeFunc(self, xmlFile, trialDir, **kwargs)
        for fn in self.writeFuncs.values():
            try:
                fn(self, xmlFile, trialDir)     # fn can modify self.tree as needed
            except Exception as e:
                raise PygcamMcsUserError(f"Call to user WriteFunc '{fn}' failed: {e}")


class XMLParameterFile(XMLFile):
    """
    Represents the overall parameters.xml file.
    """
    def __init__(self, filename):
        super().__init__(filename, schemaPath='mcs/etc/parameter-schema.xsd')

        # XMLInputFiles keyed by scenario component name
        inputFiles = self.inputFiles = OrderedDict()

        # Can't use "findAndSave" here since we need to append if a filename is repeated
        for elt in self.tree.iterfind(INFILE_ELT_NAME):
            compName = elt.get('name')
            if compName in inputFiles:
                inputFileObj = inputFiles[compName]
                inputFileObj.mergeParameters(elt)
            else:
                inputFiles[compName] = XMLInputFile(elt)

        # Match all the Correlation "with" names to actual parameter definitions
        XMLCorrelation.finishSetup()

        _logger.debug(f"Loaded parameter file: {filename}")

    def loadInputFiles(self, mapper):
        """
        Load the input files, for each scenario in scenario_names. Scenarios are
        found in {simDir}/{scenName}. WHY FOR EACH SCENARIO?
        """
        for inputFile in self.inputFiles.values():
            # inputFile.loadFiles(mapper, scenario_names, writeConfigFiles=writeConfigFiles)
            inputFile.loadFiles(mapper)

    def getFilename(self):
        return self.filename

    def runQueries(self):
        for obj in self.inputFiles.values():
            obj.runQueries()

    def generateRandomVars(self):
        for obj in self.inputFiles.values():
            obj.generateRandomVars()

    def writeLocalXmlFiles(self, mapper):
        """
        Write copies of all modified XML files
        """
        config_path = mapper.get_config_version(version=FileVersions.TRIAL_XML)
        config_file = XMLConfigFile.get_instance(config_path)

        trial_dir = mapper.trial_dir()
        scen_trial_dir = pathjoin(trial_dir, TRIAL_XML_NAME, mapper.scenario)

        xmlFiles = XMLInputFile.getModifiedXMLFiles()

        for xmlFile in xmlFiles:
            rel_path = xmlFile.getRelPath()
            abs_path = pathjoin(scen_trial_dir, os.path.basename(rel_path), normpath=True)

            # TBD: Might be cleaner to call file func on .xml file rather than on tree
            # Call per-InputFile functions, if defined.
            inputFile = xmlFile.inputFile
            inputFile.callFileFunctions(xmlFile, trial_dir)

            if os.path.exists(abs_path):
                # remove it to avoid writing through a symlink to the original file
                os.unlink(abs_path)

            _logger.info(f"Writing {abs_path}")
            xmlFile.tree.write(abs_path, xml_declaration=True, pretty_print=True)

            # update config file to reference the new path
            comp_name = inputFile.getComponentName()
            if not comp_name.lower().endswith('.xml'):
                exe_rel_path = os.path.relpath(abs_path, start=mapper.sandbox_exe_dir)
                config_file.update_component_pathname(comp_name, exe_rel_path)

        config_file.write()

    def dump(self):
        print(f"Parameter file: {self.getFilename()}")
        for obj in self.inputFiles.values():
            obj.dump()

def decache():
    '''
    Clear all instance caches so a new run can begin cleanly
    '''
    CachedFile.decache()
    XMLConfigFile.decache()
    XMLCorrelation.decache()
    XMLDataFile.decache()
    XMLRandomVar.decache()
    XMLParameter.decache()
    XMLInputFile.decache()
    XMLDistribution.decache()
