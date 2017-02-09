#!/usr/bin/env python2

from pygcam import tool
from pygcam.config import setUsingMCS

# Turn this off for pyinstaller-run versions since MCS works only
# Linux and pyinstaller is currently used only for Mac and Windows.
setUsingMCS(False)

tool.main()
