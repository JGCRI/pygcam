#!/usr/bin/env python
'''
.. Copyright (c) 2016 Richard Plevin

   See the https://opensource.org/licenses/MIT for license details.
'''

# Dummy "gt" to tie together pygcam.mcs plugins to generate documentation.

from __future__ import print_function

from ..config import getConfig, setUsingMCS
from ..tool import GcamTool

PROGRAM = 'gt'

class DummyTool(GcamTool):

    def __init__(self):
        super(DummyTool, self).__init__(loadPlugins=False, loadBuiltins=False)


def getMainParser():
    '''
    Used only to generate documentation by sphinx argparse extension, in
    which case we don't generate documentation for project-specific plugins.
    '''
    setUsingMCS(True)
    getConfig(reload=True, allowMissing=True)
    tool = DummyTool().getInstance()
    return tool.parser
