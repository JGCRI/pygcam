# Created on July 5, 2013
#
# Copyright (c) 2013-2017. The Regents of the University of California (Regents).
# See the file COPYRIGHT.txt for details.

from collections import OrderedDict, defaultdict
from lxml import etree as ET
from math import ceil
import numpy as np
import os
import pandas as pd

from ..config import getParam
from ..log import getLogger
from ..utils import importFromDotSpec
from ..XMLFile import XMLFile

from .Database import getDatabase
from .distro import DistroGen
from .error import PygcamMcsUserError, PygcamMcsSystemError, DistributionSpecError
from .util import mkdirs, loadObjectFromPath
from .XML import XMLWrapper, findAndSave, getBooleanXML
from .XMLConfigFile import XMLConfigFile

_logger = getLogger(__name__)

# XML parameter file element tags
INFILE_ELT_NAME      = 'InputFile'
PARAMLIST_ELT_NAME   = 'ParameterList'
PARAM_ELT_NAME       = 'Parameter'
QUERY_ELT_NAME       = 'Query'
DESC_ELT_NAME        = 'Description'
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
        super(XMLCorrelation, self).__init__(element)
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

        for i in xrange(count):
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
        super(XMLQuery, self).__init__(element)
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


class XMLTrialData(XMLWrapper):
    """
    An abstract class that provides the protocol required of classes that can produce
    trial data, i.e., XMLDistribution, XMLDataFile, or XMLPythonFunc
    """
    def __init__(self, element, param):
        super(XMLTrialData, self).__init__(element)
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
        super(XMLDistribution, self).__init__(element, param)

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
                    raise DistributionSpecError("Failed to evaluate expression {}: {}".format(codeStr, e))

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
        _logger.debug("<Distribution %s, %s>", ' '.join(map(lambda pair: '%s="%s"' % pair, element.items())), sig)

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
        modulePath = os.path.join(self.trialFuncDir, modname + '.py')
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
        super(XMLPythonFunc, self).__init__(element, param)
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

        df = pd.read_table(pathname, sep='\t', index_col=0)
        df.reset_index(inplace=True)
        cls.cache[pathname] = df
        return df

    @classmethod
    def decache(cls):
        cls.cache = OrderedDict()

    def __init__(self, element, param):
        super(XMLDataFile, self).__init__(element, param)
        filename = self.getFilename()
        self.df  = self.getData(filename)

    def getFilename(self):
        return os.path.expanduser(self.element.text)

    def ppf(self, *args):
        'Pseudo-ppf that just returns a column of data from the cached dataframe.'
        name   = self.param.getName()
        count  = len(args[0])

        if name not in self.df:
            raise PygcamMcsUserError("Variable '%s' was not found in '%s'" % self.getFilename())

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
        super(XMLVariable, self).__init__(element)
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
        super(XMLRandomVar, self).__init__(element, param)
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
        super(XMLParameter, self).__init__(element)
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
        self.desc    = ''    # documentation

        children = [elt for elt in element.getchildren() if elt.tag is not ET.Comment]
        maxChildren = 4
        assert len(children) <= maxChildren, \
            "<Parameter> cannot have more than %d children. (The XMLSchema is broken.)" % maxChildren

        for elt in children:
            tag = elt.tag

            if tag == QUERY_ELT_NAME:
                self.query = XMLQuery(elt)

            elif tag == CORRELATION_ELT_NAME:
                XMLCorrelation.createCorrelations(elt, self)

            elif tag == DESC_ELT_NAME:
                self.desc = elt.text

            # XMLSchema ensures that the only other tag is Distribution
            # TBD: test for DISTRIBUTION_ELT_NAME explicitly
            else:
                self.child = elt[0]
                childName = self.child.tag

                # Handle the two special cases:
                if childName == PYTHON_FUNC_ELT:
                    cls = XMLPythonFunc
                elif childName == DATAFILE_ELT:
                    cls = XMLDataFile
                else:
                    cls = XMLDistribution   # child provides distro parameters

                self.dataSrc = cls(elt, self)

    @classmethod
    def saveInstance(cls, obj):
        name = obj.getName()
        if name in cls.instances:
            raise PygcamMcsUserError("Error: attempt to redefine parameter '%s'" % name)

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
            if not self.dataSrc.isTrialFunc():
                raise PygcamMcsUserError("XMLParameter %s has no <Query> and no trial function" % self.getName())

            # trial functions are handled in updateElements()
            self.rv = XMLRandomVar(None, self)
            return

        if tree is None:
            elements = []
        else:
            # Query returns a list of Element instances or None
            elements = self.query.runQuery(tree)
            if elements is None or len(elements) == 0:
                raise PygcamMcsUserError("XPath query '%s' returned nothing for parameter %s" % (self.query.getXPath(), self.getName()))

            _logger.debug("Param %s: %d elements found", self.getName(), len(elements))

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
                _logger.debug("Skipping shared element for %s", var)
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


