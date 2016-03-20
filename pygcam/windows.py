'''
  .. Stuff specific to MS Windows
'''
import os
import sys
import platform
from pygcam.error import PygcamException

if platform.system() == 'Windows':

    import ctypes

    def islinkWindows(path):
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400

        return bool(os.path.isdir(path) and \
            (ctypes.windll.kernel32.GetFileAttributesW(unicode(path)) & FILE_ATTRIBUTE_REPARSE_POINT))

    # Adapted from http://timgolden.me.uk/python/win32_how_do_i/see_if_two_files_are_the_same_file.html
    import tempfile
    import win32file

    def get_read_handle(filename):
        if os.path.isdir(filename):
            dwFlagsAndAttributes = win32file.FILE_FLAG_BACKUP_SEMANTICS
        else:
            dwFlagsAndAttributes = 0

        # CreateFile(fileName, desiredAccess, shareMode, attributes,
        #            CreationDisposition, flagsAndAttributes, hTemplateFile)
        try:
            handle = win32file.CreateFileW(filename,  # with 'W' accepts unicode
                         win32file.GENERIC_READ, win32file.FILE_SHARE_READ, None,
                         win32file.OPEN_EXISTING, dwFlagsAndAttributes, None)
            return handle
        except Exception as e:
            raise PygcamException("get_read_handle(%s) failed: %s" % (filename, e))

    def get_unique_id (hFile):
        (attributes, created_at, accessed_at, written_at,
         volume, file_hi, file_lo, n_links,
         index_hi, index_lo) = win32file.GetFileInformationByHandle(hFile)
        return volume, index_hi, index_lo

    def samefileWindows(filename1, filename2):
        # If either of the files does not exist, create it and close
        # it to use get_read_handle(), then remove the files we created.
        # Yes, there's a race condition here, but Windows is lame...
        try:
            f1 = f2 = None
            hFile1 = hFile2 = None

            if not os.path.lexists(filename1):
                f1 = open(filename1, 'w')
                f1.close()

            if not os.path.lexists(filename2):
                f2 = open(filename2, 'w')
                f2.close()

            hFile1 = get_read_handle(filename1)
            hFile2 = get_read_handle(filename2)
            are_equal = (get_unique_id(hFile1) == get_unique_id(hFile2))

        finally:
            if hFile1:
                hFile1.Close()
            if hFile2:
                hFile2.Close()
            if f1:
                os.unlink(filename1)
            if f2:
                os.unlink(filename2)

        return are_equal

    # Adapted from http://stackoverflow.com/questions/6260149/os-symlink-support-in-windows
    # NOTE: Requires SeCreateSymbolicLink priv.
    def symlinkWindows(src, dst):
        if samefileWindows(src, dst):
            raise PygcamException("Attempted to create symlink loop from '%s' to '%s' (same file)" % (dst, src))

        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        src = src.replace('/', '\\')
        flags = 1 if os.path.isdir(src) else 0

        try:
            if csl(dst, src, flags) == 0:
                raise ctypes.WinError()
        except Exception as e:
            raise PygcamException("Failed to create symlink '%s' to '%s': %s" % (dst, src, e))
            pass

    # Replace broken functions with those defined above.
    # (In python 2.7.11 os.path.islink() indeed failed to detect link made with mklink)
    os.symlink = symlinkWindows
    os.path.islink = islinkWindows
    os.path.samefile = samefileWindows


    def setPathForJava():
        '''
        Update the PATH to be able to find the Java dlls.
        Modeled on run-gcam.bat in the GCAM distribution.
        '''
        if os.environ['JAVA_HOME']:
            path = os.environ['PATH']
            javaHome = os.environ['JAVA_HOME']

            # SET PATH=%PATH%;%JAVA_HOME%\bin;%JAVA_HOME%\bin\server"
            os.environ['PATH'] = path + ';' + javaHome + r'\bin;' + javaHome + r'\bin\server'


if __name__ == '__main__':
    #
    # This bit of the example will only work on Win2k+; it
    # was the only way I could reasonably produce two different
    # files which were the same file, without knowing anything
    # about your drives, network etc.
    #
    filename1 = sys.executable
    filename2 = tempfile.mktemp(".exe")
    win32file.CreateHardLink(filename2, filename1, None)
    print filename1, filename2, samefileWindows(filename1, filename2)
