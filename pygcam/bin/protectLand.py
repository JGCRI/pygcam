#!/usr/bin/env python
'''
.. Main program for generating land-protection scenarios.

.. code-author:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2015-2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import sys
from os.path import basename
from pygcam.landProtection import main
from pygcam.error import PygcamException

VERSION = "0.1"

if __name__ == '__main__':
    status = -1
    program = basename(sys.argv[0])

    try:
        main(program, VERSION)
        status = 0
    except PygcamException as e:
        print "%s: %s" % (program, e)

    sys.exit(status)
