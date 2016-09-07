import os
import sys
import unittest

from pygcam.windows import IsWindows

def printLink(path):
    islink = os.path.islink(os.path.normpath(path))
    sys.stderr.write("%s islink: %s\n" % (path, islink))
    if islink:
        path = os.readlink(path)
        sys.stderr.write("Link: %s" % path)
        # printLink(path)

class TestSymlinks(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_funcs(self):
        if IsWindows:
            from pygcam.windows import islinkWindows, readlinkWindows
            self.assertEqual(os.path.islink, islinkWindows)
            self.assertEqual(os.readlink, readlinkWindows)

    def test_islink(self):
        if IsWindows:
            p1 = 'C:/Users/rjp/GCAM/current'
            self.assertTrue(os.path.islink(p1), '%s should be seen as a link' % p1)

            p2 = p1 + '/Main_User_Workspace'

            self.assertFalse(os.path.islink(p2), '%s should not be seen as a link' % p2)
