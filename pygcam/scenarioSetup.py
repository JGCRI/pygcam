'''
.. Created on: 8/21/16

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import sys

from .config import getParam
from .error import PygcamException, SetupException
from .log import getLogger
from .utils import XMLFile, getBooleanXML, resourceStream
from .xmlEditor import XMLEditor, getCallableMethod

_logger = getLogger(__name__)

# Return a class (or any object) defined in this module
def classForString(className):
    return getattr(sys.modules[__name__], className)

def _classForNode(node):
    className = node.tag.capitalize()
    cls = classForString(className)
    return cls(node)

#
# Classes to parse and run "simple" scenario setup files.
# (See pygcam/etc/scenarioSetup-schema.xsd).
#
class ScenarioSetup(object):

    def __init__(self, node):
        self.name = node.get('name', '')    # unused currently
        self.defaultGroup = node.get('defaultGroup')

        # These serve as a no-op on the build-out pass. The directory vars are
        # converted when the scenario is run and the directories are known.
        self.templateDict = {'scenarioDir' : '{scenarioDir}',
                             'baselineDir' : '{baselineDir}'}

        iterators = map(Iterator, node.findall('iterator'))
        self.iteratorDict = {obj.name : obj for obj in iterators}
        self.iteratorValues = {}

        templateGroups = map(ScenarioGroup, node.findall('scenarioGroup'))
        self.groups = self.expandGroups(templateGroups)

        # Create a dict of expanded groups for lookup
        self.groupDict = {obj.name : obj for obj in self.groups}

    def getIterator(self, name):
        try:
            return self.iteratorDict[name]
        except KeyError:
            raise SetupException("Iterator '%s' is not defined")

    documentCache = {}

    @classmethod
    def parse(cls, filename):
        """
        Parse an XML file holding a list of query descriptions.
        :param filename: (str) the name of the XML file to read
        :return: a QueryFile instance.
        """
        if filename in cls.documentCache:
            _logger.debug('Found scenario file "%s" in cache', filename)
            return cls.documentCache[filename]

        schemaStream = resourceStream('etc/scenarioSetup-schema.xsd')
        xmlFile = XMLFile(filename, schemaFile=schemaStream, removeComments=True)
        obj = cls(xmlFile.tree.getroot())

        cls.documentCache[filename] = obj      # cache it
        return obj

    def expandGroups(self, templateGroups):
        '''
        Expand the `templateGroups`, which may contain names based
        on iterators, into final scenarioGroups without iterators.
        Recursively expands scenarios within groups.
        '''
        finalGroups = []
        templateDict = self.templateDict

        def expand(group):
            group.name = group.name.format(**templateDict)
            group.setScenarios(self.expandScenarios(group.scenarios()))
            finalGroups.append(group)

        for templateGroup in templateGroups:
            iterName = templateGroup.iteratorName

            if not iterName:
                expand(templateGroup)
                continue

            node = templateGroup.node
            iterator = self.getIterator(iterName)
            strFormat = iterator.format

            for value in iterator:
                try:
                    name = strFormat % value # convert to string
                except Exception:
                    raise SetupException("Bad format string: '%s'" % strFormat)

                templateDict[iterName] = name
                expand(ScenarioGroup(node))

        return finalGroups

    def expandScenarios(self, templateScenarios):
        finalScenarios = []
        templateDict = self.templateDict

        # Replace the text context in all action elements with expanded version
        def expand(scenario):
            scenario.name = scenario.name.format(**templateDict)
            finalScenarios.append(scenario)
            # This converts only the iterators. The directories {scenarioDir}
            # and {baselineDir} are converted when the scenario is run.
            for action in scenario.actions:
                action.content = action.formatContent(templateDict)

        for templateScenario in templateScenarios:
            iterName = templateScenario.iteratorName

            if not iterName:
                expand(templateScenario)
                continue

            node = templateScenario.node
            iterator = self.getIterator(iterName)
            strFormat = iterator.format

            for value in iterator:
                templateDict[iterName] = strFormat % value    # convert to string
                expand(Scenario(node))

        return finalScenarios

    def run(self, editor, directoryDict):
        """
        Run the setup for the given XmlEditor subclass.

        :param editor: (XmlEditor) an instance of a subclass of XmlEditor
        :return: none
        """
        self.editor = editor
        group = self.groupDict[editor.groupDir or self.defaultGroup]
        scenario = group.getScenario(editor.scenario or editor.baseline)
        scenario.run(editor, directoryDict)

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

# TBD: simplify int and float variants to pre-generate self.values list
class Iterator(object):
    def __init__(self, node):
        self.name = node.get('name')
        self.min  = self.max = self.step = self.values = None

        typeName  = node.get('type')
        isNumeric = typeName in ('int', 'float')
        self.type = iterType = eval(typeName)   # N.B. requires options to all be Python types

        if isNumeric:
            self.min  = iterType(node.get('min'))
            self.max  = iterType(node.get('max'))
            self.step = iterType(node.get('step', 1))
            self.format = node.get('format', '%d' if self.type == int else '%.1f')

        else: # 'list'
            valuesStr = node.get('values')
            if not valuesStr:
                raise SetupException('list iterator must provide a values attribute')

            self.values = map(str.strip, valuesStr.split(','))
            self.format = '%s'


    def __iter__(self):
        if self.type == list:
            return self.values.__iter__()

        # N.B. The irange and frange iterators *include* the maximum value.
        rangeFunc = irange if self.type == int else frange
        return rangeFunc(self.min, self.max, self.step)

    def __str__(self):
        desc = "<iterator name='%s' type='%s' " % (self.name, self.type)

        if self.type == list:
            desc += "values='%s'/>" % self.values.join(',')
        else:
            desc += "min='%s' max='%s' step='%s'/>" % (self.min, self.max, self.step)

        return desc

class ScenarioGroup(object):
    def __init__(self, node):
        self.node = node
        self.name = node.get('name')
        self.useGroupDir = getBooleanXML(node.get('useGroupDir', 0))
        self.isDefault = getBooleanXML(node.get('default', 0))
        self.iteratorName = node.get('iterator')
        self.baselineSource = node.get('baselineSource')
        self.scenarioDict = None

        nodes = node.findall('scenario')
        self.setScenarios(map(Scenario, nodes))

    def setScenarios(self, scenarios):
        self.scenarioDict = {obj.name : obj for obj in scenarios}

    def scenarios(self):
        return self.scenarioDict.values()

    def getScenario(self, name):
        return self.scenarioDict.get(name)

class Scenario(object):
    def __init__(self, node):
        self.node = node
        self.name = node.get('name')
        self.isBaseline = getBooleanXML(node.get('baseline', 0))
        self.iteratorName = node.get('iterator')

        # N.B. Elements behave like a list of its children
        self.actions = map(_classForNode, node)

    def __str__(self):
        return "<scenario name='%s'>" % self.name

    def run(self, editor, directoryDict):
        for action in self.actions:
            action.formattedContent = action.formatContent(directoryDict)
            action.run(editor)

class ConfigAction(object):
    def __init__(self, node):
        self.tag  = node.tag
        self.name = node.get('name')
        self.dir  = node.get('dir', '')     # TBD: currently unused
        self.content = node.text
        self.formattedContent = None

    def __str__(self):
        return "<%s name='%s'>%s</config>" % \
               (self.tag, self.name, self.content)

    def formatContent(self, directoryDict):
        return self.content.format(**directoryDict) if self.content else None

class Insert(ConfigAction):
    def __init__(self, node):
        super(Insert, self).__init__(node)
        self.after = node.get('after')

    def run(self, editor):
        editor.insertScenarioComponent(self.name, self.formattedContent, self.after)

class Add(ConfigAction):
    def run(self, editor):
        editor.addScenarioComponent(self.name, self.formattedContent)

class Replace(ConfigAction):
    def run(self, editor):
        editor.updateScenarioComponent(self.name, self.formattedContent)

class Delete(ConfigAction):
    def run(self, editor):
        editor.deleteScenarioComponent(self.name)

class Function(ConfigAction):
    def run(self, editor):
        name = self.name
        method = getCallableMethod(name)
        if not method:
            raise SetupException('<function name="%s">: function name is unknown', name)

        codeStr = "editor.%s(%s)" % (name, self.formattedContent)
        try:
            result = eval(codeStr)
        except SyntaxError as e:
            raise SetupException("Failed to evaluate expression %s: %s" % (codeStr, e))


class Generator(ConfigAction):
    # TBD
    def run(self, editor):
        #print("Run generator %s: %s" % (self.name, self.content))
        raise SetupException('Generator is not yet implemented')


def createXmlEditorSubclass(setupFile):
    """
    Generate a subclass of the given `superclass` that runs the
    XML setup file given by variable GCAM.ScenarioSetupFile.
    If defined, GCAM.ScenarioSetupClass must be of the form:
    "/path/to/module/dir:module.ClassName]". If the variable
    GCAM.ScenarioSetupClass is empty, the class XMLEditor is
    subclassed directly.

    :param setupFile: (str) the pathname of an XML setup file
    :return: (class) A subclass of the given `superclass`
    """
    setupClass = getParam('GCAM.ScenarioSetupClass')
    if setupClass:
        try:
            modPath, dotSpec = setupClass.split(':', 1)
        except Exception:
            raise SetupException('GCAM.ScenarioSetupClass should be of the form "/path/to/moduleDirectory:module.ClassName", got "%s"' % setupClass)

        try:
            from .utils import importFromDotSpec
            sys.path.insert(0, modPath)
            _module, superclass = importFromDotSpec(dotSpec)

        except PygcamException as e:
            raise SetupException("Can't load setup class '%s' from '%s': %s" % (dotSpec, modPath, e))
    else:
        superclass = XMLEditor

    class XmlEditorSubclass(superclass):
        def __init__(self, baseline, scenario, xmlOutputRoot, xmlSrcDir, refWorkspace, groupName, subdir, parent=None):
            self.parentConfigPath = None

            # if not a baseline, create a baseline instance as our parent
            if scenario:
                parent = XmlEditorSubclass(baseline, None, xmlOutputRoot, xmlSrcDir, refWorkspace, groupName, subdir)

            super(XmlEditorSubclass, self).__init__(baseline, scenario, xmlOutputRoot, xmlSrcDir,
                                                    refWorkspace, groupName, subdir, parent=parent)

        def setupStatic(self, args):
            directoryDict = {'scenarioDir': self.scenario_dir_rel,
                             'baselineDir': self.baseline_dir_rel}
            scenarioSetup = ScenarioSetup.parse(setupFile)

            if not self.parent:
                # Before calling setupStatic, we set the parent if there is
                # a declared baseline source. This assumes it is in this
                # project, in a different group directory.
                group = scenarioSetup.groupDict[self.groupDir or scenarioSetup.defaultGroup]
                baselineSource = group.baselineSource
                if baselineSource:
                    try:
                        groupName, baselineName = baselineSource.split('/')
                    except ValueError:
                        raise SetupException(
                            'baselineSource error: "%s"; should be of the form "groupDir/baselineDir"' % baselineSource)

                    parentGroup = scenarioSetup.groupDict[groupName]
                    scenario = parentGroup.getScenario(baselineName)
                    if scenario.isBaseline:
                        self.parent = XmlEditorSubclass(baselineName, None, self.xmlOutputRoot, self.xmlSourceDir,
                                                        self.refWorkspace, groupName, self.subdir)

            # not an "else" since parent may be set in "if" above
            if self.parent:
                # patch the template dictionary with the dynamically-determined baseline dir
                directoryDict['baselineDir'] = self.baseline_dir_rel = self.parent.scenario_dir_rel

            super(XmlEditorSubclass, self).setupStatic(args)
            scenarioSetup.run(self, directoryDict)

    return XmlEditorSubclass
