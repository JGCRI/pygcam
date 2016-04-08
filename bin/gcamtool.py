#!/usr/bin/env python

'''
.. Main driver for pygcam tools, which are accessed as sub-commands.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''

import sys
from pygcam.config import getConfig, getParamAsBoolean
from pygcam.log import getLogger, configureLogs
from pygcam.tool import GcamTool, PROGRAM

_logger = getLogger(__name__)

def main():
    # Use default section initially, to read plugin path.
    # It's a chicken-and-egg problem since we can't parse args
    # until we've loaded all the plugins, but the PluginPath is
    # defined in the config file.
    getConfig()
    configureLogs()

    tool = GcamTool()
    args = tool.parser.parse_args()
    tool.run(args=args)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print "%s failed: %s" % (PROGRAM, e)

        if getParamAsBoolean('GCAM.ShowStackTrace'):
            import traceback
            traceback.print_exc()

        sys.exit(1)