def trialRelativePath(relPath, prefix):
    """
    Convert a pathname that was relative to "exe" to be relative to "exe/../../trial-xml" instead.
    For example, "../input/gcamdata/foo.xml" becomes "../../trial-xml/input/gcamdata/foo.xml".
    """
    parentDir = '../'
    if not relPath.startswith(parentDir):
        raise PygcamMcsUserError("trialRelativePath: expected path starting with '%s', got '%s'" % \
                                 (parentDir, relPath))

    newPath = os.path.join(prefix, 'trial-xml', relPath[len(parentDir):])
    return newPath


class XMLRelFile(XMLFile):
    """
    A minor extension to XMLFile to store the original relative pathname
    that was indicated in the config file identifying this file.
    """
    def __init__(self, inputFile, relPath, simId):
        from .util import getSimLocalXmlDir

        self.inputFile = inputFile
        self.relPath = relPath

        scenarioDir = getSimLocalXmlDir(simId)
        absPath = os.path.abspath(os.path.join(scenarioDir, relPath))

        super(XMLRelFile, self).__init__(absPath)

    def getRelPath(self):
        return self.relPath

    def getAbsPath(self):
        return self.getFilename()

    def saveSomewhere(self):
        # Save the modified file somewhere for each trial. Maybe in trial-xml?
        pass


