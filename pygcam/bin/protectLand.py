#!/usr/bin/env python
'''
a@author: Rich Plevin (rich@plevin.com)

Copyright (c) 2015-2016 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.
'''
import sys
from pygcam.landProtection import ToolException, main, parseArgs, PROGRAM

if __name__ == '__main__':
    args = parseArgs()
    status = -1

    try:
        main(args)
        status = 0
    except ToolException as e:
        print "%s: %s" % (PROGRAM, e)

    sys.exit(status)
