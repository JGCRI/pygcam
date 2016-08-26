'''
.. Created on: 8/21/16

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import sys

from .config import getParam
from .error import SetupException
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

    def __init__(self, node, templateDict):
        self.name = node.get('name', '')    # unused currently
        self.defaultGroup = node.get('defaultGroup')

        iterators = map(Iterator, node.findall('iterator'))
        self.iteratorDict = {obj.name : obj for obj in iterators}

        templateGroups = map(ScenarioGroup, node.findall('scenarioGroup'))
        self.groups = self.expandGroups(templateGroups, templateDict)

        # Create a dict of expanded groups for lookup
        self.groupDict = {obj.name : obj for obj in self.groups}

    def getIterator(self, name):
        try:
            return self.iteratorDict[name]
        except KeyError:
            raise SetupException("Iterator '%s' is not defined")

    documentCache = {}

    @classmethod
    def parse(cls, filename, templateDict):
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
        obj = cls(xmlFile.tree.getroot(), templateDict)

        cls.documentCache[filename] = obj      # cache it
        return obj

    def expandGroups(self, templateGroups, templateDict):
        '''
        Expand the `templateGroups`, which may contain names based
        on iterators, into final scenarioGroups without iterators.
        Recursively expands scenarios within groups.
        '''
        finalGroups = []

        for templateGroup in templateGroups:
            iterName = templateGroup.iteratorName

            if not iterName:
                templateGroup.setScenarios(self.expandScenarios(templateGroup.scenarios(), templateDict))
                finalGroups.append(templateGroup)
                continue

            node = templateGroup.node
            iterator = self.getIterator(iterName)
            strFormat = iterator.format

            for value in iterator:
                templateDict[iterName] = strFormat % value    # convert to string
                group = ScenarioGroup(node)
                group.name = group.name.format(**templateDict)
                group.setScenarios(self.expandScenarios(group.scenarios(), templateDict))
                finalGroups.append(group)

        return finalGroups

    def expandScenarios(self, templateScenarios, templateDict):
        finalScenarios = []

        for templateScenario in templateScenarios:
            iterName = templateScenario.iteratorName

            if not iterName:
                templateScenario.name = templateScenario.name.format(**templateDict)
                finalScenarios.append(templateScenario)
                continue

            node = templateScenario.node
            iterator = self.getIterator(iterName)
            strFormat = iterator.format

            # TBD: do substitution even if no inner iterator
            for value in iterator:
                templateDict[iterName] = strFormat % value    # convert to string
                scenario = Scenario(node)
                scenario.name = scenario.name.format(**templateDict)
                finalScenarios.append(scenario)

                # Replace the text context in all action elements with expanded version
                for action in scenario.actions:
                    content = action.content
                    action.content = content.format(**templateDict) if content else None

        return finalScenarios

    def run(self, editor):
        """
        Run the setup for the given XmlEditor subclass.

        :param editor: (XmlEditor) an instance of a subclass of XmlEditor
        :return: none
        """
        self.editor = editor
        group = self.groupDict[editor.groupDir or self.defaultGroup]
        scenario = group.getScenario(editor.scenario or editor.baseline)
        scenario.run(editor)

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

    def run(self, editor):
        for obj in self.actions:
            obj.run(editor)

class ConfigAction(object):
    def __init__(self, node):
        self.tag  = node.tag
        self.name = node.get('name')
        self.dir  = node.get('dir', '')     # TBD: currently unused
        self.content = node.text

    def __str__(self):
        return "<%s name='%s' dir='%s'>%s</config>" % \
               (self.tag, self.name, self.dir, self.content)

class Insert(ConfigAction):
    def __init__(self, node):
        super(Insert, self).__init__(node)
        self.after = node.get('after')

    def run(self, editor):
        editor.insertScenarioComponent(self.name, self.content, self.after)

class Add(ConfigAction):
    def __init__(self, node):
        super(Add, self).__init__(node)

    def run(self, editor):
        editor.addScenarioComponent(self.name, self.content)

class Replace(ConfigAction):
    def __init__(self, node):
        super(Replace, self).__init__(node)

    def run(self, editor):
        editor.updateScenarioComponent(self.name, self.content)

class Delete(ConfigAction):
    def __init__(self, node):
        super(Delete, self).__init__(node)

    def run(self, editor):
        editor.deleteScenarioComponent(self.name)

class Function(ConfigAction):
    def __init__(self, node):
        super(Function, self).__init__(node)

    def run(self, editor):
        name = self.name
        method = getCallableMethod(name)
        if not method:
            raise SetupException('<function name="%s">: function name is unknown', name)

        codeStr = "editor.%s(%s)" % (name, self.content)
        try:
            result = eval(codeStr)
        except SyntaxError as e:
            raise SetupException("Failed to evaluate expression %s: %s" % (codeStr, e))


class Generator(ConfigAction):
    def __init__(self, node):
        super(Generator, self).__init__(node)
        self.content = node.text

    def __str__(self):
        return "<generator name='%s'>%s</generator>" % (self.name, self.content)

    # TBD
    def run(self, editor):
        #print("Run generator %s: %s" % (self.name, self.content))
        raise SetupException('Generator is not yet implemented')

#
# This observes the same protocol as custom XMLEditor subclasses
#
class SimpleScenario(XMLEditor):
    def __init__(self, baseline, scenario, xmlOutputRoot, xmlSrcDir, refWorkspace, groupName, subdir, parent=None):
        self.parentConfigPath = None

        # if not a baseline, create a baseline instance as our parent
        if scenario:
            parent = SimpleScenario(baseline, None, xmlOutputRoot, xmlSrcDir, refWorkspace, groupName, subdir)

        super(SimpleScenario, self).__init__(baseline, scenario, xmlOutputRoot, xmlSrcDir,
                                             refWorkspace, groupName, subdir, parent=parent)

    def setupStatic(self, args):
        setupFile = getParam('GCAM.ScenarioSetupFile')
        templateDict = {'scenarioDir': self.scenario_dir_rel,
                        'baselineDir': self.baseline_dir_rel}
        scenarioSetup = ScenarioSetup.parse(setupFile, templateDict)

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
                    raise SetupException('baselineSource error: "%s"; should be of the form "groupDir/baselineDir"' % baselineSource)

                parentGroup = scenarioSetup.groupDict[groupName]
                scenario = parentGroup.getScenario(baselineName)
                if scenario.isBaseline:
                    self.parent = SimpleScenario(baselineName, None, self.xmlOutputRoot, self.xmlSourceDir,
                                                 self.refWorkspace, groupName, self.subdir)

        super(SimpleScenario, self).setupStatic(args)
        scenarioSetup.run(self)


