import os
import shutil
from contextlib import contextmanager

from .config import getParamAsBoolean, pathjoin, getParam, mkdirs
from .error import PygcamException
from .log import getLogger

_logger = getLogger(__name__)

@contextmanager
def pushd(directory):
    """
    Context manager that changes to the given directory and then
    returns to the original directory. Usage is ``with pushd('/foo/bar'): ...``

    :param directory: (str) a directory to chdir to temporarily
    :return: none
    """
    owd = os.getcwd()
    try:
        os.chdir(directory)
        yield directory
    finally:
        os.chdir(owd)


def deleteFile(filename):
    """
    Delete the given `filename`, but ignore errors, like "rm -f"

    :param filename: (str) the file to remove
    :return: none
    """
    try:
        os.remove(filename)
    except:
        pass    # ignore errors, like "rm -f"


def symlink(src, dst):
    if os.path.lexists(dst) and os.path.islink(dst):
        os.remove(dst)

    _logger.debug('ln -s %s %s', src, dst)
    try:
        os.symlink(src, dst)
    except Exception:
        _logger.warn(f"Can't symlink '{src}' to '{dst}'")
        raise


def symlinkOrCopyFile(src, dst):
    """
    Symlink a file unless GCAM.CopyAllFiles is True, in which case, copy the file.

    :param src: (str) filename of original file
    :param dst: (dst) filename of copy
    :return: none
    """
    if getParamAsBoolean('GCAM.CopyAllFiles'):
        copyFileOrTree(src, dst)
    else:
        symlink(src, dst)


def copyFileOrTree(src, dst):
    """
    Copy src to dst, where the two can both be files or directories.
    If `src` and `dst` are directories, `dst` must not exist yet.

    :param src: (str) path to a source file or directory
    :param dst: (str) path to a destination file or directory.
    :return: none
    """
    if getParamAsBoolean('GCAM.CopyAllFiles') and src[0] == '.':   # convert relative paths
        src = pathjoin(os.path.dirname(dst), src, normpath=True)

    if os.path.islink(src):
        src = os.readlink(src)

    if os.path.isdir(src):
        removeTreeSafely(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def removeTreeSafely(path, ignore_errors=True):
    if not os.path.lexists(path):
        return

    refWorkspace = os.path.realpath(getParam('GCAM.RefWorkspace'))
    thisPath = os.path.realpath(path)
    if os.path.commonprefix((refWorkspace, thisPath)) == refWorkspace:
        raise PygcamException("Refusing to delete %s, which is part of the reference workspace" % path)

    _logger.debug("shutil.rmtree('%s')", thisPath)
    shutil.rmtree(thisPath, ignore_errors=ignore_errors)


def removeFileOrTree(path, raiseError=True):
    """
    Remove a file or an entire directory tree. Handles removal of symlinks
    on Windows, as these are treated differently in that system.

    :param path: (str) the pathname of a file or directory.
    :param raiseError: (bool) if True, re-raise any error that occurs
       during the file operations, else errors are ignored.
    :return: none
    """
    from .windows import removeSymlink

    if not os.path.lexists(path):
        return

    try:
        if os.path.islink(path):
            # Windows treats links to files and dirs differently.
            # NB: if not on Windows, just calls os.remove()
            removeSymlink(path)
        else:
            if os.path.isdir(path):
                removeTreeSafely(path)
            else:
                os.remove(path)
    except Exception as e:
        if raiseError:
            raise


def systemOpenFile(path):
    """
    Ask the operating system to open a file at the given pathname.

    :param path: (str) the pathname of a file to open
    :return: none
    """
    import platform
    from .utils import shellCommand

    if platform.system() == 'Windows':
        shellCommand(['start', os.path.abspath(path)], shell=True)
    else:
        # "-g" => don't bring app to the foreground
        shellCommand(['open', '-g', path], shell=False)


def ensureExtension(filename, ext):
    """
    Force a filename to have the given extension, `ext`, adding it to
    any other extension, if present. That is, if `filename` is ``foo.bar``,
    and `ext` is ``baz``, the result will be ``foo.bar.baz``.
    If `ext` doesn't start with a ".", one is added.

    :param filename: filename
    :param ext: the desired filename extension
    :return: filename with extension `ext`
    """
    mainPart, extension = os.path.splitext(filename)
    ext = ext if ext[0] == '.' else '.' + ext

    if not extension:
        filename = mainPart + ext
    elif extension != ext:
        filename += ext

    return filename

def ensureCSV(file):
    """
    Ensure that the file has a '.csv' extension by replacing or adding
    the extension, as required.

    :param file: (str) a filename
    :return: (str) the filename with a '.csv' extension.
    """
    return ensureExtension(file, '.csv')

def saveToFile(txt, dirname='', filename=''):
    """
    Save the given text to a file in the given directory.

    :param txt: (str) the text to save
    :param dirname: (str) path to a directory
    :param filename: (str) the name of the file to create

    :return: none
    """
    if dirname:
        mkdirs(dirname)

    pathname = pathjoin(dirname, filename)

    _logger.debug("Writing %s", pathname)
    with open(pathname, 'w') as f:
        f.write(txt)

def is_abspath(pathname):
    """
    Return True if pathname is an absolute pathname, else False.
    """
    import re
    return bool(re.match(r"^([/\\])|([a-zA-Z]:)", pathname))

def get_path(pathname, defaultDir):
    """
    Return pathname if it's an absolute pathname, otherwise return
    the path composed of pathname relative to the given defaultDir.
    """
    return pathname if is_abspath(pathname) else pathjoin(defaultDir, pathname)


def copyIfMissing(src, dst, makedirs=False):
    """
    Copy file `src` to `dst`, but only if `dst` doesn't already exist.

    :param src: (str) pathname of the file to copy
    :param dst: (str) pathname of the copy to create
    :param makedirs: if True, make any missing directories
    :return: none
    """
    if not os.path.lexists(dst):
        parentDir = os.path.dirname(dst)
        if makedirs and not os.path.isdir(parentDir):
            _logger.debug("mkdir '%s'", parentDir)
            os.makedirs(parentDir, 0o755)

        _logger.info("Copy %s\n      to %s", src, dst)
        shutil.copy(src, dst)
        os.chmod(dst, 0o644)

def rename(direc, src, dest):
    old = pathjoin(direc, src)
    new = pathjoin(direc, dest)
    os.rename(old, new)


def filecopy(src, dst, removeDst=True):
    'Copy src file to dst, optionally removing dst first to avoid writing through symlinks'
    from shutil import copy2        # equivalent to "cp -p"

    _logger.debug("copyfile(%s,%s,%s)" % (src, dst, removeDst))
    if removeDst and os.path.islink(dst):
        os.remove(dst)

    copy2(src, dst)


def copyfiles(files, dstdir, removeDst=True):
    '''
    :param files: a list of files to copy
    :param dstdir: the directory to copy to
    :param removeDst: if True-like, remove destination file before copying
    :return: nothing
    '''
    mkdirs(dstdir)
    for f in files:
        filecopy(f, dstdir, removeDst=removeDst)
