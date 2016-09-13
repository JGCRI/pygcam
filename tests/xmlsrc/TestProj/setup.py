#!/usr/bin/env python
#
import sys
from os.path import dirname, realpath

XmlSourceDir = dirname(realpath(sys.argv[0]))
sys.path.insert(0, dirname(dirname(dirname(XmlSourceDir))))

from pygcam.scenarioSetup import ConfigEditor
from pygcam.sectorEditors import RefiningEditor, BioenergyEditor

# Paper1.scenarios import (BiofuelShock, ResultsDir, XmlOutputRoot,
#                                  cornName, cornTag, cellName, cellTag,
#                                  bdName, bdTag, ftName, ftTag)
# from xmlsrc.lib.BaseScenario import parseArgs

# from xmlsrc.common.genDeltaConstraints import genDeltaConstraints

# This sets default baseline and scenario, both of which can be
# overridden on the command-line to scenarioSetup.py
args = ConfigEditor.parseArgs(baseline='base-1', scenario='corn-1')

BaselineName  = args.baseline
ScenarioName  = args.scenario
Years         = args.years
resultsDir    = args.resultsDir # or ResultsDir
generate      = not args.noGenerate
#xmlOutputRoot = args.xmlOutputRoot or XmlOutputRoot

cornPolicyType = 'subsidy'
cellPolicyType = 'subsidy'
ftPolicyType   = 'subsidy'
bdPolicyType   = 'subsidy'

cornTag = 'corn ethanol'
cellTag = 'cellulosic ethanol'
ftTag   = 'FT biofuels'
bdTag   = 'biodiesel'

UseDynXml = False

class BiofuelShock(ConfigEditor, RefiningEditor, BioenergyEditor):
    def __init__(self, *args, **kwargs):
        super(BiofuelShock, self).__init__(*args, **kwargs)

s = BiofuelShock(ScenarioName, BaselineName, XmlOutputRoot, XmlSourceDir)
s.setup(dynamic=UseDynXml)
s.setSolutionTolerance(0.01)

s.addMarketConstraint(cornTag, cornPolicyType, dynamic=UseDynXml)
s.addMarketConstraint(cellTag, cellPolicyType, dynamic=UseDynXml)
s.addMarketConstraint(ftTag,   ftPolicyType,   dynamic=UseDynXml)
s.addMarketConstraint(bdTag,   bdPolicyType,   dynamic=UseDynXml)
