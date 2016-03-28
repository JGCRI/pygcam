'''
  .. Stuff specific to MS Windows
'''
import os
import platform

IsWindows = platform.system() == 'Windows'

if IsWindows:
    # print "Loading Windows support functions..."

    import ctypes
    import win32file
    from .common import mkdirs
    from .error import PygcamException
    from .log import getLogger

    _logger = getLogger(__name__)

    # Adapted from http://stackoverflow.com/questions/1447575/symlinks-on-windows
    # Win32file is missing this attribute.
    FILE_ATTRIBUTE_REPARSE_POINT = 0x0400

    REPARSE_FOLDER = (win32file.FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)

    def islinkWindows(path):
        """ Windows islink implementation. """
        return win32file.GetFileAttributesW(unicode(path)) & REPARSE_FOLDER == REPARSE_FOLDER

    # From http://tomjbward.co.uk/detect-symlink-using-python-2-x-on-windows/
    # def islinkWindows2(path):
    #     return bool(os.path.isdir(path) and \
    #         (win32file.GetFileAttributesW(unicode(path)) & FILE_ATTRIBUTE_REPARSE_POINT))


    # Adapted from http://timgolden.me.uk/python/win32_how_do_i/see_if_two_files_are_the_same_file.html
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
        # Yes, there's a race condition here, and this has the side-effect
        # of possibly creating directories that aren't deleted, but
        # Windows is lame, so we do what we can.
        try:
            f1 = f2 = None
            hFile1 = hFile2 = None

            if not os.path.lexists(filename1):
                mkdirs(os.path.dirname(os.path.abspath(filename1)))
                f1 = open(filename1, 'w')
                f1.close()

            if not os.path.lexists(filename2):
                mkdirs(os.path.dirname(os.path.abspath(filename2)))
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
        src = src.replace('/', '\\')
        dst = dst.replace('/', '\\')

        if samefileWindows(src, dst):
            raise PygcamException("Attempted to create symlink loop from '%s' to '%s' (same file)" % (dst, src))

        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte

        # links to files and dir differ in Windows
        flags = 1 if os.path.isdir(src) else 0

        try:
            if csl(dst, src, flags) == 0:
                raise ctypes.WinError()
        except Exception as e:
            _logger.error('''
  ============================================================================================================
  To use pygcam either (i) ask Administrator to give you permission to Create Symbol Links (using gpedit.msc)
  or (ii) edit your ~/.pygcam.cfg file to include the line: "GCAM.CopyAllFiles = True" (without the quotes),
  which tells pygcam to copy files rather than attempting to use symbolic links. This uses much more file
  space than using symlinks, but it works.
  See http://superuser.com/questions/104845/permission-to-make-symbolic-links-in-windows-7 for more info.
  ============================================================================================================
  ''')
            raise PygcamException("Failed to create symlink '%s' to '%s': %s" % (dst, src, e))

    # Replace broken functions with those defined above.
    # (In python 2.7.11 os.path.islink() indeed failed to detect link made with mklink)
    os.symlink = symlinkWindows
    os.path.islink = islinkWindows
    os.path.samefile = samefileWindows


def setJavaPath(exeDir):
    '''
    Update the PATH to be able to find the Java dlls.
    Modeled on run-gcam.bat in the GCAM distribution.
    '''
    if not IsWindows:
        return

    javaHome = os.environ.get('JAVA_HOME', None)
    # Attempt to use WriteLocalBaseXDB which will print the java.home property of the Java
    # Runtime used to run it.  Note if the runtime is not 64-bit it will only print an error.
    from subprocess import check_output

    if not javaHome:
        curdir = os.getcwd()
        os.chdir(exeDir)
        # For some reason, this doesn't work with a path to WriteLocalBaseXDB
        # so we chdir to the directory and run java there.
        output = check_output('java WriteLocalBaseXDB', shell=True)
        javaHome = output and output.strip()
        os.chdir(curdir)

    if javaHome and os.path.isdir(javaHome):
        path = os.environ['PATH']
        # SET PATH=%PATH%;%JAVA_HOME%\bin;%JAVA_HOME%\bin\server"
        os.environ['PATH'] = path + ';' + javaHome + r'\bin;' + javaHome + r'\bin\server'
        _logger.debug("Setting PATH to %s", os.environ['PATH'])

def removeSymlink(path):
    """
    On Windows, symlinks to directories  must be removed with os.rmdir(),
    while symlinks to files must be removed with os.remove()
    """
    if not os.path.islink(path):
        raise PygcamException("removeSymlink: path '%s' is not a symlink" % path)

    if IsWindows and os.path.isdir(path):
        os.rmdir(path)
    else:
        os.remove(path)

    # Adapted from
    # http://stackoverflow.com/questions/19672352/how-to-run-python-script-with-elevated-privilege-on-windows
    # def runAsAdmin(argv=None, debug=False):
    #     shell32 = ctypes.windll.shell32
    #
    #     if argv is None and shell32.IsUserAnAdmin():
    #         return True
    #
    #     if argv is None:
    #         argv = sys.argv
    #
    #     if hasattr(sys, '_MEIPASS'):
    #         # Support pyinstaller wrapped program.
    #         arguments = map(unicode, argv[1:])
    #     else:
    #         arguments = map(unicode, argv)
    #
    #     argumentLine = u' '.join(arguments)
    #     executable = unicode(sys.executable)
    #
    #     if debug:
    #         print 'Command line: ', executable, argumentLine
    #
    #     lpDirectory = None
    #     SHOW_NORMAL = 1
    #     ret = shell32.ShellExecuteW(None, u"runas", executable, argumentLine, lpDirectory, SHOW_NORMAL)
    #     if int(ret) <= 32:
    #         return False
    #
    #     return None
