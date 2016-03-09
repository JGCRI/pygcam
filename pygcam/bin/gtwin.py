#!/usr/bin/env python

'''
.. Windows version of main driver for pygcam tools, which just calls
   the functions defined in gcamtools.py

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import sys
import pygcam.bin.gcamtool as gt
from pygcam.config import DEFAULT_SECTION, getConfig

getConfig(DEFAULT_SECTION)      # TBD: use project as config section

try:
    gt.GcamTool().run()

except Exception, e:
    print "%s failed: %s" % (gt.PROGRAM, e)
    sys.exit(1)

