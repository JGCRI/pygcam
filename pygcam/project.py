#!/usr/bin/env python
"""
@author: Rich Plevin (rich@plevin.com)

Copyright (c) 2015 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.

Support for running a sequence of operations for a GCAM project
that is described in an XML file.
"""

# TBD: After library is created from the gcam-utils, rewrite this to use it.

import os
import sys
import platform
from itertools import chain
import argparse
import subprocess
#from collections import OrderedDict
from os.path import join
from lxml import etree as ET
from .config import readConfigFiles, getParam
from .common import getTempFile

PROGRAM = os.path.basename(__file__)
VERSION = "0.1"
PlatformName = platform.system()
Verbose = False

class ProjectException(Exception):
    pass

DefaultProjectFile = './project.xml'

def parseArgs():
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description='''Perform a series of steps typical for a GCAM-based analysis. This script
        reads instructions from the file project.xml, the location of which is taken from the
        user's pygcam.cfg file.''')

    parser.add_argument('project', help='''The project to run.''')

    parser.add_argument('-l', '--listSteps', action='store_true', default=False,
                        help='''List the steps defined for the given project and exit.
                        Dynamic variables (created at run-time) are not displayed.''')

    parser.add_argument('-L', '--listScenarios', action='store_true', default=False,
                        help='''List the scenarios defined for the given project and exit.
                        Dynamic variables (created at run-time) are not displayed.''')

    parser.add_argument('-n', '--noRun', action='store_true', default=False,
                        help='''Display the commands that would be run, but don't run them.''')

    parser.add_argument('-p', '--projectFile', default=None,
                        help='''The directory into which to write the modified files.
                        Default is taken from config file variable GCAM.ProjectXmlFile,
                        if defined, otherwise the default is '%s'.''' % DefaultProjectFile)

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

    parser.add_argument('--vars', action='store_true', help='''List variables and their values''')

    parser.add_argument('-v', '--verbose', action='store_true', help='''Show diagnostic output''')

    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + VERSION)

    args = parser.parse_args()
    return args


def flatten(listOfLists):
    "Flatten one level of nesting"
    return list(chain.from_iterable(listOfLists))

def shellCommand(command):
    exitStatus = subprocess.call(command, shell=True)
    if exitStatus <> 0:
        raise ProjectException("Command failed: %s\nexit status %s" % (command, exitStatus))

def checkAttributes(node, allowed, required):
    """
    Checks that the node has all required attributes and doesn't
    have any unknown attributes. The arguments 'given' and 'required'
    are sets.
    """
    given = set(node.keys())

    missing = required - given
    if missing:
        raise ProjectException('<%s> element is missing required attributes: %s' % (node.tag, ' '.join(missing)))

    unknown = given - allowed
    if unknown:
        raise ProjectException('<%s> element has unknown attributes: %s' % (node.tag, ' '.join(unknown)))

def getBaseline(scenarioNodes):
    '''Check that exactly one active baseline is defined, and if so, return it'''

    baselines = [s for s in scenarioNodes if s.get('baseline', '0') == '1' and s.get('active', '1') == '1']
    if len(baselines) == 1:
        return baselines[0]

    raise ProjectException('Exactly one active baseline scenario must be defined; found %d' % len(baselines))


class TmpFile(object):
    FilesToDelete = []
    Instances = {}  # keyed by name
    Allowed  = {'varName', 'delete', 'replace', 'eval', 'dir'}
    Required = {'varName'}

    def __init__(self, node):
        """
        defaults is an optional TmpFile instance from which to
        take default file contents, which are appended to or
        replaced by the list defined here.
        """
        checkAttributes(node, self.Allowed, self.Required)

        # e.g., <tmpFile varName="scenPlots" dir="/tmp/runProject" delete="1" replace="0" eval="1">
        name = node.get('varName')
        if not name:
            raise ProjectException("tmpFile element is missing its required 'name' attribute")

        self.delete  = int(node.get('delete',  '1'))
        self.replace = int(node.get('replace', '0'))
        self.eval    = int(node.get('eval',    '1'))    # convert {args} before writing file
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
                print "WARNING: Failed to delete file '%s" % path

    @classmethod
    def writeFiles(cls, argDict):
        for tmpFile in cls.Instances.values():
            path = tmpFile.write(argDict)
            argDict[tmpFile.varName] = path

    def write(self, argDict):
        path = getTempFile('.txt', tmpDir=self.dir)
        if self.delete:
            self.FilesToDelete.append(path)

        with open(path, 'w') as f:
            text = '\n'.join(map(lambda x: x.text or '', self.textNodes)) + '\n'
            if text and self.eval:
                text = text.format(**argDict)
            f.write(text)

        self.path = path
        return path


