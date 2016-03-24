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
from os.path import join
from lxml import etree as ET
from .config import getParam
from .common import getTempFile, flatten, shellCommand, getBooleanXML, unixPath
from .error import PygcamException
from .log import getLogger
from .subcommand import SubcommandABC

_logger = getLogger(__name__)

DefaultProjectFile = './project.xml'

def getBaseline(scenarios):
    '''Check that exactly one active baseline is defined, and if so, return it'''

    baselines = [s for s in scenarios if s.isBaseline and s.isActive]
    if len(baselines) == 1:
        return baselines[0]

    raise PygcamException('Exactly one active baseline scenario must be defined; found %d' % len(baselines))

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

    raise PygcamException('Exactly one active default scenario group must be defined; found %d' % len(defaults))


class TmpFile(object):
    """
    Represents the ``<tmpFile>`` element in the projects.xml file.
    """
    FilesToDelete = []
    Instances = {}  # keyed by name

    def __init__(self, node):
        """
        defaults is an optional TmpFile instance from which to
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
    def deleteFiles(cls):
        for path in cls.FilesToDelete:
            try:
                os.unlink(path)
            except:
                _logger.warn("Failed to delete file '%s", path)

    @classmethod
    def writeFiles(cls, argDict):
        for tmpFile in cls.Instances.values():
            path = tmpFile.write(argDict)
            argDict[tmpFile.varName] = path

    def write(self, argDict):
        path = getTempFile('.txt', tmpDir=self.dir)
        path = unixPath(path)
        if self.delete:
            self.FilesToDelete.append(path)

        with open(path, 'w') as f:
            text = '\n'.join(map(lambda x: x.text or '', self.textNodes)) + '\n'
            if text and self.eval:
                text = text.format(**argDict)
            f.write(text)

        self.path = path
        return path


class ScenarioGroup(object):
    """
    Represents the ``<scenarioGroup>`` element in the projects.xml file.
    """
    def __init__(self, node):
        self.name = node.get('name')
        self.isDefault = getBooleanXML(node.get('default', default='0'))

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
        self.command = node.text

        if not self.command:
            raise PygcamException("<step name='%s'> is missing command text" % self.name)

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
            command = self.command.format(**argDict)    # replace vars in template
        except KeyError as e:
            raise PygcamException("%s -- No such variable exists in the project XML file" % e)

        _logger.info("[%s, %s, %s] %s", scenario.name, self.seq, self.name, command)

        if not noRun:
            if command[0] == '@':       # run internally in gcamtool
                argList = shlex.split(command[1:])
                tool.run(argList=argList)
            else:
                shellCommand(command)

class Variable(object):
    """
    Represents the ``<var>`` element in the projects.xml file.
    """
    Instances = {}

    def __init__(self, node):
        self.name = node.get('name')
        self.configVar = configVar = node.get('configVar')
        self.eval = getBooleanXML(node.get('eval', 0))

        try:
            self.value = getParam(configVar) if configVar else node.text
        except Exception as e:
            raise PygcamException("Failed to get value for configVar '%s': %s" % (configVar, e))

        self.Instances[self.name] = self

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

    @classmethod
    def evaluateVars(cls, argDict):
        '''Evaluate vars and store results in argDict'''
        for name, var in cls.Instances.iteritems():
            # TBD: might only do this if var.evaluate is set
            argDict[name] = var.evaluate(argDict)

    def evaluate(self, argDict):
        value = self.getValue()
        result = value.format(**argDict) if value and self.eval else value
        return result

    def getValue(self):
        return self.value

    def setValue(self, value):
        self.value = value


class Project(object):
    """
    Represents the ``<project>`` element in the projects.xml file.
    """
    def __init__(self, tree, projectName, groupName):
        self.validateXML(tree)
        self.projectName = projectName

        projectNodes = tree.findall('project[@name="%s"]' % projectName)

        if len(projectNodes) == 0:
            raise PygcamException("Project '%s' is not defined" % projectName)

        if len(projectNodes) > 1:
            raise PygcamException("Project '%s' is defined %d times" % (projectName, len(projectNodes)))

        projectNode = projectNodes[0]

        self.subdir = projectNode.get('subdir', projectName)        # subdir defaults to project name

        defaultsNode = tree.find('defaults')   # returns 1st match

        scenarioGroups = map(ScenarioGroup, projectNode.findall('scenarioGroup'))
        self.scenarioGroupDict = groupDict = {group.name : group for group in scenarioGroups}
        if not groupName:
            defaultGroup = getDefaultGroup(scenarioGroups)
            groupName = defaultGroup.name

        if groupName not in groupDict:
            raise PygcamException("Group '%s' is not defined for project '%s'" % (groupName, projectName))

        self.scenarioGroupName = groupName
        self.scenarioGroup = scenarioGroup = groupDict[groupName]
        self.baselineName  = scenarioGroup.baseline
        self.scenarioDict  = scenarioGroup.scenarioDict

        dfltSteps = map(Step, defaultsNode.findall('./steps/step'))
        projSteps = map(Step, projectNode.findall('./steps/step'))
        allSteps  = dfltSteps + projSteps

        # project steps with same name and seq overwrite defaults
        self.stepsDict = stepsDict = {}
        for step in allSteps:
            key = "%s-%d" % (step.name, step.seq)
            stepsDict[key] = step

        self.vars = {}

        map(Variable, defaultsNode.findall('./vars/var'))
        map(Variable,  projectNode.findall('./vars/var'))

        # Deprecated?
        Variable.setFromDefault('shockYear', 'startYear')    # set defaults from other vars
        Variable.setFromDefault('analysisEndYear', 'endYear')

        self.checkRequiredVars()

        dfltTmpFileNodes = defaultsNode.findall('tmpFile')
        projTmpFileNodes = projectNode.findall('tmpFile')
        self.tmpFiles = map(TmpFile, dfltTmpFileNodes + projTmpFileNodes)

    @staticmethod
    def validateXML(doc, raiseError=True):
        '''
        Validate a parsed project.xml file
        '''
        schemaFile = os.path.join(os.path.dirname(__file__), 'etc', 'project-schema.xsd')
        schemaDoc = ET.parse(schemaFile)
        schema = ET.XMLSchema(schemaDoc)

        if raiseError:
            schema.assertValid(doc)
        else:
            return schema.validate(doc)

    def checkRequiredVars(self):
        '''Ensure that the required vars are set to non-empty strings'''
        required = {'xmlsrc', 'workspaceRoot', 'localXml'}
        given = set(Variable.definedVars())
        missing = required - given
        if missing:
            raise PygcamException("Missing required variables: %s" % missing)

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
        :raises: PygcamException if the elements requested by the user are not defined in
          the current (project, scenario) context
        """
        unknownArgs = set(userArgs) - set(knownArgs)
        if unknownArgs:
            s = ' '.join(unknownArgs)
            raise PygcamException("Requested %s do not exist in project '%s', group '%s': %s" % \
                                  (argName, self.projectName, self.scenarioGroupName, s))

    def run(self, scenarios, steps, args, tool):
        """
        Command templates can include keywords curly braces that are substituted
        to create the command to execute in the shell. Variables are defined in
        the <vars> section of the project XML file.
        """
        # Get the text values for all variables
        self.argDict = argDict = Variable.getDict()

        xmlSrc = argDict['xmlsrc']
        argDict['project']       = self.projectName
        argDict['projectSubdir'] = subdir = self.subdir
        argDict['projectSrcDir'] = projectSrcDir = unixPath(join(xmlSrc, subdir))
        argDict['projectWsDir']  = projectWsDir  = unixPath(join(argDict['workspaceRoot'], subdir))
        argDict['projectXmlDir'] = projectXmlDir = unixPath(join(argDict['localXml'], subdir))
        argDict['baseline']      = argDict['reference'] = baseline = self.baselineName     # baseline is synonym for reference
        argDict['years']         = argDict['startYear'] + '-' + argDict['endYear']
        argDict['scenarioGroup'] = self.scenarioGroupName

        argDict['SEP'] = os.path.sep    # '/' on Unix and '\\' on Windows

        knownGroups    = self.getKnownGroups()
        knownScenarios = self.getKnownScenarios()
        knownSteps     = self.getKnownSteps()

        self.maybeListProjectArgs(args, knownGroups, knownScenarios, knownSteps)

        # Set steps / scenarios to all known values if user doesn't specify any
        steps = steps or knownSteps
        scenarios = scenarios or knownScenarios

        # Check that the requested scenarios and steps are defined
        self.validateProjectArgs(scenarios, knownScenarios, 'scenarios')
        self.validateProjectArgs(steps,     knownSteps,     'steps')

        quitProgram = args.quit

        for scenarioName in scenarios:
            scenario = self.scenarioDict[scenarioName]

            if not scenario.isActive:
                _logger.debug("Skipping inactive scenario: %s", scenarioName)
                continue

            # These get reset as each scenario is processed
            argDict['scenario'] = scenarioName
            argDict['scenarioSubdir'] = scenario.subdir
            argDict['scenarioSrcDir'] = unixPath(join(projectSrcDir, scenario.subdir))
            argDict['scenarioXmlDir'] = unixPath(join(projectXmlDir, scenarioName))
            argDict['scenarioWsDir'] = scenarioWsDir = unixPath(join(projectWsDir, scenarioName))
            argDict['diffsDir'] = unixPath(join(scenarioWsDir, 'diffs'))
            argDict['batchDir'] = unixPath(join(scenarioWsDir, 'batch-' + scenarioName))

            # Evaluate dynamic variables and re-generate temporary files, saving paths in
            # variables indicated in <tmpFile>. This is in the scenario loop so run-time
            # variables are handled correctly, though it does result in the files being
            # written multiple times (though with different values.)
            Variable.evaluateVars(argDict)
            TmpFile.writeFiles(argDict)

            try:
                # Loop over all steps and run those that user has requested
                for step in self.sortedSteps:
                    if step.name in steps:
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


