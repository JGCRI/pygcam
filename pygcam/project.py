#!/usr/bin/env python
'''
@author: Rich Plevin (rich@plevin.com)

Copyright (c) 2015 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.

Support for running a sequence of operations for a GCAM project
that is described in an XML file.
'''

# TBD: After library is created from the gcam-utils, rewrite this to use it.

import os
import sys
import platform
from itertools import chain
import argparse
import subprocess
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


class TmpFile(object):
    FilesToDelete = []
    Instances = {}  # keyed by name

    def __init__(self, node):
        """
        defaults is an optional TmpFile instance from which to
        take default file contents, which are appended to or
        replaced by the list defined here.
        """
        # e.g., <tmpFile varName="scenPlots" dir="/tmp/runProject" delete="0" replace="1">
        name = node.get('varName')
        if not name:
            raise ProjectException("tmpFile element is missing its required 'name' attribute")

        self.delete  = int(node.get('delete',  '1'))
        self.replace = int(node.get('replace', '0'))
        self.interp  = int(node.get('interpolate', '1'))    # convert {args} before writing file
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

        interp = self.interp

        with open(path, 'w') as f:
            text = '\n'.join(map(lambda x: x.text or '', self.textNodes)) + '\n'
            if interp and text:
                text = text.format(**argDict) if interp else text
            f.write(text)

        self.path = path
        return path


class Scenario(object):
    def __init__(self, node):
        self.name = node.get('name')
        self.isActive   = node.get('active',   default='1') == '1'
        self.isBaseline = node.get('baseline', default='0') == '1'
        self.subdir = node.get('subdir', default=self.name)


class Step(object):
    # seq="1" name="gcam"  scenario="baseline" replace="1"
    def __init__(self, node):
        self.seq     = int(node.get('seq', 0))
        self.name    = node.get('name')
        self.runFor  = node.get('runFor', 'all')
        self.command = node.text

        if not self.name:
            raise ProjectException("<step> requires a name attribute")

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

        print "[%s, %s] %s" % (scenario.name, self.seq, command)

        if not noRun:
            shellCommand(command)


