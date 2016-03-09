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

    # From http://stackoverflow.com/questions/6260149/os-symlink-support-in-windows
    def symlink(src, dst):
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        src = src.replace('/', '\\')
        flags = 1 if os.path.isdir(src) else 0
        
        try:
            if csl(dst, src, flags) == 0:
                raise ctypes.WinError()
        except:
            print "Failed to create symlink '%s' to '%s'" % (dst, src)
            pass

    os.symlink = symlink