class Scenario(object):
    Allowed  = {'name', 'active', 'baseline', 'subdir'}
    Required = {'name'}

    def __init__(self, node):
        checkAttributes(node, self.Allowed, self.Required)

        self.name = node.get('name')
        self.isActive   = node.get('active',   default='1') == '1'
        self.isBaseline = node.get('baseline', default='0') == '1'
        self.subdir = node.get('subdir', default=self.name)


class Step(object):
    Allowed  = {'name', 'seq', 'runFor'}
    Required = {'name', 'seq'}

    def __init__(self, node):
        checkAttributes(node, self.Allowed, self.Required)

        self.seq     = int(node.get('seq', 0))
        self.name    = node.get('name')
        self.runFor  = node.get('runFor', 'all')
        self.command = node.text

        if not self.command:
            raise ProjectException("<step name='%s'> is missing command text" % self.name)

    def __str__(self):
        return "<Step name='%s' seq='%s' runFor='%s'>%s</Step>" % \
               (self.name, self.seq, self.runFor, self.command)

    def run(self, project, baseline, scenario, argDict, args, noRun=False):
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
            raise ProjectException("%s -- No such variable exists in the project XML file" % e)

        print "[%s, %s, %s] %s" % (scenario.name, self.seq, self.name, command)

        if not noRun:
            shellCommand(command)

