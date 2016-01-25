#!/usr/bin/env python
'''
@author: Rich Plevin (rich@plevin.com)

Copyright (c) 2015 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.

Support for running a sequence of operations for a GCAM project
that is described in an XML file.
'''

# TBD: After library is created from the gcam-utils, rewrite this to use it.

# TBD: Implement reading from config file for <var configVar="GCAM.QueryPath">
# TBD: Allow user to specify QueryFile or list the queries in project.xml and write to tmp file
# TBD: Allow projects to de-activate select queries (see project.xml)
# TBD: Generalize "save this list of stuff to a tmp file with a given variable name,
# TBD:  e.g., <tempFile dir="/tmp" delete="1" var="queryFile"><text>asdfasdf</text></tempFile>
# TBD:  where the <text> elements are written to a temp file in "dir", and the name of the
# TBD:  file is assigned to var with name given in the "var" attribute.

import os
import sys
import platform
from itertools import chain
import argparse
import subprocess
from lxml import etree as ET
from pygcam.config import readConfigFiles, getParam

# Read the following imports from the same dir as the script
sys.path.insert(0, os.path.dirname(sys.argv[0]))

PROGRAM = os.path.basename(__file__)
VERSION = "0.1"
PlatformName = platform.system()
Verbose = False

class ProjectException(Exception):
    pass

DefaultProjectFile = os.path.join(os.getenv('HOME'), 'project.xml')

def parseArgs():
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description='''Perform a series of steps typical for a GCAM-based analysis. This script
        reads instructions from the file project.xml, the location of which is taken from the
        user's pygcam.cfg file.''')

    parser.add_argument('project', help='''The project to run.''')

    parser.add_argument('-l', '--listSteps', action='store_true', default=False,
                        help='''List the steps defined for the given project and exit.''')

    parser.add_argument('-L', '--listScenarios', action='store_true', default=False,
                        help='''List the scenarios defined for the given project and exit.''')

    parser.add_argument('-n', '--noRun', action='store_true', default=False,
                        help='''Display the commands that would be run, but don't run them.''')

    parser.add_argument('-p', '--projectFile', default=DefaultProjectFile,
                        help='''The directory into which to write the modified files.
                        Default is current directory.''')

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

class PlotInfo(object):
    def __init__(self, tree, xpath, defaults=None):
        """
        defaults is an optional PlotInfo instance from which to
        take default plot commands, which are appended to our list.
        """
        dfltCommonArgs = defaults.commonArgs if defaults else ''

        node = tree.find(xpath)
        if node is None:
            self.plotCommands = []
            self.commonArgs = dfltCommonArgs
        else:
            self.plotCommands = list(node.itertext(tag='plot'))
            self.commonArgs = node.findtext('commonArgs', default=dfltCommonArgs)

        if defaults:
            self.plotCommands += defaults.plotCommands


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

        command = self.command.format(**argDict)    # replace vars in template
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
        self.setProjectVarsFromNode(defaultsNode)   # set default values
        self.setProjectVarsFromNode(projectNode)    # override whichever are specified

        self.setVarFromDefault('shockYear', 'startYear')    # set defaults from other vars
        self.setVarFromDefault('analysisEndYear', 'endYear')

        dfltScenInfo = PlotInfo(defaultsNode, 'scenarioPlots')
        dfltDiffInfo = PlotInfo(defaultsNode, 'diffPlots')

        # The project appends to default plot commands, but it replaces common plot args
        self.scenPlotInfo = PlotInfo(projectNode, 'scenarioPlots', defaults=dfltScenInfo)
        self.diffPlotInfo = PlotInfo(projectNode, 'diffPlots',     defaults=dfltDiffInfo)

        self.vars['scenarioPlotArgs'] = self.scenPlotInfo.commonArgs
        self.vars['diffPlotArgs']     = self.diffPlotInfo.commonArgs

        self.checkRequiredVars()


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

            # read config var if indicated
            configVar = elt.get('configVar')
            value = getParam(configVar) if configVar else elt.text
            self.vars[name] = value

    def setVarFromDefault(self, varName, defaultName):
        vars = self.vars
        if not varName in vars:
            vars[varName] = vars[defaultName]

    def run(self, scenarios, steps, args):
        """
        Command templates can include keywords curly braces that are substituted
        to create the command to execute in the shell. Variables are defined in
        the <vars> section of the project XML file.
        """
        # TBD: document the available variables
        # Create a dict for use in formatting command templates
        vars = self.vars
        argDict = vars.copy()
        subdir = self.subdir
        xmlSrc = vars['xmlsrc']
        argDict['projectSubdir'] = subdir
        argDict['projectSrcDir'] = projectSrcDir = os.path.join(xmlSrc, subdir)
        argDict['projectWsDir']  = projectWsDir  = os.path.join(vars['workspaceRoot'], subdir)
        argDict['projectXmlDir'] = projectXmlDir = os.path.join(vars['localXml'], subdir)
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
            argDict['scenarioSrcDir'] = os.path.join(projectSrcDir, scenario.subdir)
            argDict['scenarioXmlDir'] = os.path.join(projectXmlDir, scenario.subdir)
            argDict['scenarioWsDir'] = scenarioWsDir = os.path.join(projectWsDir, scenario.name)
            argDict['diffsDir'] = os.path.join(scenarioWsDir, 'diffs')
            argDict['batchDir'] = os.path.join(scenarioWsDir, 'batch-' + scenarioName)

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


def main():
    args = parseArgs()
    readConfigFiles()

    global Verbose
    Verbose = args.verbose

    steps = flatten(map(lambda s: s.split(','), args.steps)) if args.steps else None
    scenarios = args.scenarios and flatten(map(lambda s: s.split(','), args.scenarios))
    projectFile = args.projectFile
    projectName = args.project

    parser  = ET.XMLParser(remove_blank_text=True)
    tree    = ET.parse(projectFile, parser)
    project = Project(tree, projectName)

    if args.verbose:
        project.dump(steps, scenarios)

    project.run(scenarios, steps, args)

if __name__ == '__main__':
    status = -1
    try:
        main()
        status = 0
    except ProjectException as e:
        print "%s: %s" % (PROGRAM, e)

    sys.exit(status)
