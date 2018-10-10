import os
from tempfile import mkstemp, mkdtemp

from .error import PygcamException
from .config import getParam

def getTempFile(suffix='', tmpDir=None, text=True, delete=True):
    """
    Convenience function for common use pattern, which is to get
    the name of a temp file that needs to be deleted on app exit.

    :param suffix: (str) an extension to give the temporary file
    :param tmpDir: (str) the directory in which to create the file.
      (Defaults to the value of configuration file variable 'GCAM.TempDir',
      or '/tmp' if the variable is not found.
    :param text: True if this will be a text file
    :param delete: (bool) if False, don't delete the file on cleanup.
       (This is useful for debugging.)
    :return: (str) pathname of a new temporary file
    """
    obj = TempFile(suffix=suffix, text=text, tmpDir=tmpDir, delete=delete)
    return obj.path

def getTempDir(suffix='', tmpDir=None, delete=True):
    """
    Convenience function for common use pattern, which is to get the
    name of a temporary directory that needs to be deleted on app exit.

    :param suffix: (str) an extension to give the temporary file
    :param tmpDir: (str) the directory in which to create the new temporary
        directory (Defaults to the value of configuration file variable
        'GCAM.TempDir', or '/tmp' if the variable is not found.
    :param delete: (bool) if False, don't delete the file on cleanup.
       (This is useful for debugging.)
    :return: (str) pathname of a new temporary directory
    """
    obj = TempFile(suffix=suffix, tmpDir=tmpDir, delete=delete, createDir=True)
    return obj.path


class TempFile(object):
    """
    Class to create and track temporary files in one place
    so they can be deleted before an application exits.
    """
    Instances = {}

    def __init__(self, path=None, suffix='', tmpDir=None, delete=True,
                 openFile=False, text=True, createDir=False):
        """
        Construct the name of a temporary file.

        :param path: (str) a path to register for deletion. If given, all other
            args are ignored.
        :param suffix: (str) an extension to give the temporary file
        :param tmpDir: (str) the directory in which to create the (defaults to
            the value of configuration file variable 'GCAM.TempDir', or '/tmp'
            if the variable is not found.
        :param delete: (bool) whether deleteFile() should delete the file when
            called
        :param openFile: (bool) whether to leave the new file open (ignored if
            createDir is True)
        :param text: (bool) Set to False if this will not be a text file
        :param createDir: (bool) if True, a temporary directory will be created
            rather than a temporary file.
        :return: none
        """
        from .utils import mkdirs

        self.suffix = suffix
        self.delete = delete
        self.fd = None

        if path:
            # If we're called with a path, it's just to register a file for deletion.
            # We ignore all other parameters.
            self.path = path
        else:
            tmpDir = tmpDir or getParam('GCAM.TempDir') or "/tmp"
            mkdirs(tmpDir)

            if createDir:
                self.path = mkdtemp(suffix=suffix, dir=tmpDir)
            else:
                fd, tmpFile = mkstemp(suffix=suffix, dir=tmpDir, text=text)

                self.path = tmpFile
                if openFile:
                    self.fd = fd
                else:
                    # the caller is just after a pathname, so close it here
                    os.close(fd)
                    os.unlink(tmpFile)

        # save this instance by the unique path
        self.Instances[self.path] = self

    def deleteFile(self):
        """
        Remove the file for a TempFile instance if ``self.delete`` is True. In either
        case, delete the instance from the class instance dict.

        :return: none
        :raises: PygcamException if the path is not related to a TempFile instance.
        """
        from .log import getLogger
        _logger = getLogger(__name__)

        path = self.path

        try:
            if self.fd is not None:
                os.close(self.fd)
        except Exception as e:
            _logger.debug('Failed to close file descriptor for "%s": %s', path, e)

        try:
            del self.Instances[path]
        except KeyError:
            raise PygcamException('No TempFile instance with name "%s"' % path)

        deleting = 'Deleting' if self.delete else 'Not deleting'
        _logger.debug("%s TempFile file '%s'", deleting, path)

        if self.delete:
            from .utils import removeFileOrTree
            try:
                removeFileOrTree(path, raiseError=True)
            except Exception as e:
                _logger.debug('Failed to delete "%s": %s', path, e)

    @classmethod
    def deleteAll(cls):
        for obj in list(cls.Instances.values()):    # compose a list to avoid changing dict during iteration
            obj.deleteFile()

    @classmethod
    def remove(cls, filename, raiseError=True):
        """
        Remove a temporary file and delete the TempFile instance from the dict.

        :param filename: (str) the name of a temp file created by this class
        :param raiseError: (bool) if True, raise an exception if the filename is
            not a known TempFile.
        :return: none
        :raises PygcamException: if the path is not related to a TempFile instance.
        """
        try:
            obj = cls.Instances[filename]
            obj.deleteFile()
        except KeyError:
            if raiseError:
                raise PygcamException('No TempFile instance with name "%s"' % filename)

