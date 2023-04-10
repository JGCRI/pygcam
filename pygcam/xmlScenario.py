"""
.. Created on: 8/21/16

.. Classes to parse and run scenario setup file (scenarios.xml).
   See also pygcam/etc/scenarios-schema.xsd.

.. Copyright (c) 2016-2023 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from collections import OrderedDict
import os
import sys

from .config import getParam, getParamAsPath, pathjoin
from .constants import LOCAL_XML_NAME, McsMode
from .error import PygcamException, SetupException
from .log import getLogger
from .utils import getBooleanXML, splitAndStrip
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
    at the innermost loop, when recursion ends.
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


class XMLScenario(object):
    """
    Top-level class for reading and parsing scenarios.xml file.
    """
    documentCache = {}  # parsed XML files are cached here

    @classmethod
    def get_instance(cls, filename=None):
        filename = filename or getParamAsPath('GCAM.ScenariosFile')
        if filename in cls.documentCache:
            _logger.debug('Found scenario file "%s" in cache', filename)
            obj = cls.documentCache[filename]
        else:
            obj = XMLScenario(filename)
            cls.documentCache[filename] = obj      # cache it

        return obj

    def __init__(self, filename):
        """
        Parse an XML file with query descriptions.
        :param filename: (str) the name of the XML file to read
        :return: a QueryFile instance.
        """
        xmlFile = XMLFile(filename, schemaPath='etc/scenarios-schema.xsd', conditionalXML=True)
        root = xmlFile.getRoot()

        self.name = root.get('name', '')    # unused currently
        self.defaultGroup = root.get('defaultGroup')

        # These serve as a no-op on the build-out pass. The directory vars are
        # converted when the scenario is run and the directories are known.
        self.templateDict = {'scenarioDir' : '{scenarioDir}',
                             'baselineDir' : '{baselineDir}'}

        self.iterators = [Iterator(item) for item in root.findall('iterator')]
        self.iteratorDict = {obj.name : obj for obj in self.iterators}

        templateGroups = [ScenarioGroup(item) for item in root.findall('scenarioGroup')]

        # Create a dict of expanded groups for lookup
        self.groupDict = OrderedDict()
        self.expandGroups(templateGroups)   # saves into groupDict

    def getGroup(self, name=None):
        return self.groupDict[name or self.defaultGroup]

    def scenariosInGroup(self, groupName=None):
        group = self.getGroup(groupName)
        return group.scenarioNames()

    def baselineForGroup(self, groupName=None):
        group = self.getGroup(groupName)
        return group.baseline

    def getIterator(self, name):
        try:
            return self.iteratorDict[name]
        except KeyError:
            raise SetupException("Iterator '%s' is not defined" % name)

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
        sbx = editor.sbx

        group = self.getGroup(sbx.scenario_group)
        scenario = group.getFinalScenario(sbx.scenario or sbx.baseline)

        _logger.debug('Running %s setup for scenario %s', 'dynamic' if dynamic else 'static', scenario.name)
        scenario.run(editor, directoryDict, dynamic=dynamic)

# Iterators for float and int that *include* the stop value.
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
            raise PygcamException(f'Scenario "{name}" was not found in group "{self.name}"')

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
                    raise SetupException(f'Group {self.name} declares multiple baselines')
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
        text = f'<scenarioGroup name="{self.name}" useGroupDir="{int(self.useGroupDir)}" srcGroupDir="{self.srcGroupDir}">\n'
        stream.write(_tab * indent + text)

        for obj in self.finalDict.values():
            obj.writeXML(stream, indent + 1)

        stream.write(_tab * indent + '</scenarioGroup>\n')

class Scenario(object):
    def __init__(self, node):
        self.node = node
        self.name = node.get('name')
        self.isBaseline = getBooleanXML(node.get('baseline', default='0'))
        self.isActive   = getBooleanXML(node.get('active',   default='1'))
        self.iteratorName = node.get('iterator')
        self.actions = [_classForNode(item) for item in node]
        self.subdir = node.get('subdir', default=self.name)

    def __str__(self):
        return f"<scenario name='{self.name}'>"

    def run(self, editor, directoryDict, dynamic=False):
        for action in self.actions:
            action.run(editor, directoryDict, dynamic=dynamic)

    def formatContent(self, templateDict):
        # This converts only the iterators. The directories {scenarioDir}
        # and {baselineDir} are converted when the scenario is run.
        for action in self.actions:
            action.formatContent(templateDict)

    def writeXML(self, stream, indent=0):
        text = f'<scenario name="{self.name}" baseline="{int(self.isBaseline)}">\n'
        stream.write(_tab * indent + text)

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
        return f"<{tag} name='{self.name}'>{content}</{tag}>"

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
        after = f" after='{self.after}'" if self.after else ''
        return f"<{tag} name='{self.name}'{after}>{content}</{tag}>"

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
        return f"<{self.tag} name='{self.name}'/>"

class Function(ConfigAction):
    def _run(self, editor):
        name = self.name
        method = getCallableMethod(name)
        if not method:
            raise SetupException(f"<function name='{name}'>: function doesn't exist or is not callable from XML")

        args = f"({self.formattedContent.strip()})" if self.formattedContent else "()"
        codeStr = f"editor.{name}{args}"

        try:
            eval(codeStr)
        except SyntaxError as e:
            raise SetupException(f"Failed to evaluate expression {codeStr}: {e}")

    def __str__(self):
        tag = self.tag
        content = self.formattedContent or self.content
        return f"<{tag} name='{self.name}' dynamic='{self.dynamic}'>{content}</{tag}>"

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
        return f"<{self.tag} value1='{value1}' value2='{value2}' matches='{self.matches}'/>"

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

def createXmlEditorSubclass(setupFile):
    """
    Generate a subclass of the given `superclass` that runs the
    XML setup file given by variable GCAM.ScenariosFile.
    If defined, GCAM.ScenarioSetupClass must be of the form:
    "/path/to/module/dir;module.ClassName]". If the variable
    GCAM.ScenarioSetupClass is empty, the class XMLEditor is
    subclassed directly.

    :param setupFile: (str) the pathname of an XML setup file
    :return: (class) A subclass of the given `superclass`
    """
    setupClass = getParam('GCAM.ScenarioSetupClass')
    if setupClass:
        try:
            modPath, dotSpec = setupClass.split(';', 1)
        except Exception:
            raise SetupException(f'GCAM.ScenarioSetupClass should be of the form '
                                 f'"/path/to/moduleDirectory:module.ClassName", got "{setupClass}"')

        try:
            from .utils import importFromDotSpec
            sys.path.insert(0, modPath)
            superclass = importFromDotSpec(dotSpec)

        except PygcamException as e:
            raise SetupException(f"Can't load setup class '{dotSpec}' from '{modPath}': {e}")

        # check that superclass inherits from or is an XMLEditor
        if not issubclass(superclass, XMLEditor):
            raise SetupException(f"GCAM.ScenarioSetupClass {superclass} is not a subclass of pygcam.XMLEditor")
    else:
        superclass = XMLEditor

    # TBD: pass pathname computations to Sandbox argument

    class XmlEditorSubclass(superclass):
        def __init__(self, sbx, cleanXML=True):
            self.parentConfigPath = None
            self.cleanXML = cleanXML

            self.scenarioSetup = XMLScenario.get_instance(setupFile) # if parent else None

            if not sbx.is_baseline:
                # TBD: test this in FCIP case where baseline builds on FuelShock
                parent = XMLEditor(sbx, cleanXML=cleanXML)

            super().__init__(sbx, cleanXML=cleanXML)
            self.paramFile = None

            # Read shocks from mcsValues.xml if present
            if sbx.mcs_mode == McsMode.TRIAL:
                # TBD: simplify using ScenarioInfo and DirectoryPath
                # ../../trial-xml/local-xml/base-0/mcsValues.xml
                self.trial_xml_abs = pathjoin(sbx.sandbox_local_xml, 'trial-xml', normpath=True)
                self.trial_xml_rel = pathjoin('../..', 'trial-xml')

                scen_name = self.parent.name if self.parent else self.name
                self.paramFile = pathjoin(self.trial_xml_abs, LOCAL_XML_NAME, sbx.scenario_group,
                                          scen_name, MCSVALUES_FILE, normpath=True)

            self.directoryDict = {'scenarioDir': self.scenario_dir.rel,
                                  'baselineDir': self.baseline_dir.rel if self.baseline_dir else None}

        def setupDynamic(self, args):
            self.groupName = args.group

            super(XmlEditorSubclass, self).setupDynamic(args)
            sbx = self.sbx

            if sbx.mcs_mode == McsMode.TRIAL: # TBD: was just "if self.mcsMode" -- test this
                paramFile = self.paramFile
                if paramFile and os.path.lexists(paramFile):
                    self.mcsValues = McsValues(paramFile)

            if not self.scenarioSetup:
                raise SetupException("XmlEditorSubclass.setupDynamic() was called without having read an XML scenario file")

            self.scenarioSetup.run(self, self.directoryDict, dynamic=True)

            # TBD: Maybe nothing to do here if dyn-xml is merged into local-xml?

            # # Add symlinks to any files that were added in the dynamic setup
            # dynDir  = sbx.sandbox_local_xml # was self.scenario_dyn_dir_abs
            # scenDir = self.scenario_dir_abs
            # xmlFiles = glob.glob(f"{scenDir}/*.xml")
            #
            # # TBD: This appears to be redundant with code in XMLEditor.setupDynamic, but this version
            # #  skips files that already exist, so it's probably just a NO-OP.
            #
            # if xmlFiles:
            #     mode = 'Copy' if getParamAsBoolean('GCAM.CopyAllFiles') else 'Link'
            #     _logger.info("%s additional static XML files in %s to %s", mode, scenDir, dynDir)
            #     for xml in xmlFiles:
            #         base = os.path.basename(xml)
            #         dst = pathjoin(dynDir, base)
            #         src = pathjoin(scenDir, base)
            #         if not os.path.lexists(dst):
            #             symlinkOrCopyFile(src, dst)

            CachedFile.decacheAll()

        def setupStatic(self, args):
            self.groupName = args.group
            scenarioSetup = self.scenarioSetup
            sbx = self.sbx

            # TBD: test this in FCIP case where baseline builds on FuelShock
            # TBD: move baselineSource logic into ScenarioGroup so it can be shared with Sandbox
            if not sbx.parent:
                # Before calling setupStatic, we set the parent if there is
                # a declared baseline source. This assumes it is in this
                # project, in a different group directory.
                group = scenarioSetup.getGroup(self.groupName)
                baselineSource = group.baselineSource
                if baselineSource:
                    try:
                        groupName, baselineName = baselineSource.split('/')
                    except ValueError:
                        raise SetupException(
                            f'baselineSource error: "{baselineSource}"; should be of the form "groupDir/baselineDir"')

                    parentGroup = scenarioSetup.getGroup(groupName)
                    scenario = parentGroup.getFinalScenario(baselineName)
                    if scenario.isBaseline:
                        from copy import copy
                        sbx2 = copy(self.sbx)
                        sbx2.scenario = scenario
                        self.parent = XmlEditorSubclass(sbx2, cleanXML=self.cleanXML)

            directoryDict = self.directoryDict

            # not an "else" since parent may be set in "if" above
            if sbx.parent:
                # patch the template dictionary with the dynamically-determined baseline dir

                directoryDict['baselineDir'] = self.baseline_dir_rel = sbx.parent_scenario_path.rel

            super(XmlEditorSubclass, self).setupStatic(args)

            scenarioSetup.run(self, directoryDict, dynamic=False)
            CachedFile.decacheAll()

    return XmlEditorSubclass

# TBD: used only by ZEVPolicy.py
def scenarioEditor(sbx):
    setupXml = getParam('GCAM.ScenariosFile')
    editorClass = createXmlEditorSubclass(setupXml)
    return editorClass(sbx)

# TBD: currently unused
# def scenarioConfigPath(scenario):
#     # We don't need to specify most of the keyword args when we're just getting the config file
#     editor = scenarioEditor(scenario)
#     path = editor.cfgPath()
#     return path
