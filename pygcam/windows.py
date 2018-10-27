'''
.. Stuff specific to MS Windows
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
import os
import platform
from errno import EEXIST
from .config import getParamAsBoolean, unixPath

IsWindows = platform.system() == 'Windows'

if IsWindows:
    # print("Loading Windows support functions...")

    import ctypes
    import win32file
    from pygcam.error import PygcamException

    # From http://stackoverflow.com/questions/8231719/how-to-check-whether-a-file-is-open-and-the-open-status-in-python
    _sopen = ctypes.cdll.msvcrt._sopen
    _close = ctypes.cdll.msvcrt._close
    _SH_DENYRW = 0x10

    def is_open(filename):
        if not os.access(filename, os.F_OK):
            return False  # file doesn't exist
        h = _sopen(filename, 0, _SH_DENYRW, 0)
        if h == 3:
            _close(h)
            return False  # file is not opened by anyone else
        return True  # file is already open

    # Adapted from http://stackoverflow.com/questions/1447575/symlinks-on-windows
    # Win32file is missing this attribute.
    # FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
    #
    # REPARSE_FOLDER = (win32file.FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)
    #
    # def islinkWindows(path):
    #     """ Windows islink implementation. """
    #     return win32file.GetFileAttributesW(unicode(path)) & REPARSE_FOLDER == REPARSE_FOLDER

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

    def makeParents(path):
        path = unixPath(path, abspath=True)
        try:
            os.makedirs(os.path.dirname(path), 0o770)
        except OSError as e:
            if e.errno != EEXIST:
                raise

    def samefileWindows(filename1, filename2):
        # If either of the files does not exist, create it and close
        # it to use get_read_handle(), then remove the files we created.
        # Yes, there's a race condition here, and this has the side-effect
        # of possibly creating directories that aren't deleted, but
        # Windows is lame, so we do what we can.
        f1 = f2 = None
        hFile1 = hFile2 = None
        try:

            if not os.path.lexists(filename1):
                makeParents(filename1)
                f1 = open(filename1, 'w')
                f1.close()

            if not os.path.lexists(filename2):
                makeParents(filename2)
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
            from pygcam.log import getLogger
            _logger = getLogger(__name__)

            if getParamAsBoolean('GCAM.SymlinkWarning'):
                _logger.error('''
  ============================================================================================================
  WARNING: The current user does not have permission to create symbolic links, forcing pygcam to copy rather
  than symlink files. This uses much more file space than using symlinks, but it works.  To use pygcam more
  efficiently, ask your System Administrator to give you permission to Create Symbol Links (using gpedit.msc)

  See http://superuser.com/questions/104845/permission-to-make-symbolic-links-in-windows-7 for more info.

  Set "GCAM.SymlinkWarning = False" in ~/.pygcam.cfg to suppress this message.
  ============================================================================================================
  ''')
            raise PygcamException("Failed to create symlink '%s' to '%s': %s" % (dst, src, e))

    # The following taken from
    # http://stackoverflow.com/questions/27972776/having-trouble-implementing-a-readlink-function
    #from ctypes import *
    from ctypes.wintypes import DWORD, LPCWSTR, LPVOID, HANDLE, BOOL, USHORT, ULONG, WCHAR
    kernel32 = ctypes.WinDLL('kernel32')
    LPDWORD = ctypes.POINTER(DWORD)
    UCHAR = ctypes.c_ubyte

    GetFileAttributesW = kernel32.GetFileAttributesW
    GetFileAttributesW.restype = DWORD
    GetFileAttributesW.argtypes = (LPCWSTR,) #lpFileName In

    INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
    FILE_ATTRIBUTE_REPARSE_POINT = 0x00400

    CreateFileW = kernel32.CreateFileW
    CreateFileW.restype = HANDLE
    CreateFileW.argtypes = (LPCWSTR, #lpFileName In
                            DWORD,   #dwDesiredAccess In
                            DWORD,   #dwShareMode In
                            LPVOID,  #lpSecurityAttributes In_opt
                            DWORD,   #dwCreationDisposition In
                            DWORD,   #dwFlagsAndAttributes In
                            HANDLE)  #hTemplateFile In_opt

    CloseHandle = kernel32.CloseHandle
    CloseHandle.restype = BOOL
    CloseHandle.argtypes = (HANDLE,) #hObject In

    INVALID_HANDLE_VALUE = HANDLE(-1).value
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000

    DeviceIoControl = kernel32.DeviceIoControl
    DeviceIoControl.restype = BOOL
    DeviceIoControl.argtypes = (HANDLE,  #hDevice In
                                DWORD,   #dwIoControlCode In
                                LPVOID,  #lpInBuffer In_opt
                                DWORD,   #nInBufferSize In
                                LPVOID,  #lpOutBuffer Out_opt
                                DWORD,   #nOutBufferSize In
                                LPDWORD, #lpBytesReturned Out_opt
                                LPVOID)  #lpOverlapped Inout_opt

    FSCTL_GET_REPARSE_POINT = 0x000900A8
    IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003
    IO_REPARSE_TAG_SYMLINK = 0xA000000C
    MAXIMUM_REPARSE_DATA_BUFFER_SIZE = 0x4000

    class GENERIC_REPARSE_BUFFER(ctypes.Structure):
        _fields_ = (('DataBuffer', UCHAR * 1),)

    class SYMBOLIC_LINK_REPARSE_BUFFER(ctypes.Structure):
        _fields_ = (('SubstituteNameOffset', USHORT),
                    ('SubstituteNameLength', USHORT),
                    ('PrintNameOffset', USHORT),
                    ('PrintNameLength', USHORT),
                    ('Flags', ULONG),
                    ('PathBuffer', WCHAR * 1))
        @property
        def PrintName(self):
            arrayt = WCHAR * (self.PrintNameLength // 2)
            offset = type(self).PathBuffer.offset + self.PrintNameOffset
            return arrayt.from_address(ctypes.addressof(self) + offset).value


    class MOUNT_POINT_REPARSE_BUFFER(ctypes.Structure):
        _fields_ = (('SubstituteNameOffset', USHORT),
                    ('SubstituteNameLength', USHORT),
                    ('PrintNameOffset', USHORT),
                    ('PrintNameLength', USHORT),
                    ('PathBuffer', WCHAR * 1))
        @property
        def PrintName(self):
            arrayt = WCHAR * (self.PrintNameLength // 2)
            offset = type(self).PathBuffer.offset + self.PrintNameOffset
            return arrayt.from_address(ctypes.addressof(self) + offset).value


    class REPARSE_DATA_BUFFER(ctypes.Structure):
        class REPARSE_BUFFER(ctypes.Union):
            _fields_ = (('SymbolicLinkReparseBuffer',
                            SYMBOLIC_LINK_REPARSE_BUFFER),
                        ('MountPointReparseBuffer',
                            MOUNT_POINT_REPARSE_BUFFER),
                        ('GenericReparseBuffer',
                            GENERIC_REPARSE_BUFFER))
        _fields_ = (('ReparseTag', ULONG),
                    ('ReparseDataLength', USHORT),
                    ('Reserved', USHORT),
                    ('ReparseBuffer', REPARSE_BUFFER))
        _anonymous_ = ('ReparseBuffer',)

    REPARSE_FOLDER = (win32file.FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT)

    # def islinkWindows(path):
    #     """ Windows islink implementation. """
    #     import six
    #
    #     if not os.path.lexists(path):
    #         return False
    #
    #     return win32file.GetFileAttributesW(six.u(path)) & REPARSE_FOLDER == REPARSE_FOLDER

    def islinkWindows2(path):
        if not os.path.lexists(path):
            return False

        result = GetFileAttributesW(path)
        if result == INVALID_FILE_ATTRIBUTES:
            raise PygcamException("Can't get file attributes for '%s': %s'" % (path, ctypes.WinError()))

        return bool(result & FILE_ATTRIBUTE_REPARSE_POINT)

    def readlinkWindows(path):
        reparse_point_handle = CreateFileW(path,
                                           0,
                                           0,
                                           None,
                                           OPEN_EXISTING,
                                           FILE_FLAG_OPEN_REPARSE_POINT |
                                           FILE_FLAG_BACKUP_SEMANTICS,
                                           None)
        if reparse_point_handle == INVALID_HANDLE_VALUE:
            from pygcam.log import getLogger
            _logger = getLogger(__name__)
            _logger.info("Can't readlink: %s", path)
            raise ctypes.WinError()

        target_buffer = ctypes.c_buffer(MAXIMUM_REPARSE_DATA_BUFFER_SIZE)
        n_bytes_returned = DWORD()
        io_result = DeviceIoControl(reparse_point_handle,
                                    FSCTL_GET_REPARSE_POINT,
                                    None, 0,
                                    target_buffer, len(target_buffer),
                                    ctypes.byref(n_bytes_returned),
                                    None)
        CloseHandle(reparse_point_handle)
        if not io_result:
            raise ctypes.WinError()

        rdb = REPARSE_DATA_BUFFER.from_buffer(target_buffer)
        if rdb.ReparseTag == IO_REPARSE_TAG_SYMLINK:
            return rdb.SymbolicLinkReparseBuffer.PrintName
        elif rdb.ReparseTag == IO_REPARSE_TAG_MOUNT_POINT:
            return rdb.MountPointReparseBuffer.PrintName

        raise ValueError("not a link")

    # Replace broken functions with those defined above.
    # (In python 2.7.11 os.path.islink() indeed failed to detect link made with mklink)
    os.symlink = symlinkWindows
    os.readlink = readlinkWindows
    os.path.islink = islinkWindows2
    os.path.samefile = samefileWindows

def removeSymlink(path):
    """
    On Windows, symlinks to directories  must be removed with os.rmdir(),
    while symlinks to files must be removed with os.remove()
    """
    if not os.path.lexists(path):
        return

    if not os.path.islink(path):
        raise PygcamException("removeSymlink: path '%s' is not a symlink" % path)

    if IsWindows and os.path.isdir(path):
        os.rmdir(path)
    else:
        os.remove(path)

