import os
from .config import pathjoin, mkdirs, unixPath
from .error import SetupException
from .log import getLogger

_logger = getLogger(__name__)

def makeDirPath(*elements, require=False, normpath=True, create=False):
    """
    Join the tuple of elements to create a path to a directory,
    optionally checking that it exists or creating intermediate
    directories as needed.

    :param elements: a tuple of pathname elements to join
    :param require: if True, raise an error if the path doesn't exist
    :param normpath: if True, normalize the path
    :param create: if True, create the path if it doesn't exist
    :return: the joined path
    :raises: pygcam.error.SetupException
    """
    non_empty = [e for e in elements if e]
    path = pathjoin(*non_empty, normpath=normpath)

    if (create or require) and not os.path.lexists(path):
        if create:
            _logger.debug(f"Creating directory '{path}'")
            mkdirs(path)
        elif require:
            raise SetupException(f"Required path '{path}' does not exist.")

    return path


class GcamPath(object):
    """
    Simple struct to store absolute and relative paths together. Relative
    paths are generally relative to the run-time "exe" directory.
    """
    __slots__ = ['base', 'rel', 'abs']

    def __init__(self, base, rel, create=False):
        self.base = base
        self.rel = unixPath(rel)
        self.abs = makeDirPath(base, rel, create=create)

    def __str__(self):
        return f"<GcamPath base='{self.base}' rel='{self.rel}'>"

    def basename(self):
        return os.path.basename(self.abs)

    def lexists(self):
        return os.path.lexists(self.abs)

# TBD: Transitional; eventually might be able to drop this when GcamPaths are used consistently.
def gcam_path(obj, abs=True):
    """
    Return a path from either a simple pathname (str) or from a
    GcamPath object. In the GcamPath case, the ``abs`` argument
    is used; in the string case, it is ignored.

    :param obj: (str or GcamPath) the object from which to extract a path
    :param abs: (bool) whether to extract the absolute (default) or relative
        path from GcamPath objects. Ignored when ``obj`` is not a GcamPath.
    :return: (str) the extracted pathname
    """
    if isinstance(obj, GcamPath):
        return obj.abs if abs else obj.rel

    return obj  # just return the object
