#!/usr/bin/env python
'''
@author: Rich Plevin (rich@plevin.com)

Copyright (c) 2015 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.

Support for running a sequence of operations for a GCAM project
that is described in an XML file.
'''
import sys

# Read the following imports from the same dir as the script
# sys.path.insert(0, dirname(dirname(dirname(sys.argv[0]))))
# print 'sys.path=',sys.path

from pygcam.project import ToolException, main, parseArgs, PROGRAM

if __name__ == '__main__':
    status = -1
    args = parseArgs()

    try:
        main(args)
        status = 0
    except ToolException as e:
        print "\n****%s: %s" % (PROGRAM, e)

    sys.exit(status)
