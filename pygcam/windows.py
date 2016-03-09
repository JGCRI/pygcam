'''
  .. Stuff specific to MS Windows
'''

import os, ctypes, platform

def IsSymlink(path):
    FILE_ATTRIBUTE_REPARSE_POINT = 0x0400

    return os.path.isdir(path) and \
        (ctypes.windll.kernel32.GetFileAttributesW(unicode(path)) & FILE_ATTRIBUTE_REPARSE_POINT)


if platform.system() == 'Windows':
    # Replace broken function with the one above
    os.path.islink = IsSymlink
