#!/usr/bin/env python
'''
.. Main program for generating land-protection scenarios.

.. code-author:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import sys
from pygcam.landProtection import main, parseArgs, PROGRAM
from pygcam.error import PygcamException

if __name__ == '__main__':
    args = parseArgs()
    status = -1

    try:
        main(args)
        status = 0
    except PygcamException as e:
        print "%s: %s" % (PROGRAM, e)

    sys.exit(status)