class Variable(object):
    Allowed  = {'name', 'eval', 'configVar'}
    Required = {'name'}
    Instances = {}

    def __init__(self, node):
        checkAttributes(node, self.Allowed, self.Required)
        self.name = node.get('name')
        self.configVar = configVar = node.get('configVar')
        self.value = getParam(configVar) if configVar else node.text
        self.eval = int(node.get('eval', 0))

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
    Allowed  = {'name', 'subdir'}
    Required = {'name'}

    def __init__(self, tree, projectName):
        self.projectName = projectName

        projectNodes = tree.findall('project[@name="%s"]' % projectName)

        if len(projectNodes) == 0:
            raise ProjectException("Project '%s' is not defined" % projectName)

        if len(projectNodes) > 1:
            raise ProjectException("Project '%s' is defined %d times" % (projectName, len(projectNodes)))

        projectNode = projectNodes[0]

        checkAttributes(projectNode, self.Allowed, self.Required)

        self.subdir = projectNode.get('subdir', projectName)        # subdir defaults to project name

        defaultsNode = tree.find('defaults')   # returns 1st match

        scenarioNodes = projectNode.findall('scenario')
        self.scenarioDict = {node.name : node for node in map(Scenario, scenarioNodes)}

        self.baselineNode = getBaseline(scenarioNodes)
        self.baselineName = self.baselineNode.get('name')

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

    def checkRequiredVars(self):
        # Ensure that the required vars are set to non-empty strings
        required = {'xmlsrc', 'workspaceRoot', 'localXml'}
        given = set(Variable.definedVars())
        missing = required - given
        if missing:
            raise ProjectException("Missing required variables: %s" % missing)

    def maybeListProjectArgs(self, args, knownScenarios, knownSteps):
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

        if args.listScenarios:
            showList(knownScenarios, 'Scenarios:')

        if args.listSteps:
            showList(knownSteps, 'Steps:')

        if args.vars:
            varList = ["%15s = %s" % (name, value) for name, value in sorted(argDict.iteritems())]
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
        Return a list of known scenarios for the current project, alpha sorted
        '''
        # sorting by not(node.isBaseline) results in baseline preceding scenarios
        self.sortedScenarios = sorted(self.scenarioDict.values(), key=lambda node: not node.isBaseline)
        knownScenarios  = map(lambda node: node.name, self.sortedScenarios)
        return knownScenarios

    def validateProjectArgs(self, userArgs, knownArgs, argName):
        '''
        If the user requested steps or scenarios that are not defined, raise an error.
        '''
        unknownArgs = set(userArgs) - set(knownArgs)
        if unknownArgs:
            s = ' '.join(unknownArgs)
            raise ProjectException("Requested %s do not exist in project %s: %s" % \
                                   (argName, self.projectName, s))

    def run(self, scenarios, steps, args):
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
        argDict['projectSrcDir'] = projectSrcDir = join(xmlSrc, subdir)
        argDict['projectWsDir']  = projectWsDir  = join(argDict['workspaceRoot'], subdir)
        argDict['projectXmlDir'] = projectXmlDir = join(argDict['localXml'], subdir)
        argDict['baseline']      = argDict['reference'] = baseline = self.baselineName     # baseline is synonym for reference
        argDict['years']         = argDict['startYear'] + '-' + argDict['endYear']

        knownScenarios = self.getKnownScenarios()
        knownSteps     = self.getKnownSteps()

        self.maybeListProjectArgs(args, knownScenarios, knownSteps)

        # Set steps / scenarios to all known values if user doesn't specify any
        steps = steps or knownSteps
        scenarios = scenarios or knownScenarios

        # Check that the requested scenarios and steps are defined
        self.validateProjectArgs(scenarios, knownScenarios, 'scenarios')
        self.validateProjectArgs(steps,     knownSteps,     'steps')

        for scenarioName in scenarios:
            scenario = self.scenarioDict[scenarioName]

            if not scenario.isActive:
                print '  Skipping inactive scenario: %s' % scenarioName
                continue

            # These get reset as each scenario is processed
            argDict['scenario'] = scenarioName
            argDict['scenarioSubdir'] = scenario.subdir
            argDict['scenarioSrcDir'] = join(projectSrcDir, scenario.subdir)
            argDict['scenarioXmlDir'] = join(projectXmlDir, scenario.subdir)
            argDict['scenarioWsDir'] = scenarioWsDir = join(projectWsDir, scenarioName)
            argDict['diffsDir'] = join(scenarioWsDir, 'diffs')
            argDict['batchDir'] = join(scenarioWsDir, 'batch-' + scenarioName)

            # Evaluate dynamic variables and re-generate temporary files, saving paths in
            # variables indicated in <tmpFile>. This is in the scenario loop so run-time
            # variables are handled correctly, though it does result in the files being
            # written multiple times (though with different values.)
            Variable.evaluateVars(argDict)
            TmpFile.writeFiles(argDict)

            # Loop over all steps and run those that user has requested
            for step in self.sortedSteps:
                if step.name in steps:
                    argDict['step'] = step.name
                    step.run(self, baseline, scenario, argDict, args, noRun=args.noRun)

    def dump(self, steps, scenarios):
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


def main(args):
    readConfigFiles()

    global Verbose
    Verbose = args.verbose

    steps = flatten(map(lambda s: s.split(','), args.steps)) if args.steps else None
    scenarios = args.scenarios and flatten(map(lambda s: s.split(','), args.scenarios))
    projectFile = getParam('GCAM.ProjectXmlFile') or args.projectFile or './project.xml'
    projectName = args.project

    parser  = ET.XMLParser(remove_blank_text=True)
    tree    = ET.parse(projectFile, parser)
    project = Project(tree, projectName)

    if args.verbose:
        project.dump(steps, scenarios)

    try:
        project.run(scenarios, steps, args)
    finally:
        TmpFile.deleteFiles()