def driver(args, tool):
    if not args.project:
        args.project = getParam('GCAM.DefaultProject')

    if not args.project:
        raise PygcamException("runProj: must specify project name")

    steps = flatten(map(lambda s: s.split(','), args.steps)) if args.steps else None
    scenarios = args.scenarios and flatten(map(lambda s: s.split(','), args.scenarios))
    projectFile = args.projectFile or getParam('GCAM.ProjectXmlFile') or DefaultProjectFile

    parser  = ET.XMLParser(remove_blank_text=True)
    tree    = ET.parse(projectFile, parser)
    project = Project(tree, args.project, args.group)

    # if args.dump:
    #     project.dump(steps, scenarios)

    try:
        project.run(scenarios, steps, args, tool)
    finally:
        TmpFile.deleteFiles()


class ProjectCommand(SubcommandABC):
    VERSION = '0.2'

    def __init__(self, subparsers):
        kwargs = {'help' : '''Run the steps for a project defined in a project.xml file''',
                  'description' : '''This sub-command reads a single XML input file
                        that defines one or more projects, one or more groups of scenarios, one
                        or more scenarios, and one or more workflow steps. The workflow steps
                        for the chosen project and scenario(s) are run in the order defined.'''}

        super(ProjectCommand, self).__init__('runProj', subparsers, kwargs)

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
                            argument, or the -S flag can be repeated to indicate additional steps.
                            By default, all active scenarios are run.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + self.VERSION)

        parser.add_argument('--vars', action='store_true', help='''List variables and their values''')

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
