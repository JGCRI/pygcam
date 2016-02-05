#!/usr/bin/env python
'''
@author: Rich Plevin (rich@plevin.com)

Copyright (c) 2015 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.

Support for running a sequence of operations for a GCAM project
that is described in an XML file.
'''

import os
import sys
import platform
import argparse

# Read the following imports from the same dir as the script
# sys.path.insert(0, dirname(dirname(dirname(sys.argv[0]))))
# print 'sys.path=',sys.path

from pygcam.project import ToolException, main

PROGRAM = os.path.basename(__file__)
VERSION = "0.1"
PlatformName = platform.system()
Verbose = False

def parseArgs():
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description='''Perform a series of steps typical for a GCAM-based analysis. This script
        reads instructions from the file project.xml, the location of which is taken from the
        user's pygcam.cfg file.''')

    parser.add_argument('project', help='''The project to run.''')

    parser.add_argument('-g', '--group', type=str, default=None,
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

    parser.add_argument('-p', '--projectFile', default=None,
                        help='''The directory into which to write the modified files.
                        Default is taken from config file variable GCAM.ProjectXmlFile,
                        if defined, otherwise the default is './project.xml'.''')

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

if __name__ == '__main__':
    status = -1

    args = parseArgs()

    try:
        main(args)
        status = 0
    except ToolException as e:
        print "%s: %s" % (PROGRAM, e)

    sys.exit(status)
