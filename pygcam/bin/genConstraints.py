#!/usr/bin/env python
'''
.. Support for running a sequence of operations for a GCAM project
   that is described in an XML file.

.. code-author:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import sys
from os.path import basename
from pygcam.constraints import bioMain
from pygcam.error import PygcamException

VERSION = "0.1"

if __name__ == '__main__':
    status = -1
    program = basename(sys.argv[0])

    try:
        bioMain(program, VERSION)
        status = 0
    except PygcamException as e:
        print "\n****%s: %s" % (program, e)

    sys.exit(status)
