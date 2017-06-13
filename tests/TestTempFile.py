import unittest
import os
from glob import glob
import shutil

from pygcam.utils import TempFile, getTempFile

class TestTempFile(unittest.TestCase):
    def setUp(self):
        self.tmpDir = './data/tmp/test'
        self.removeTmpDir()
        os.mkdir(self.tmpDir)

    def tearDown(self):
        self.removeTmpDir()

    def removeTmpDir(self):
        try:
            shutil.rmtree(self.tmpDir)
        except:
            pass

    def test_createTempFile(self):
        file = getTempFile('.txt', tmpDir=self.tmpDir, delete=True)

        with open(file, 'w') as f:
            f.write("Test string\n")

        assert os.path.isfile(file), "File was not created"
        TempFile.remove(file)
        assert not os.path.isfile(file), "File was not deleted"

    def test_deletion(self):
        fileCount = 3
        for i in range(fileCount):
            TempFile(suffix='.xml', tmpDir=self.tmpDir, openFile=True)

        files = glob(os.path.join(self.tmpDir, '*'))
        self.assertEqual(len(files), fileCount)

        TempFile.deleteAll()

        files = glob(os.path.join(self.tmpDir, '*'))
        self.assertEqual(len(files), 0)

    def test_noDeletion(self):
        fileCount = 3
        for i in range(fileCount):
            obj = TempFile(suffix='.xml', tmpDir=self.tmpDir, openFile=True, delete=False)
            os.close(obj.fd)

        files = glob(os.path.join(self.tmpDir, '*'))
        self.assertEqual(len(files), fileCount)

        TempFile.deleteAll()

        files = glob(os.path.join(self.tmpDir, '*'))
        self.assertEqual(len(files), fileCount)
        # print "tmpDir has files:", files


if __name__ == "__main__":
    unittest.main()
