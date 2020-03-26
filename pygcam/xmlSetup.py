'''
.. Created on: 8/21/16

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from collections import OrderedDict
import glob
import os
import sys

from .config import getParam, getParamAsBoolean, pathjoin
from .error import PygcamException, SetupException
from .log import getLogger
from .utils import getBooleanXML, symlinkOrCopyFile, splitAndStrip
from .xmlEditor import XMLEditor, getCallableMethod, CachedFile
from .XMLFile import XMLFile, McsValues

_logger = getLogger(__name__)

_tab = ' ' * 3

# Return a class (or any object) defined in this module
def classForString(className):
    return getattr(sys.modules[__name__], className)

def _classForNode(node):
    className = node.tag.capitalize()
    cls = classForString(className)
    return cls(node)

def iterateList(scenarioSetup, cls, node, expandFunc, iterators):
    """
    Recursively evaluate iterators for generalized nested loop, adding
    values to the templateDict in scenarioSetup. Expand ScenarioGroup
    at the inner-most loop, when recursion ends.
    """
    iterName = iterators[0]
    otherIters = iterators[1:]
    iterator = scenarioSetup.getIterator(iterName)
    templateDict = scenarioSetup.templateDict

    for value in iterator.values:
        templateDict[iterName] = value

        if otherIters:
            iterateList(scenarioSetup, cls, node, expandFunc, otherIters)
        else:
            obj = cls(node)
            expandFunc(obj)

#
# Classes to parse and run scenario setup files.
# (See pygcam/etc/scenarios-schema.xsd).
#
class ScenarioSetup(object):

    def __init__(self, node):
        self.name = node.get('name', '')    # unused currently
        self.defaultGroup = node.get('defaultGroup')

        # These serve as a no-op on the build-out pass. The directory vars are
        # converted when the scenario is run and the directories are known.
        self.templateDict = {'scenarioDir' : '{scenarioDir}',
                             'baselineDir' : '{baselineDir}'}

        self.iterators = [Iterator(item) for item in node.findall('iterator')]
        self.iteratorDict = {obj.name : obj for obj in self.iterators}

        templateGroups = [ScenarioGroup(item) for item in node.findall('scenarioGroup')]

        # Create a dict of expanded groups for lookup
        self.groupDict = OrderedDict()
        self.expandGroups(templateGroups)   # saves into groupDict

    def scenariosInGroup(self, groupName=None):
        group = self.groupDict[groupName or self.defaultGroup]
        return group.scenarioNames()

    def baselineForGroup(self, groupName=None):
        group = self.groupDict[groupName or self.defaultGroup]
        return group.baseline

    def getIterator(self, name):
        try:
            return self.iteratorDict[name]
        except KeyError:
            raise SetupException("Iterator '%s' is not defined" % name)

    documentCache = {}

    @classmethod
    def parse(cls, filename):
        """
        Parse an XML file with query descriptions.
        :param filename: (str) the name of the XML file to read
        :return: a QueryFile instance.
        """
        if filename in cls.documentCache:
            _logger.debug('Found scenario file "%s" in cache', filename)
            return cls.documentCache[filename]

        xmlFile = XMLFile(filename, schemaPath='etc/scenarios-schema.xsd', conditionalXML=True)
        obj = cls(xmlFile.getRoot())

        cls.documentCache[filename] = obj      # cache it
        return obj

    def writeXML(self, stream, indent=0):
        stream.write(_tab * indent + '<setup>\n')

        # No need to show these once expanded
        # for obj in self.iterators:
        #     obj.writeXML(stream, indent + 1)

        for obj in self.groupDict.values():
            obj.writeXML(stream, indent + 1)

        stream.write(_tab * indent + '</setup>\n')

    def expandGroups(self, templateGroups):
        '''
        Expand the `templateGroups`, which may contain names based
        on iterators, into final scenarioGroups without iterators.
        Recursively expands scenarios within groups.
        '''
        templateDict = self.templateDict

        def expand(group):
            group.name = group.name.format(**templateDict)
            group.expandScenarios(self, templateDict)
            self.groupDict[group.name] = group

        for templateGroup in templateGroups:
            iterName = templateGroup.iteratorName

            if not iterName:
                expand(templateGroup)
                continue

            # allow iterator name to be comma-delimited list of iterators
            iterators = splitAndStrip(iterName, ',')
            iterateList(self, ScenarioGroup, templateGroup.node, expand, iterators)

    def run(self, editor, directoryDict, dynamic=False):
        """
        Run the setup for the given XmlEditor subclass.

        :param editor: (XmlEditor) an instance of a subclass of XmlEditor
        :param directoryDict: (dict) directory with values for {scenarioDir}
            {baselineDir}
        :param dynamic: (bool) if True, run only "dynamic" actions; else
           run only static (non-dynamic) actions.
        :return: none
        """
        self.editor = editor
        group = self.groupDict[editor.groupName or self.defaultGroup]
        scenario = group.getFinalScenario(editor.scenario or editor.baseline)

        _logger.debug('Running %s setup for scenario %s', 'dynamic' if dynamic else 'static', scenario.name)
        scenario.run(editor, directoryDict, dynamic=dynamic)

# Iterators for float and int that *included* the stop value.
# That is, terminal condition is "<= stop", not "< stop" as
# with the standard Python range() function.
def frange(start, stop, step=1.0):
    while start <= stop:
        yield start
        start += step

def irange(start, stop, step=1):
    while start <= stop:
        yield start
        start += step

class Iterator(object):
    def __init__(self, node):
        self.name = node.get('name')
        self.min  = self.max = self.step = self.values = self.format = None

        typeName  = node.get('type', 'list')
        isNumeric = typeName in ('int', 'float')
        self.type = iterType = eval(typeName)   # N.B. schema ensures numeric values

        if isNumeric:
            minValue = node.get('min')
            maxValue = node.get('max')
            if not (minValue and maxValue):
                raise SetupException('%s iterator must provide min and max attributes' % typeName)

            self.min  = iterType(minValue)
            self.max  = iterType(maxValue)
            self.step = iterType(node.get('step', 1))
            self.format = node.get('format', '%d' if self.type == int else '%.1f')

            rangeFunc = irange if self.type == int else frange
            self.values = [self.format % value for value in rangeFunc(self.min, self.max, self.step)]

        else: # 'list'
            valuesStr = node.get('values')
            if not valuesStr:
                raise SetupException('list iterator must provide a values attribute')

            self.values = splitAndStrip(valuesStr, ',')

    def __str__(self):
        desc = "<iterator name='%s' type='%s' " % (self.name, self.type.__name__)

        if self.type == list:
            values = ','.join(self.values)
            desc += "values='%s'/>" % values
        else:
            desc += "min='%s' max='%s' step='%s'/>" % (self.min, self.max, self.step)

        return desc

    def writeXML(self, stream, indent=0):
        stream.write(_tab * indent + "%s\n" % self)

class ScenarioGroup(object):
    def __init__(self, node):
        self.node = node
        self.name = node.get('name')
        self.srcGroupDir = node.get('srcGroupDir', '')  # TBD: fix XML docs to refer to this name
        self.useGroupDir = bool(self.srcGroupDir) or getBooleanXML(node.get('useGroupDir', default='0'))
        self.isDefault = getBooleanXML(node.get('default', default='0'))
        self.iteratorName = node.get('iterator')
        self.baselineSource = node.get('baselineSource')
        self.templateScenarios = scenarios = [Scenario(item) for item in node.findall('scenario')]
        self.templateDict = {obj.name: obj for obj in scenarios}
        self.finalDict = OrderedDict()
        self.baseline = None

    def getFinalScenario(self, name):
        try:
            return self.finalDict[name]
        except KeyError:
            raise PygcamException('Scenario "%s" was not found in group "%s"' % (name, self.name))

    def scenarioNames(self):
        return self.finalDict.keys()

    def expandScenarios(self, scenarioSetup, templateDict):
        # Replace the text context in all action elements with expanded version

        # This converts only the iterators. The directories {scenarioDir}
        # and {baselineDir} are converted when the scenario is run.
        def expand(scenario):
            scenario.name = name = scenario.name.format(**templateDict)
            subdir = scenario.node.get('subdir', default=scenario.name)
            scenario.subdir = subdir.format(**templateDict)

            self.finalDict[name] = scenario
            scenario.formatContent(templateDict)
            if scenario.isBaseline:
                if self.baseline:
                    raise SetupException('Group %s declares multiple baselines' % self.name)
                self.baseline = name

        for templateScenario in self.templateScenarios:
            iterName = templateScenario.iteratorName

            if not iterName:
                expand(templateScenario)
                continue

            # allow iterator name to be comma-delimited list of iterators
            iterators = splitAndStrip(iterName, ',')
            iterateList(scenarioSetup, Scenario, templateScenario.node, expand, iterators)

    def writeXML(self, stream, indent=0):
        stream.write('\n')
        stream.write(_tab * indent + '<scenarioGroup name="%s" useGroupDir="%s" srcGroupDir="%s">\n' % \
                     (self.name, int(self.useGroupDir), self.srcGroupDir))

        for obj in self.finalDict.values():
            obj.writeXML(stream, indent + 1)

        stream.write(_tab * indent + '</scenarioGroup>\n')

class Scenario(object):
    def __init__(self, node):
        self.node = node
        self.name = node.get('name')
        self.isBaseline = getBooleanXML(node.get('baseline', default=0))
        self.isActive   = getBooleanXML(node.get('active',   default='1'))
        self.iteratorName = node.get('iterator')
        self.actions = [_classForNode(item) for item in node]
        self.subdir = node.get('subdir', default=self.name)

    def __str__(self):
        return "<scenario name='%s'>" % self.name

    def run(self, editor, directoryDict, dynamic=False):
        for action in self.actions:
            action.run(editor, directoryDict, dynamic=dynamic)

    def formatContent(self, templateDict):
        # This converts only the iterators. The directories {scenarioDir}
        # and {baselineDir} are converted when the scenario is run.
        for action in self.actions:
            action.formatContent(templateDict)

    def writeXML(self, stream, indent=0):
        stream.write(_tab * indent + '<scenario name="%s" baseline="%s">\n' % \
                     (self.name, int(self.isBaseline)))

        for obj in self.actions:
            obj.writeXML(stream, indent + 1)

        stream.write(_tab * indent + '</scenario>\n')

class ConfigActionBase(object):
    def __init__(self, node):
        self.tag  = node.tag
        self.content = node.text
        self.formattedContent = None
        self.dynamic = False

    def formatContent(self, formatDict):
        content = self.formattedContent or self.content
        self.formattedContent = content.format(**formatDict) if content else None

    def writeXML(self, stream, indent=0):
        stream.write(_tab * indent + "%s\n" % self)

class ConfigAction(ConfigActionBase):
    def __init__(self, node):
        super(ConfigAction, self).__init__(node)
        self.name = node.get('name')
        self.dynamic = getBooleanXML(node.get('dynamic', '0'))

    def __str__(self):
        tag = self.tag
        content = self.formattedContent or self.content
        return "<%s name='%s'>%s</%s>" % (tag, self.name, content, tag)

    def run(self, editor, directoryDict, dynamic=False):
        if self.dynamic == dynamic:
            self.formatContent(directoryDict)
            self._run(editor)

class Insert(ConfigAction):
    def __init__(self, node):
        super(Insert, self).__init__(node)
        self.after = node.get('after')

    def __str__(self):
        tag = self.tag
        content = self.formattedContent or self.content
        after = " after='%s'" % self.after if self.after else ''
        return "<%s name='%s'%s>%s</%s>" % (tag, self.name, after, content, tag)

    def _run(self, editor):
        editor.insertScenarioComponent(self.name, self.formattedContent, self.after)

class Add(ConfigAction):
    def _run(self, editor):
        editor.addScenarioComponent(self.name, self.formattedContent)

class Replace(ConfigAction):
    def _run(self, editor):
        editor.updateScenarioComponent(self.name, self.formattedContent)

class Delete(ConfigAction):
    def _run(self, editor):
        editor.deleteScenarioComponent(self.name)

    def __str__(self):
        return "<%s name='%s'/>" % (self.tag, self.name)

class Function(ConfigAction):
    def _run(self, editor):
        name = self.name
        method = getCallableMethod(name)
        if not method:
            raise SetupException("<function name='%s'>: function doesn't exist or is not callable from XML" % name)

        args = "(%s)" % self.formattedContent if self.formattedContent else "()"
        codeStr = "editor.%s%s" % (name, args)
        try:
            eval(codeStr)
        except SyntaxError as e:
            raise SetupException("Failed to evaluate expression %s: %s" % (codeStr, e))

    def __str__(self):
        tag = self.tag
        content = self.formattedContent or self.content
        return "<%s name='%s' dynamic='%s'>%s</%s>" % (tag, self.name, self.dynamic, content, tag)

class If(ConfigActionBase):
    def __init__(self, node):
        super(If, self).__init__(node)
        self.value1 = node.get('value1')
        self.value2 = node.get('value2')
        self.matches = getBooleanXML(node.get('matches', '1'))
        self.actions = [_classForNode(item) for item in node]
        self.formattedValue1 = ''
        self.formattedValue2 = ''

    def __str__(self):
        value1 = self.formattedValue1 or self.value1
        value2 = self.formattedValue2 or self.value2
        return "<%s value1='%s' value2='%s' matches='%s'/>" % (self.tag, value1, value2, self.matches)

    def writeXML(self, stream, indent=0):
        # deprecated
        # value1 = self.formattedValue1 or self.value1
        # value2 = self.formattedValue2 or self.value2

        # output active actions, without the "<if>"
        values = self.formattedValue2.split(',')
        if (self.formattedValue1 in values) == self.matches:
            for obj in self.actions:
                obj.writeXML(stream, indent)

    # N.B. Override superclass method since this runs regardless of dynamic flag
    def run(self, editor, directoryDict, dynamic=False):
        values = splitAndStrip(self.formattedValue2, ',')
        if (self.formattedValue1 in values) == self.matches:
            for action in self.actions:
                action.run(editor, directoryDict, dynamic=dynamic)

    def formatContent(self, formatDict):
        value1 = self.formattedValue1 or self.value1
        value2 = self.formattedValue2 or self.value2

        self.formattedValue1 = value1.format(**formatDict)
        self.formattedValue2 = value2.format(**formatDict)

        for obj in self.actions:
            obj.formatContent(formatDict)

MCSVALUES_FILE = 'mcsValues.xml'

def createXmlEditorSubclass(setupFile, mcsMode=None, cleanXML=True):
    """
    Generate a subclass of the given `superclass` that runs the
    XML setup file given by variable GCAM.ScenarioSetupFile.
    If defined, GCAM.ScenarioSetupClass must be of the form:
    "/path/to/module/dir;module.ClassName]". If the variable
    GCAM.ScenarioSetupClass is empty, the class XMLEditor is
    subclassed directly.

    :param setupFile: (str) the pathname of an XML setup file
    :param mcsMode (str) must be 'trial', 'gensim', or None
    :return: (class) A subclass of the given `superclass`
    """
    setupClass = getParam('GCAM.ScenarioSetupClass')
    if setupClass:
        try:
            modPath, dotSpec = setupClass.split(';', 1)
        except Exception:
            raise SetupException('GCAM.ScenarioSetupClass should be of the form "/path/to/moduleDirectory:module.ClassName", got "%s"' % setupClass)

        try:
            from .utils import importFromDotSpec
            sys.path.insert(0, modPath)
            superclass = importFromDotSpec(dotSpec)

        except PygcamException as e:
            raise SetupException("Can't load setup class '%s' from '%s': %s" % (dotSpec, modPath, e))

        # check that superclass inherits from or is an XMLEditor
        assert issubclass(superclass, XMLEditor), 'GCAM.ScenarioSetupClass must be a subclass of pygcam.XMLEditor'
    else:
        superclass = XMLEditor

    class XmlEditorSubclass(superclass):
        def __init__(self, baseline, scenario, xmlOutputRoot, xmlSrcDir, refWorkspace, groupName,
                     srcGroupDir, subdir, parent=None, mcsMode=None, cleanXML=True):
            self.parentConfigPath = None

            self.scenarioSetup = scenarioSetup = ScenarioSetup.parse(setupFile) #if parent else None

            # deprecated
            # group = scenarioSetup.groupDict[groupName or scenarioSetup.defaultGroup]

            # if not a baseline, create a baseline instance as our parent
            if scenario:
                # TBD: test this in FCIP case where baseline builds on FuelShock
                baselineSubdir = None
                baseXmlOutputRoot = pathjoin(os.path.dirname(xmlOutputRoot), baseline)
                parent = XMLEditor(baseline, None, baseXmlOutputRoot, xmlSrcDir, refWorkspace, groupName,
                                   srcGroupDir, baselineSubdir)

            super(XmlEditorSubclass, self).__init__(baseline, scenario, xmlOutputRoot, xmlSrcDir,
                                                    refWorkspace, groupName, srcGroupDir, subdir,
                                                    parent=parent, mcsMode=mcsMode, cleanXML=cleanXML)
            self.paramFile = None

            # Read shocks from mcsValues.xml if present
            #if self.parent and mcsMode:
            if mcsMode == 'trial':
                # ../../trial-xml/local-xml/base-0/mcsValues.xml
                self.trial_xml_abs = pathjoin(self.xmlOutputRoot, '../trial-xml', normpath=True)
                self.trial_xml_rel = pathjoin('../..', 'trial-xml')

                scenName = self.parent.name if self.parent else self.name
                self.paramFile = pathjoin(self.trial_xml_abs, 'local-xml', self.groupDir,
                                          scenName, MCSVALUES_FILE, normpath=True)

            self.directoryDict = {'scenarioDir': self.scenario_dir_rel,
                                  'baselineDir': self.baseline_dir_rel}

        def setupDynamic(self, args):
            self.groupName = args.group

            super(XmlEditorSubclass, self).setupDynamic(args)

            if self.mcsMode == 'trial':             # TBD: was just "if self.mcsMode" -- test this
                paramFile = self.paramFile
                if paramFile and os.path.lexists(paramFile):
                    self.mcsValues = McsValues(paramFile)

            assert self.scenarioSetup, "XmlEditorSubclass.setupDynamic() was called without having read an XML scenario file"
            self.scenarioSetup.run(self, self.directoryDict, dynamic=True)

            # Add symlinks to any files that were added in the dynamic setup
            dynDir  = self.scenario_dyn_dir_abs
            scenDir = self.scenario_dir_abs
            xmlFiles = glob.glob("%s/*.xml" % scenDir)

            if xmlFiles:
                mode = 'Copy' if getParamAsBoolean('GCAM.CopyAllFiles') else 'Link'
                _logger.info("%s additional static XML files in %s to %s", mode, scenDir, dynDir)
                for xml in xmlFiles:
                    base = os.path.basename(xml)
                    dst = pathjoin(dynDir, base)
                    src = pathjoin(scenDir, base)
                    if not os.path.lexists(dst):
                        symlinkOrCopyFile(src, dst)

            CachedFile.decacheAll()

        def setupStatic(self, args):
            self.groupName = args.group
            scenarioSetup = self.scenarioSetup

            # TBD: test this in FCIP case where baseline builds on FuelShock
            if not self.parent:
                # Before calling setupStatic, we set the parent if there is
                # a declared baseline source. This assumes it is in this
                # project, in a different group directory.
                group = scenarioSetup.groupDict[self.groupName or scenarioSetup.defaultGroup]
                baselineSource = group.baselineSource
                if baselineSource:
                    try:
                        groupName, baselineName = baselineSource.split('/')
                    except ValueError:
                        raise SetupException(
                            'baselineSource error: "%s"; should be of the form "groupDir/baselineDir"' % baselineSource)

                    parentGroup = scenarioSetup.groupDict[groupName]
                    scenario = parentGroup.getFinalScenario(baselineName)
                    if scenario.isBaseline:
                        self.parent = XmlEditorSubclass(baselineName, None, self.xmlOutputRoot, self.xmlSourceDir,
                                                        self.refWorkspace, groupName, group.srcGroupDir, scenario.subdir)
            directoryDict = self.directoryDict

            # not an "else" since parent may be set in "if" above
            if self.parent:
                # patch the template dictionary with the dynamically-determined baseline dir
                directoryDict['baselineDir'] = self.baseline_dir_rel = self.parent.scenario_dir_rel

            super(XmlEditorSubclass, self).setupStatic(args)

            scenarioSetup.run(self, directoryDict, dynamic=False)
            CachedFile.decacheAll()

    return XmlEditorSubclass


def scenarioEditor(scenario):
    setupXml = getParam('GCAM.ScenarioSetupFile')
    editorClass = createXmlEditorSubclass(setupXml, cleanXML=False)

    # we don't need to specify any of these for real since we're just getting the config file
    baseline = ''
    xmlSrcDir = ''
    refWorkspace = ''
    groupName = ''
    srcGroupDir = ''
    subdir = ''

    xmlOutputRoot = pathjoin(getParam('GCAM.SandboxDir'), groupName, scenario, normpath=True)

    editor = editorClass(baseline, scenario, xmlOutputRoot, xmlSrcDir, refWorkspace,
                         groupName, srcGroupDir, subdir, cleanXML=False)
    return editor

def scenarioConfigPath(scenario):
    editor = scenarioEditor(scenario)
    path = editor.cfgPath()
    return path

def scenarioXML(scenario, tag, groupName=None):
    editor = scenarioEditor(scenario)
    path = editor.componentPath(tag)
    groupName = groupName or ''
    absPath = pathjoin(getParam('GCAM.SandboxDir'), groupName, scenario, 'exe', path, abspath=True)
    return absPath

