'''
  .. Stuff specific to MS Windows
'''
import platform

if platform.system() == 'Windows':
    print "Loading Windows support functions..."

    import os
    import sys
    from .common import mkdirs
    from .error import PygcamException
    import ctypes

    def islinkWindows(path):
        FILE_ATTRIBUTE_REPARSE_POINT = 0x0400

        return bool(os.path.isdir(path) and \
            (ctypes.windll.kernel32.GetFileAttributesW(unicode(path)) & FILE_ATTRIBUTE_REPARSE_POINT))

    # Adapted from http://timgolden.me.uk/python/win32_how_do_i/see_if_two_files_are_the_same_file.html
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
        # And yes, this has the side-effect of possibly creating directories
        # that aren't deleted.
        try:
            f1 = f2 = None
            hFile1 = hFile2 = None

            if not os.path.lexists(filename1):
                mkdirs(os.path.dirname(filename1))
                f1 = open(filename1, 'w')
                f1.close()

            if not os.path.lexists(filename2):
                mkdirs(os.path.dirname(filename2))
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


    def setJavaPath():
        '''
        Update the PATH to be able to find the Java dlls.
        Modeled on run-gcam.bat in the GCAM distribution.
        '''
        javaHome = os.environ.get('JAVA_HOME', None)
        if javaHome:
            path = os.environ['PATH']
            # SET PATH=%PATH%;%JAVA_HOME%\bin;%JAVA_HOME%\bin\server"
            os.environ['PATH'] = path + ';' + javaHome + r'\bin;' + javaHome + r'\bin\server'


    # Adapted from
    # http://stackoverflow.com/questions/19672352/how-to-run-python-script-with-elevated-privilege-on-windows
    def runAsAdmin(argv=None, debug=False):
        shell32 = ctypes.windll.shell32

        if argv is None and shell32.IsUserAnAdmin():
            return True

        if argv is None:
            argv = sys.argv

        if hasattr(sys, '_MEIPASS'):
            # Support pyinstaller wrapped program.
            arguments = map(unicode, argv[1:])
        else:
            arguments = map(unicode, argv)

        argumentLine = u' '.join(arguments)
        executable = unicode(sys.executable)

        if debug:
            print 'Command line: ', executable, argumentLine

        lpDirectory = None
        SHOW_NORMAL = 1
        ret = shell32.ShellExecuteW(None, u"runas", executable, argumentLine, lpDirectory, SHOW_NORMAL)
        if int(ret) <= 32:
            return False

        return None

    # Replace broken functions with those defined above.
    # (In python 2.7.11 os.path.islink() indeed failed to detect link made with mklink)
    os.symlink = symlinkWindows
    os.path.islink = islinkWindows
    os.path.samefile = samefileWindows

    setJavaPath()


if __name__ == '__main__':
    ret = runAsAdmin()
    if ret is True:
        print 'I have admin privilege.'
        raw_input('Press ENTER to exit.')
    elif ret is None:
        print 'I am elevating to admin privilege.'
        raw_input('Press ENTER to exit.')
    else:
        print 'Error(ret=%d): cannot elevate privilege.' % (ret, )
