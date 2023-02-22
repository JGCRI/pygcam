import glob
import os

from .config import getParam, pathjoin, unixPath
from .constants import LOCAL_XML_NAME, CONFIG_XML
from .error import SetupException
from .log import getLogger

_logger = getLogger(__name__)


def makeDirPath(*elements, require=False, normpath=True, create=False, mode=0o775):
    """
    Join the tuple of elements to create a path to a directory,
    optionally checking that it exists or creating intermediate
    directories as needed.

    :param elements: a tuple of pathname elements to join
    :param require: if True, raise an error if the path doesn't exist
    :param create: if True, create the path if it doesn't exist
    :param mode: file mode used when making directories
    :return: the joined path
    :raises: pygcam.error.SetupException
    """
    path = pathjoin(*elements, normpath=normpath)

    if (create or require) and not os.path.lexists(path):
        if create:
            _logger.debug(f"Creating directory '{path}'")
            os.makedirs(path, mode)
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


def gcam_path(obj, abs=True):
    """
    Return a path from either a simple pathname (str) or from a
    GcamPath object. In the latter case, the ``abs`` argument is
    used; in the former, it is ignored.

    :param obj: (str or GcamPath) the object from which to extract a path
    :param abs: (bool) whether to extract the absolute (default) or relative
        path from GcamPath objects. Ignored when ``obj`` is not a GcamPath.
    :return: (str) the extracted pathname
    """
    if isinstance(obj, GcamPath):
        return obj.abs if abs else obj.rel

    return obj  # just return the object


# TBD: incomplete
#
#   Maybe xmlSetup should be the only approach rather than supporting original setup subclasses.
#   this way we can assume scenario definition exists in xml format and create an API to get the
#   information about any scenario definition from xmlSetup.py.
#
#   The question is whether command-line override capability is required, or if all should be in XML.
#   Need to think through alternative use cases.
#
#   Should be no need to pass baseline since this can be inferred from scenario and scenarioGroup.
#   also can tell if it's a baseline; if not, find and cache ref to baseline
#
class GcamContext(object):
    def __init__(self, baseline, scenario, scenarioGroup='', projectName=None,
                 xmlSourceDir=None, xmlGroupSubdir='', sandboxRoot=None,
                 sandboxGroupSubdir='', createDirs=True):

        self.group = scenarioGroup
        self.scenario = scenario or baseline    # if no scenario stated, assume baseline
        self.baseline = baseline
        self.isBaseline = (scenario == baseline)
        self.baselineContext = None if self.isBaseline else self.fromXmlSetup(scenarioGroup, baseline)      # TBD
        self.projectName = projectName or getParam('GCAM.ProjectName')
        self.parent = None

        # self.xmlOutputRoot = xmlOutputRoot # TBD: default was self.dyn_xml_abs a defunct file
        # self.xmlOutputDir  = None # TBD: what is this used for? Apparently only used for generated xml, e.g., policies in constraints.py
        #self.scenarioSubdir = scenarioSubdir or scenario   # TBD: Is scenario subdir ever used?

        self.xmlSourceDir  = xmlSourceDir or getParam('GCAM.XmlSrcDir')
        self.xmlGroupSubdir = xmlGroupSubdir or scenarioGroup

        self.refWorkspace = getParam("GCAM.RefWorkspace")
        self.refExeDir = pathjoin(self.refWorkspace, "exe")

        self.sandboxRoot = sandboxRoot or getParam('GCAM.SandboxRoot')
        self.sandboxRefWorkspace = getParam('GCAM.SandboxRefWorkspace')
        self.sandboxGroupSubdir = sandboxGroupSubdir or scenarioGroup
        self.sandboxExeDir = makeDirPath(self.sandboxRoot, self.projectName, self.xmlGroupSubdir, scenario, 'exe', create=createDirs)
        self.sandboxExePath = pathjoin(self.sandboxExeDir, getParam('GCAM.Executable'))

#        self.scenarioXmlOutputDir = makeDirPath(self.xmlOutputDir, self.xmlGroupSubdir, scenario, create=createDirs)
        self.scenarioXmlSrcDir    = makeDirPath(self.xmlSourceDir, self.xmlGroupSubdir, scenario, create=createDirs)

        # directories accessed from configuration XML files (so we store relative-to-exe and absolute paths
        self.gcam_xml  = self.gcam_path('..', 'input', getParam('GCAM.DataDir'), 'xml')
        self.local_xml = self.gcam_path("..", LOCAL_XML_NAME, create=createDirs)

        # TBD: this produces '.../sandboxes/gcam_mcs/group1/policy/local-xml/group1/policy' with redundant dirs
        self.scenario_dir = self.gcam_path(self.local_xml.rel, self.xmlGroupSubdir, scenario, create=createDirs)

        # TBD: This produces, e.g., '/Users/rjp/ws/group1/policy/local-xml/group1/policy/config.xml'. Simplify dir structure.
        # self.scenarioConfigPath = pathjoin(self.scenario_dir.abs, CONFIG_XML)
        # TBD: Maybe store in exe dir, i.e., '.../ws/group1/policy/exe/config.xml' rather than storing in sandbox_dir/Workspace?
        self.scenarioConfigPath = pathjoin(self.sandboxExeDir, CONFIG_XML)

    # TBD: lookup the group and scenario, grab all data and return GcamContext(...)
    @classmethod
    def fromXmlSetup(cls, scenarioGroup, scenario):
        pass

    def gcam_path(self, *rel_path_elements, create=False):
        """
        Create a GcamPath instance by joining ``rel_path_elements`` into a relative path.

        :param rel_path_elements: (tuple of str) path elements
        :param create: (bool) if True, create the directory if it doesn't already exist.
        :return: a DirectoryPath instance
        """
        rel_path = pathjoin(*rel_path_elements)
        return GcamPath(self.sandboxExeDir, rel_path, create=create)

    def scenarioXmlSourceFiles(self):
        files = glob.glob(self.scenarioXmlSrcDir + '/*.xml')
        return files

    def cfgPath(self):
        """
        Compute the name of the GCAM config file for the current scenario.

        :return: (str) the pathname to the XML configuration file.
        """
        return self.scenarioConfigPath
