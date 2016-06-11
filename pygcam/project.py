#!/usr/bin/env python
"""
.. Support for running a sequence of operations for a GCAM project
   that is described in an XML file.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
import os
import sys
import shlex
import re
import glob
from os.path import join
from lxml import etree as ET
from .config import getParam, getConfigDict
from .utils import (getTempFile, flatten, shellCommand, getBooleanXML, unixPath, simpleFormat,
                    resourceStream)
from .error import PygcamException, CommandlineError, FileFormatError
from .log import getLogger
from .subcommand import SubcommandABC
#from .queryFile import QueryFile

__version__ = '0.2'

_logger = getLogger(__name__)

DefaultProjectFile = './project.xml'

def getBaseline(scenarios):
    '''Check that exactly one active baseline is defined, and if so, return it'''

    baselines = [s for s in scenarios if s.isBaseline and s.isActive]
    if len(baselines) == 1:
        return baselines[0]

    raise FileFormatError('Exactly one active baseline scenario must be defined; found %d' % len(baselines))

def getDefaultGroup(groups):
    '''
    Check that exactly one default scenarioGroup is defined, unless there is only one group,
    in which case it is obviously the default.
    '''
    if len(groups) == 1:
        return groups[0]

    defaults = [group for group in groups if group.isDefault]
    if len(defaults) == 1:
        return defaults[0]

    raise FileFormatError('Exactly one active default scenario group must be defined; found %d' % len(defaults))


class _TmpFile(object):
    """
    Represents the ``<tmpFile>`` element in the projects.xml file.
    """
    Instances = {}  # keyed by name

    def __init__(self, node):
        """
        defaults is an optional _TmpFile instance from which to
        take default file contents, which are appended to or
        replaced by the list defined here.
        """
        # e.g., <tmpFile varName="scenPlots" dir="/tmp/runProject" delete="1" replace="0" eval="1">
        name = node.get('varName')  # required by schema

        self.delete  = getBooleanXML(node.get('delete',  '1'))
        self.replace = getBooleanXML(node.get('replace', '0'))
        self.eval    = getBooleanXML(node.get('eval',    '1'))    # convert {args} before writing file
        self.dir     = node.get('dir')
        self.varName = name
        self.path    = None

        default = self.Instances.get(name)  # save default node of the same name, if any
        self.Instances[name] = self         # replace default with our own definition

        textNodes = node.findall('text')
        defaults = []

        # Substitute any lines based on matching tags, unless we're replacing
        # all the defaults or there are no defaults to replace.
        if not self.replace and default:
            def getTag(node):
                return node.get('tag')

            tags = map(getTag, filter(getTag, textNodes))

            # Save all the defaults that are not overridden by current definitions
            defaults = filter(lambda node: node.get('tag') not in tags, default.textNodes)

        self.textNodes = defaults + textNodes


    @classmethod
    def writeFiles(cls, argDict):
        """
        Write the files and set the associated variables to the generated filenames.
        """
        for tmpFile in cls.Instances.values():
            path = tmpFile.write(argDict)
            argDict[tmpFile.varName] = path

    def write(self, argDict):
        # Note: TempFiles are deleted in the main driver (tool.py)
        path = getTempFile('.txt', tmpDir=self.dir, delete=self.delete)
        path = unixPath(path)

        with open(path, 'w') as f:
            text = '\n'.join(map(lambda x: x.text or '', self.textNodes)) + '\n'
            if text and self.eval:
                text = simpleFormat(text, argDict)
            f.write(text)

        self.path = path
        return path


class ScenarioGroup(object):
    """
    Represents the ``<scenarioGroup>`` element in the projects.xml file.
    """
    def __init__(self, node):
        self.name = node.get('name')
        self.isDefault   = getBooleanXML(node.get('default', default='0'))
        self.useGroupDir = getBooleanXML(node.get('useGroupDir', default='0'))

        scenarioNodes = node.findall('scenario')
        scenarios = map(Scenario, scenarioNodes)

        self.scenarioDict = {scen.name : scen for scen in scenarios}

        baselineNode = getBaseline(scenarios)
        self.baseline = baselineNode.name

class Scenario(object):
    """
    Represents the ``<scenario>`` element in the projects.xml file.
    """
    def __init__(self, node):
        self.name = node.get('name')
        self.isActive   = getBooleanXML(node.get('active',   default='1'))
        self.isBaseline = getBooleanXML(node.get('baseline', default='0'))
        self.subdir = node.get('subdir', default=self.name)


class Step(object):
    """
    Represents the ``<step>`` element in the projects.xml file.
    """
    def __init__(self, node):
        self.seq     = int(node.get('seq', 0))
        self.name    = node.get('name')
        self.runFor  = node.get('runFor', 'all')
        self.group   = node.get('group', None)
        self.command = node.text

        if not self.command:
            raise FileFormatError("<step name='%s'> is missing command text" % self.name)

    def __str__(self):
        return "<Step name='%s' seq='%s' runFor='%s'>%s</Step>" % \
               (self.name, self.seq, self.runFor, self.command)

    def run(self, project, baseline, scenario, argDict, tool, noRun=False):
        runFor = self.runFor
        isBaseline = (baseline == scenario.name)
        isPolicy = not isBaseline

        # See if this step should be run.
        if runFor != 'all' and ((isBaseline and runFor != 'baseline') or (isPolicy and runFor != 'policy')):
            return

        # User can substitute an empty command to delete a default step
        if not self.command:
            return

        try:
            # command = self.command.format(**argDict)    # replace vars in template
            command = simpleFormat(self.command, argDict)    # replace vars in template
        except KeyError as e:
            raise FileFormatError("%s -- No such variable exists in the project XML file" % e)

        _logger.info("[%s, %s, %s] %s", scenario.name, self.seq, self.name, command)

        if not noRun:
            if command[0] == '@':       # run internally in gt
                argList = shlex.split(command[1:])
                argList = flatten(map(lambda s: glob.glob(s) or [s], argList))  # expand shell wildcards
                tool.run(argList=argList)
            else:
                shellCommand(command, shell=True)   # shell=True to expand shell wildcards and so on


class SimpleVariable(object):
    """
    Simple variable of name and value to allow loading config file
    variables alongside variables defined in the project XML file.
    """
    Instances = {}

    def __init__(self, name, value, evaluate=False):
        self.name      = name
        self.value     = value
        self.eval      = evaluate
        self.Instances[name] = self

    def getValue(self):
        return self.value

    def setValue(self, value):
        self.value = value

    def evaluate(self, argDict):
        return self.getValue()

    @classmethod
    def instances(cls):
        return cls.Instances.values()

    @classmethod
    def definedVars(cls):
        return cls.Instances.keys()


    @classmethod
    def setFromDefault(cls, varName, defaultName):
        vars = cls.Instances
        if not varName in vars:
            vars[varName] = vars[defaultName]

    @classmethod
    def getDict(cls):
        argDict = {name: var.value for name, var in cls.Instances.iteritems()}
        return argDict


class Variable(SimpleVariable):
    """
    Represents the ``<var>`` element in the projects.xml file.
    """
    def __init__(self, node):
        name     = node.get('name')
        evaluate = getBooleanXML(node.get('eval', 0))

        super(Variable, self).__init__(name, node.text, evaluate=evaluate)

    @classmethod
    def evaluateVars(cls, argDict):
        '''Evaluate vars and store results in argDict'''
        for name, var in cls.Instances.iteritems():
            argDict[name] = var.evaluate(argDict)

    def evaluate(self, argDict, value=None):
        # optional arg lets us call it recursively
        value = value or self.getValue()

        # result = value.format(**argDict) if value and self.eval else value
        result = simpleFormat(value, argDict) if value and self.eval else value

        # recurse in case there are vars whose values are variable references
        return self.evaluate(argDict, value=result) if re.search('\{[^\}]+\}', result) else result


class Project(object):
    """
    Represents the ``<project>`` element in the projects.xml file.
    """
    def __init__(self, tree, projectName, groupName):
        self.validateXML(tree)
        self.projectName = projectName

        projectNodes = tree.findall('project[@name="%s"]' % projectName)

        if len(projectNodes) == 0:
            raise FileFormatError("Project '%s' is not defined" % projectName)

        if len(projectNodes) > 1:
            raise FileFormatError("Project '%s' is defined %d times" % (projectName, len(projectNodes)))

        projectNode = projectNodes[0]

        self.subdir = projectNode.get('subdir', '')

        defaultsNode = tree.find('defaults')   # returns 1st match
        hasDefaults = defaultsNode is not None

        scenarioGroups = map(ScenarioGroup, projectNode.findall('scenarioGroup'))
        self.scenarioGroupDict = groupDict = {group.name : group for group in scenarioGroups}
        if not groupName:
            defaultGroup = getDefaultGroup(scenarioGroups)
            groupName = defaultGroup.name

        if groupName not in groupDict:
            raise FileFormatError("Group '%s' is not defined for project '%s'" % (groupName, projectName))

        self.scenarioGroupName = groupName
        self.scenarioGroup = scenarioGroup = groupDict[groupName]
        self.baselineName  = scenarioGroup.baseline
        self.scenarioDict  = scenarioGroup.scenarioDict

        dfltSteps = map(Step, defaultsNode.findall('./steps/step')) if hasDefaults else []
        projSteps = map(Step, projectNode.findall('./steps/step'))
        allSteps  = dfltSteps + projSteps

        # project steps with same name and seq overwrite defaults
        self.stepsDict = stepsDict = {}
        for step in allSteps:
            key = "%s-%d" % (step.name, step.seq)
            stepsDict[key] = step

        self.vars = {}

        if hasDefaults:
            map(Variable, defaultsNode.findall('./vars/var'))

        map(Variable,  projectNode.findall('./vars/var'))

        dfltTmpFileNodes = defaultsNode.findall('tmpFile') if hasDefaults else []
        projTmpFileNodes = projectNode.findall('tmpFile')
        self.tmpFiles = map(_TmpFile, dfltTmpFileNodes + projTmpFileNodes)

    @staticmethod
    def validateXML(doc, raiseError=True):
        '''
        Validate a parsed project.xml file
        '''
        schemaStream = resourceStream('etc/project-schema.xsd')

        schemaDoc = ET.parse(schemaStream)
        schema = ET.XMLSchema(schemaDoc)

        if raiseError:
            schema.assertValid(doc)
        else:
            return schema.validate(doc)

    def maybeListProjectArgs(self, args, knownGroups, knownScenarios, knownSteps):
        '''
        If user asked to list scenarios, steps, or variables, do so and quit.
        '''
        self.quit = False

        def showList(strings, header):
            self.quit = True
            if header:
                print header
            for s in strings:
                print '  ', s

        if args.listGroups:
            showList(knownGroups, 'Scenario groups:')

        if args.listScenarios:
            showList(knownScenarios, 'Scenarios:')

        if args.listSteps:
            showList(knownSteps, 'Steps:')

        if args.vars:
            varList = ["%15s = %s" % (name, value) for name, value in sorted(self.argDict.iteritems())]
            showList(varList, 'Vars:')

        if self.quit:
            sys.exit(0)

    def getKnownSteps(self):
        '''
        Return a list of known steps in seq order, without duplicates.
        '''
        tmpDict = {}    # used to eliminate duplicates

        def uniqStep(step):
            key = step.name
            if tmpDict.get(key):
                return False # already in dict

            tmpDict[key] = 1
            return key       # first time for this name

        self.sortedSteps = sortedSteps = sorted(self.stepsDict.values(), key=lambda node: node.seq)
        knownSteps = [step.name for step in sortedSteps if uniqStep(step)]
        return knownSteps

    def getKnownScenarios(self):
        '''
        Return a list of known scenarios for the current project and scenarioGroup, alpha sorted
        '''
        # sorting by not(node.isBaseline) results in baseline preceding scenarios
        sortedScenarios = sorted(self.scenarioDict.values(), key=lambda node: not node.isBaseline)
        knownScenarios  = map(lambda node: node.name, sortedScenarios)
        return knownScenarios

    def getKnownGroups(self):
        '''
        Return a list of known scenarioGroups for the current project.
        '''
        sortedGroups = sorted(self.scenarioGroupDict.values(), key=lambda node: node.name)
        knownGroups = map(lambda node: node.name, sortedGroups)
        return knownGroups

    def validateProjectArgs(self, userArgs, knownArgs, argName):
        """
        If the user requested steps or scenarios that are not defined, raise an error.

        :param userArgs: a list of the elements (projects, groups, scenarios, steps)
          passed by the user on the command-line.
        :param knownArgs: a list of known elements of the given type
        :param argName: the tag of the XML element
        :return: nothing
        :raises: CommandlineError if the elements requested by the user are not defined in
          the current (project, scenario) context
        """
        unknownArgs = set(userArgs) - set(knownArgs)
        if unknownArgs:
            s = ' '.join(unknownArgs)
            raise CommandlineError("Requested %s do not exist in project '%s', group '%s': %s" % \
                                  (argName, self.projectName, self.scenarioGroupName, s))

    def sortScenarios(self, scenarioSet):
        """
        If a baseline is in the scenario set, move it to the front and return the new list
        """
        scenarios = list(scenarioSet)

        for scenarioName in scenarios:
            scenario = self.scenarioDict[scenarioName]
            if scenario.isBaseline:
                scenarios.remove(scenarioName)
                scenarios.insert(0, scenarioName)
                break

        return scenarios


    def run(self, scenarios, skipScenarios, steps, skipSteps, args, tool):
        """
        Command templates can include keywords curly braces that are substituted
        to create the command to execute in the shell. Variables are defined in
        the <vars> section of the project XML file.
        """
        # Get the text values for all config variables, allowing variables
        # defined in the project to override them.
        cfgDict = getConfigDict(section=self.projectName)
        for name, value in cfgDict.iteritems():
            SimpleVariable(name, value)

        self.argDict = argDict = Variable.getDict()

        scenarioGroupName  = self.scenarioGroupName
        groupDir = scenarioGroupName if self.scenarioGroup.useGroupDir else ''

        # Add standard variables from project XML file itself
        argDict['project']       = self.projectName
        argDict['projectSubdir'] = subdir = self.subdir
        argDict['baseline']      = argDict['reference'] = baseline = self.baselineName     # baseline is synonym for reference
        argDict['scenarioGroup'] = self.scenarioGroupName

        argDict['projectSrcDir'] = unixPath(join(argDict['GCAM.XmlSrc'], groupDir, subdir), rmFinalSlash=True)
        argDict['projectXmlDir'] = unixPath(join(argDict['GCAM.LocalXml'], groupDir, subdir), rmFinalSlash=True)
        # deprecated argDict['projectWsDir']  = unixPath(join(argDict['GCAM.SandboxDir'], groupDir, subdir), rmFinalSlash=True)

        argDict['SEP']  = os.path.sep       # '/' on Unix; '\\' on Windows
        argDict['PSEP'] = os.path.pathsep   # ':' on Unix; ';' on Windows

        knownGroups    = self.getKnownGroups()
        knownScenarios = self.getKnownScenarios()
        knownSteps     = self.getKnownSteps()

        self.maybeListProjectArgs(args, knownGroups, knownScenarios, knownSteps)

        # Set steps / scenarios to all known values if user doesn't specify any
        steps = set(steps or knownSteps) - set(skipSteps or [])
        scenarios = set(scenarios or knownScenarios) - set(skipScenarios or [])

        # Check that the requested scenarios and steps are defined
        self.validateProjectArgs(scenarios, knownScenarios, 'scenarios')
        self.validateProjectArgs(steps,     knownSteps,     'steps')

        quitProgram = args.quit

        scenarios = self.sortScenarios(scenarios)

        for scenarioName in scenarios:
            scenario = self.scenarioDict[scenarioName]

            if not scenario.isActive:
                _logger.debug("Skipping inactive scenario: %s", scenarioName)
                continue

            # These get reset as each scenario is processed
            argDict['scenario']       = scenarioName
            argDict['scenarioSubdir'] = scenario.subdir or scenarioName
            argDict['sandboxRoot']    = argDict['GCAM.SandboxRoot']
            argDict['sandboxDir']     = sandboxDir  = argDict['GCAM.SandboxDir']
            argDict['sandboxGroupDir']= groupDir = unixPath(join(sandboxDir, groupDir))
            argDict['scenarioDir']    = scenarioDir = unixPath(join(groupDir, scenarioName))
            argDict['diffsDir']       = unixPath(join(scenarioDir, 'diffs'))
            argDict['batchDir']       = unixPath(join(scenarioDir, 'batch-' + scenarioName))

            # Evaluate dynamic variables and re-generate temporary files, saving paths in
            # variables indicated in <tmpFile>. This is in the scenario loop so run-time
            # variables are handled correctly, though it does result in the files being
            # written multiple times (though with different values.)
            Variable.evaluateVars(argDict)
            _TmpFile.writeFiles(argDict)

            try:
                # Loop over all steps and run those that user has requested
                for step in self.sortedSteps:
                    if step.name in steps and (not step.group or step.group == scenarioGroupName):
                        argDict['step'] = step.name
                        step.run(self, baseline, scenario, argDict, tool, noRun=args.noRun)
            except PygcamException as e:
                if quitProgram:
                    raise
                _logger.error(e)


    def dump(self, steps, scenarios):
        print "Scenario group: %s" % self.scenarioGroupName
        print "Requested steps:", steps
        print "Requested scenarios:", scenarios
        print "Defined steps:", self.getKnownSteps()
        print "Defined scenarios:", self.getKnownScenarios()
        print 'Defined vars:'
        for name, var in Variable.Instances.iteritems():
            print "  %15s : %s" % (name, var.getValue())
        print '\nTmpFiles:'
        for t in self.tmpFiles:
            print "  ", t.varName


def driver(args, tool, cmdClass=Project):
    if not args.project:
        args.project = args.configSection or getParam('GCAM.DefaultProject')

    if not args.project:
        raise CommandlineError("run: must specify project name")

    steps = flatten(map(lambda s: s.split(','), args.steps)) if args.steps else None
    skipSteps = flatten(map(lambda s: s.split(','), args.skipSteps)) if args.skipSteps else None

    scenarios = args.scenarios and flatten(map(lambda s: s.split(','), args.scenarios))
    skipScenarios = flatten(map(lambda s: s.split(','), args.skipScenarios)) if args.skipScenarios else None

    projectFile = args.projectFile or getParam('GCAM.ProjectXmlFile') or DefaultProjectFile

    parser  = ET.XMLParser(remove_blank_text=True)
    tree    = ET.parse(projectFile, parser)
    project = cmdClass(tree, args.project, args.group)

    project.run(scenarios, skipScenarios, steps, skipSteps, args, tool)


class ProjectCommand(SubcommandABC):
    def __init__(self, subparsers, name='run', help='Run the steps for a project defined in a project.xml file'):
        kwargs = {'help' : help}
        super(ProjectCommand, self).__init__(name, subparsers, kwargs)

    def addArgs(self, parser):

        parser.add_argument('-f', '--projectFile',
                            help='''The XML file describing the project. If set, command-line
                            argument takes precedence. Otherwise, value is taken from config file
                            variable GCAM.ProjectXmlFile, if defined, otherwise the default
                            is './project.xml'.''')

        parser.add_argument('-g', '--group',
                            help='''The name of the scenario group to process. If not specified,
                            the group with attribute default="1" is processed.''')

        parser.add_argument('-G', '--listGroups', action='store_true',
                            help='''List the scenario groups defined in the project file and exit.''')

        parser.add_argument('-k', '--skipStep', dest='skipSteps', action='append',
                            help='''Steps to skip. These must be names of steps defined in the
                            project.xml file. Multiple steps can be given in a single (comma-delimited)
                            argument, or the -k flag can be repeated to indicate additional steps.
                            By default, all steps are run.''')

        parser.add_argument('-K', '--skipScenario', dest='skipScenarios', action='append',
                            help='''Scenarios to skip. Multiple scenarios can be given in a single
                            (comma-delimited) argument, or the -K flag can be repeated to indicate
                            additional scenarios. By default, all scenarios are run.''')

        parser.add_argument('-l', '--listSteps', action='store_true', default=False,
                            help='''List the steps defined for the given project and exit.
                            Dynamic variables (created at run-time) are not displayed.''')

        parser.add_argument('-L', '--listScenarios', action='store_true', default=False,
                            help='''List the scenarios defined for the given project and exit.
                            Dynamic variables (created at run-time) are not displayed.''')

        parser.add_argument('-n', '--noRun', action='store_true', default=False,
                            help='''Display the commands that would be run, but don't run them.''')

        parser.add_argument('-p', '--project', help='''The name of the project to run.''')

        parser.add_argument('-q', '--quit', action='store_true',
                            help='''Quit if an error occurs when processing a scenario. By default, the
                            next scenario (if any) is run when an error occurs in a scenario.''')

        parser.add_argument('-s', '--step', dest='steps', action='append',
                            help='''The steps to run. These must be names of steps defined in the
                            project.xml file. Multiple steps can be given in a single (comma-delimited)
                            argument, or the -s flag can be repeated to indicate additional steps.
                            By default, all steps are run.''')

        parser.add_argument('-S', '--scenario', dest='scenarios', action='append',
                            help='''Which of the scenarios defined for the given project should
                            be run. Multiple scenarios can be given in a single (comma-delimited)
                            argument, or the -S flag can be repeated to indicate additional scenarios.
                            By default, all active scenarios are run.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

        parser.add_argument('--vars', action='store_true', help='''List variables and their values''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
