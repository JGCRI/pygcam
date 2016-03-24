#!/usr/bin/env python

'''
.. Main driver for pygcam tools, which are accessed as sub-commands.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''

import sys
from pygcam.config import getConfig
from pygcam.log import getLogger, setLevel, configureLogs
from pygcam.tool import GcamTool, PROGRAM

_logger = getLogger(__name__)

def main():
    # Use default section to read plugin path initially.
    # It's a chicken-and-egg problem since we can't parse args
    # until we've loaded all the plugins. Thus we can't use
    # the 'project' arg until we've already loaded them.
    getConfig()
    configureLogs()

    tool = GcamTool()
    args = tool.parser.parse_args()

    if args.configSection:
        getConfig(section=args.configSection, reload=True)
        if args.logLevel:
            setLevel(args.logLevel)
        configureLogs(force=True)

    tool.run(args=args)


if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print "%s failed: %s" % (PROGRAM, e)

        if True: # getLevel() == 'DEBUG':
            import traceback
            traceback.print_exc()

        sys.exit(1)