class XMLInputFile(XMLWrapper):
    """
    <InputFile> abstraction that represents the XML input file(s) that are associated
    with a given <ScenarioComponent> name. This is necessary because there may be
    different versions of the file for this name in different scenarios. Each instance
    of XMLInputFile holds a set of XMLRelFile instances which each represent an actual
    GCAM input file. Each of these may be referenced from multiple scenarios.
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
        cls.xmlFileMap = OrderedDict()

    def __init__(self, element):
        super(XMLInputFile, self).__init__(element)
        self.parameters = OrderedDict()
        self.element = element
        self.pathMap = defaultdict(set)
        self.xmlFiles = []
        self.writeFuncs = OrderedDict()    # keyed by funcRef; values are loaded fn objects
        self.writeFuncDir = None

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
        modulePath = os.path.join(self.writeFuncDir, modname + '.py')
        try:
            fn = loadObjectFromPath(objname, modulePath)
        except Exception as e:
            raise PygcamMcsUserError("Failed to load trial function '%s': %s" % (funcRef, e))

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
        assert compName == eltName, \
            "mergeParameters: InputFile name mismatch: %s and %s" % (compName, eltName)

        self.findAndSaveParams(element)

    def loadFiles(self, context, scenNames, writeConfigFiles=True):
        """
        Find the distinct pathnames associated with our component name. Each scenario
        that refers to this path is stored in a set in self.inputFiles, keyed by pathname.
        The point is to read and update the target file only once, even if referred to
        multiple times.
        """
        import copy

        compName = self.getComponentName()  # an identifier in the config file, e.g., "land2"

        useCopy = not writeConfigFiles  # if we're not writing the configs, use the saved original

        ctx = copy.copy(context)
        simId = context.simId

        for scenName in scenNames:
            ctx.setVars(scenario=scenName)
            configFile = XMLConfigFile.getConfigForScenario(ctx, useCopy=useCopy)

            # If compName ends in '.xml', assume its value is the full relative path, with
            # substitution for {scenario}, e.g., "../local-xml/{scenario}/mcsValues.xml"
            isXML = compName.lower().endswith('.xml')
            relPath = compName if isXML else configFile.getComponentPathname(compName)

            # If another scenario "registered" this XML file, we don't do so again.
            if not relPath in self.xmlFileMap:
                xmlFile = XMLRelFile(self, relPath, simId)
                self.xmlFileMap[relPath] = xmlFile  # unique for all scenarios so we read once
                self.xmlFiles.append(xmlFile)       # per input file in one scenario

            # TBD: In either case, we need to update the config files' XML trees because
            # TBD: some parameter(s) modify the file for this component, in all cases.
            # TBD: This new path has to be coordinated between config file and actual file.
            if writeConfigFiles and not isXML:
                trialRelPath = trialRelativePath(relPath, '../..')
                configFile.updateComponentPathname(compName, trialRelPath)

    def runQueries(self):
        """
        Run the queries for all the parameters in this <InputFile> on each of
        the physical XMLRelFiles associated with this XMLInputFile.
        """
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
                raise PygcamMcsUserError("Call to user WriteFunc '%s' failed: %s" % (fn, e))


class XMLParameterFile(XMLFile):
    """
    Represents the overall parameters.xml file.
    """
    def __init__(self, filename):
        super(XMLParameterFile, self).__init__(filename, schemaPath='mcs/etc/parameter-schema.xsd')

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

        _logger.debug("Loaded parameter file: %s", filename)

    def loadInputFiles(self, context, scenNames, writeConfigFiles=True):
        """
        Load the input files, for each scenario in scenNames. Scenarios are
        found in {simDir}/{scenName}.
        """
        for inputFile in self.inputFiles.values():
            inputFile.loadFiles(context, scenNames, writeConfigFiles=writeConfigFiles)

        if writeConfigFiles:
            # Writes all modified configs. Config files' XML trees are updated
            # as InputFile elements are processed.
            XMLConfigFile.writeAll(context)

    def getFilename(self):
        return self.filename

    def runQueries(self):
        for obj in self.inputFiles.values():
            obj.runQueries()

    def generateRandomVars(self):
        for obj in self.inputFiles.values():
            obj.generateRandomVars()

    def writeLocalXmlFiles(self, trialDir):
        """
        Write copies of all modified XML files
        """
        xmlFiles = XMLInputFile.getModifiedXMLFiles()

        for xmlFile in xmlFiles:
            exeRelPath = xmlFile.getRelPath()
            absPath = trialRelativePath(exeRelPath, trialDir)

            # Ensure that directories down to basename exist
            dirname = os.path.dirname(absPath)
            mkdirs(dirname)

            # TBD: Might be cleaner to call file func on .xml file rather than on tree
            # Call per-InputFile functions, if defined.
            inputFile = xmlFile.inputFile
            inputFile.callFileFunctions(xmlFile, trialDir)

            if os.path.exists(absPath):
                # remove it to avoid writing through a symlink to the original file
                _logger.debug("Removing %s", absPath)
                os.unlink(absPath)

            _logger.info("XMLParameterFile: writing %s", absPath)
            xmlFile.tree.write(absPath, xml_declaration=True, pretty_print=True)

    def dump(self):
        print("Parameter file: %s" % self.getFilename())
        for obj in self.inputFiles.values():
            obj.dump()

def decache():
    '''
    Clear all instance caches so a new run can begin cleanly
    '''
    XMLConfigFile.decache()
    XMLCorrelation.decache()
    XMLDataFile.decache()
    XMLRandomVar.decache()
    XMLParameter.decache()
    XMLInputFile.decache()
    XMLDistribution.decache()
