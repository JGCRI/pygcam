#!/usr/bin/env python
'''
a@author: Rich Plevin (rich@plevin.com)

Copyright (c) 2015-2016 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.
'''
import sys
import os
from pygcam.landProtection import ToolException, main, parseArgs

if __name__ == '__main__':
    program = os.path.basename(__file__)
    version = '0.1'

    status = -1
    args = parseArgs(program, version)

    try:
        main(args)
        status = 0
    except ToolException as e:
        print "%s: %s" % (program, e)

    sys.exit(status)