class Project(object):

    def __init__(self, tree, projectName):
        self.projectName = projectName

        projectNode = tree.find('project[@name="%s"]' % projectName)
        if projectNode is None:
            raise ProjectException("Project '%s' is not defined" % projectName)

        self.subdir = projectNode.get('subdir', projectName)        # subdir defaults to project name

        defaultsNode = tree.find('defaults')   # returns 1st match

        scenarioNodes = projectNode.findall('scenario')
        self.scenarioDict = {node.name : node for node in map(Scenario, scenarioNodes)}

        # Check that exactly one active baseline is defined
        baselines = [s for s in scenarioNodes if s.get('baseline', '0') == '1' and s.get('active', '1') == '1']
        if len(baselines) != 1:
            raise ProjectException('Exactly one active baseline scenario must be defined; found %d' % len(baselines))

        self.baseline = baselines[0]
        self.baselineName = self.baseline.get('name')

        def collectInfo(node):
            queriesNode = node.find('queries')
            queries = list(queriesNode.itertext()) if queriesNode is not None else []

            stepNodes = node.findall('./steps/step')
            steps = map(Step, stepNodes)
            return queries, steps

        dfltQueries, dfltSteps = collectInfo(defaultsNode)
        projQueries, projSteps = collectInfo(projectNode)

        # Combine default queries with project-specific queries
        self.queries = dfltQueries + projQueries

        # Combine default steps with project-specific steps
        self.stepsDict = stepsDict = {}
        allSteps = dfltSteps + projSteps

        # project steps with same name and seq overwrite defaults in tmpDict
        for step in allSteps:
            key = "%s-%d" % (step.name, step.seq)
            stepsDict[key] = step

        # sort by seq and save a set of all known steps
        self.stepsList  = sorted(stepsDict.values(), key=lambda node: node.seq)
        self.knownSteps = set([step.name for step in self.stepsList])

        self.vars = {}
        self.varsToEval = [] # TBD: better as a 'Variable' class
        self.setProjectVarsFromNode(defaultsNode)   # set default values
        self.setProjectVarsFromNode(projectNode)    # override whichever are specified

        self.setVarFromDefault('shockYear', 'startYear')    # set defaults from other vars
        self.setVarFromDefault('analysisEndYear', 'endYear')

        self.checkRequiredVars()

        dfltTmpFileNodes = defaultsNode.findall('tmpFile')
        projTmpFileNodes = projectNode.findall('tmpFile')
        self.tmpFiles = map(TmpFile, dfltTmpFileNodes + projTmpFileNodes)


    def checkRequiredVars(self):
        # Ensure that the required vars are set to non-empty strings
        required = ['xmlsrc', 'workspaceRoot', 'localXml']
        missing = []
        for var in required:
            if var not in self.vars or not self.vars[var]:
                missing.append(var)

        if len(missing):
            raise ProjectException("Missing required variables: %s" % missing)

    def setProjectVarsFromNode(self, node):
        nodeList = node.findall('./vars/var')   # allows for multiple <vars> sections
        for elt in nodeList:
            name = elt.get('name')
            if not name:
                raise ProjectException('<var> definition is missing a name attribute')

            if int(elt.get('eval', 0)):
                self.varsToEval.append(name)

            # read config var if indicated
            configVar = elt.get('configVar')
            text = getParam(configVar) if configVar else elt.text
            self.vars[name] = text

    def setVarFromDefault(self, varName, defaultName):
        vars = self.vars
        if not varName in vars:
            vars[varName] = vars[defaultName]

    def evaluateVars(self):
        '''Evaluate vars that indicated eval="1"'''
        argDict = self.argDict
        for name in self.varsToEval:
            text = argDict[name]
            argDict[name] = text.format(**argDict) if text else ''

    def run(self, scenarios, steps, args):
        """
        Command templates can include keywords curly braces that are substituted
        to create the command to execute in the shell. Variables are defined in
        the <vars> section of the project XML file.
        """

        # Create a dict for use in formatting command templates
        vars = self.vars
        self.argDict = argDict = vars.copy()

        subdir = self.subdir
        xmlSrc = vars['xmlsrc']
        argDict['projectSubdir'] = subdir
        argDict['projectSrcDir'] = projectSrcDir = join(xmlSrc, subdir)
        argDict['projectWsDir']  = projectWsDir  = join(vars['workspaceRoot'], subdir)
        argDict['projectXmlDir'] = projectXmlDir = join(vars['localXml'], subdir)
        argDict['project'] = self.projectName
        argDict['baseline'] = argDict['reference'] = baseline = self.baselineName     # baseline is synonym for reference
        argDict['years'] = vars['startYear'] + '-' + vars['endYear']

        # Set steps and scenarios to "all" if user doesn't specify
        if not steps:
            steps = self.knownSteps

        if not scenarios:
            # sorting by the integer value of isBaseline results in baseline preceding scenarios
            sortedScenarios = sorted(self.scenarioDict.values(), key=lambda node: not node.isBaseline)
            scenarios = map(lambda node: node.name, sortedScenarios)

        def listAndExit(strings):
            for s in strings:
                print s
            sys.exit(0)

        if args.listScenarios:
            listAndExit(scenarios)

        if args.listSteps:
            listAndExit(steps)

        if args.vars:
            for name, value in sorted(argDict.iteritems()):
                print "%20s = %s" % (name, value)
            sys.exit(0)

        for stepName in steps:
            if not stepName in self.knownSteps:
                raise ProjectException('Requested step "%s" does not exist in project description' % stepName)

        for scenarioName in scenarios:
            try:
                scenario = self.scenarioDict[scenarioName]
            except:
                raise ProjectException('Scenario "%s" not found for project "%s"' % (scenarioName, self.projectName))

            if not scenario.isActive:
                print '  %s is inactive' % scenarioName
                continue

            # TBD: document the available variables
            argDict['scenario'] = scenarioName
            argDict['scenarioSubdir'] = scenario.subdir
            argDict['scenarioSrcDir'] = join(projectSrcDir, scenario.subdir)
            argDict['scenarioXmlDir'] = join(projectXmlDir, scenario.subdir)
            argDict['scenarioWsDir'] = scenarioWsDir = join(projectWsDir, scenario.name)
            argDict['diffsDir'] = join(scenarioWsDir, 'diffs')
            argDict['batchDir'] = join(scenarioWsDir, 'batch-' + scenarioName)

            # Generate temporary files and save paths in variables indicated in <tmpFile>.
            # This is in the scenario loop so run-time variables are handled correctly,
            # though it does result in the files being written multiple times (though with
            # different values.)
            self.evaluateVars()
            TmpFile.writeFiles(argDict)

            # Loop over all defined steps and run those that user has requested
            for step in self.stepsList:
                if steps is None or step.name in steps:
                    argDict['step'] = step

                    step.run(self, baseline, scenario, argDict, args, noRun=args.noRun)

    def dump(self, steps, scenarios):
        print "Steps:", steps
        print "\nScenarios:", scenarios
        print "\nDefined steps: \n  %s" % "\n  ".join(map(str, self.stepsList))
        print "\nDefined queries:\n  %s" % "\n  ".join(self.queries)
        print '\nDefined vars:'
        for name, value in self.vars.iteritems():
            print "  %15s : %s" % (name, value)
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
