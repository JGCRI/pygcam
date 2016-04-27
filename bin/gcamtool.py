#!/usr/bin/env python

'''
.. Main driver for pygcam tools, which are accessed as sub-commands.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import sys
import argparse
import signal
from pygcam.config import getConfig, getParam, getParamAsBoolean, getSection, setSection
from pygcam.log import getLogger, configureLogs
from pygcam.tool import GcamTool, PROGRAM
from pygcam.utils import TempFile
from pygcam.windows import IsWindows

if IsWindows:
    SignalsToCatch = [signal.SIGTERM, signal.SIGINT, signal.SIGABRT]
else:
    SignalsToCatch = [signal.SIGTERM, signal.SIGINT, signal.SIGQUIT]

_logger = getLogger(__name__)


class SignalException(Exception):
    pass

def _sigHandler(signum, _frame):
    raise SignalException(signum)


def main():
    getConfig()
    configureLogs()

    # This parser handles only --batch, --showBatch, and --projectName args.
    # If --batch is given, we need to create a script and call the GCAM.BatchCommand
    # on it. We grab --projectName so we can set PluginPath by project
    parser = argparse.ArgumentParser(prog=PROGRAM, add_help=False)

    parser.add_argument('-b', '--batch', action='store_true')
    parser.add_argument('-B', '--showBatch', action="store_true")
    parser.add_argument('-P', '--projectName', dest='configSection', metavar='name')

    ns, otherArgs = parser.parse_known_args()

    if ns.configSection:
        ns.configSection = section = ns.configSection or getParam('GCAM.DefaultProject')
        if section:
            setSection(section)

    if ns.showBatch:          # don't run batch command); --showBatch implies --batch
        ns.batch = True

    # Catch these to allow cleanup of TempFile instances, e.g., on ^C
    for sig in SignalsToCatch:
        signal.signal(sig, _sigHandler)

    tool = GcamTool()

    try:
        if ns.batch:
            run = not ns.showBatch
            tool.runBatch(otherArgs, run=run)
        else:
            args = tool.parser.parse_args(args=otherArgs)
            tool.run(args=args)
    finally:
        # Delete any temporary files that were created, but only when
        # after existing any recursive invocation.
        TempFile.deleteAll()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print "%s failed: %s" % (PROGRAM, e)

        if not getSection() or getParamAsBoolean('GCAM.ShowStackTrace'):
            import traceback
            traceback.print_exc()

        sys.exit(1)
