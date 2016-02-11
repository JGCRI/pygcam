#!/usr/bin/env python
'''
.. Support for running a sequence of operations for a GCAM project
   that is described in an XML file.

.. code-author:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import sys
from pygcam.project import main, parseArgs, PROGRAM
from pygcam.error import PygcamException

if __name__ == '__main__':
    status = -1
    args = parseArgs()

    try:
        main(args)
        status = 0
    except PygcamException as e:
        print "\n****%s: %s" % (PROGRAM, e)

    sys.exit(status)
