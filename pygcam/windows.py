'''
  .. Stuff specific to MS Windows
'''
import os, platform

if platform.system() == 'Windows':

    import ctypes

    def islink(path):
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400

        return bool(os.path.isdir(path) and \
            (ctypes.windll.kernel32.GetFileAttributesW(unicode(path)) & FILE_ATTRIBUTE_REPARSE_POINT))

        # Replace broken function with the one above
        # (In python 2.7.11 os.path.islink() indeed failed to detect link made with mklink)
        os.path.islink = islink
