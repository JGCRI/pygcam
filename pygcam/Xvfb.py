'''
Created on 1/19/15

@author : Richard Plevin

Copyright (c) 2015 Richard Plevin. See COPYRIGHT.txt for details.
'''

import os
import subprocess as subp
import time
import re

class XvfbException(Exception):
    pass


class Xvfb(object):
    '''
    Class to wrap the Xvfb (X virtual frame buffer) command to acquire a virtual X11 display.
    This allows X11 apps that (think they) need a display to be run in "headless" mode.
    Sets the environment var DISPLAY to the corresponding value (i.e., for display 1, DISPLAY=":1.0")
    '''
    # The first message in the "|" expression occurs on the Linux systems this has been
    # tested on. The second message occurs on Mac OSX 10.9.
    # This may require updating to run on other systems or versions of these systems.
    lockFailureMsg = "(Could not create server lock file)|(Server is already active for display)"

    def __init__(self, delay=0.2, maxDisplays=20):
        self.delay = delay
        self.maxDisplays = maxDisplays
        self.proc = None
        self.displayNum = None

        self.acquireDisplay()

        # Set environment variable, but save old value to restore later
        self.oldDisplay = os.environ.get("DISPLAY")
        os.environ["DISPLAY"] = ":%d.0" % self.displayNum


    def terminate(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

        os.environ["DISPLAY"] = self.oldDisplay or ""


    def acquireDisplay(self):
        '''
        Loop from display number 0 to self.maxDisplays until we've tried them all or
        we succeed in allocating one.
        :return: The integer number of the allocated display.
        '''

        self.displayNum = None
        for displayNum in range(self.maxDisplays):
            display = ":%d" % displayNum

            args = ['Xvfb', display, '-pn', '-audit', '4', '-screen', '0', '800x600x16']

            try:
                self.proc = subp.Popen(args, stdout=subp.PIPE, stderr=subp.STDOUT)

            except Exception, e:
                raise XvfbException(e)

            time.sleep(self.delay)      # allow time for process to start

            if not self.proc:
                raise XvfbException("Xvfb could not be run")

            retcode = self.proc.poll()
            if retcode is None:         # process is still running
                self.displayNum = displayNum
                return displayNum       # we have acquired a display

            # If Xvfb exited, read stdout to see why
            errmsgs = list(self.proc.stdout)
            lockFailure = any(map(lambda line: re.search(self.lockFailureMsg, line), errmsgs))

            if lockFailure:     # must be allocated to someone else
                continue        # try the next display number

            # Fail if there's any reason other than failing to acquire the lock
            raise XvfbException("Xvfb failed: %s" % errmsgs)

        raise XvfbException("Failed to open any display using Xvfb")


if __name__ == '__main__':
    from coremcs.util import setRunningPackage
    from gcammcs.Package import GcamPackage

    pkg = GcamPackage()
    setRunningPackage(pkg)

    xvfb = None
    try:
        xvfb = Xvfb(delay=0.2)

        print "Do stuff requiring virtual display"
        time.sleep(1)

    except Exception, e:
        print e

    finally:
        if xvfb:
            xvfb.terminate()