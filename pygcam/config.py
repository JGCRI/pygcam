'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import io
import platform
from ConfigParser import SafeConfigParser
from .error import ConfigFileError, PygcamException, CommandlineError
from .subcommand import SubcommandABC

DEFAULT_SECTION = 'DEFAULT'
USR_CONFIG_FILE = '.pygcam.cfg'
CONFIG_VAR_NAME = 'QUEUE_GCAM_CONFIG_FILE'
WORKSPACE_VAR_NAME   = 'QUEUE_GCAM_WORKSPACE'
NO_RUN_GCAM_VAR_NAME = 'QUEUE_GCAM_NO_RUN_GCAM'


_SystemDefaults = \
"""#
# This file defines variables read by the pygcam package. It allows
# you to customize many aspects of pygcam, such as file locations,
# and arguments to various commands. See the documentation for the
# config module for detailed explanations.
#
# The default configuration values are provided below. To modify a
# value, remove the '#' comment character at the start of the line
# and set the value as desired.
#
# To set a project-specific value to override the defaults for one
# project, create a new section by indicating the project name in
# square brackets. For example for the project GCAM, you would add
# [GCAM]. All settings after this until the next section declaration
# (or end of file) taken as values for "GCAM". The script gcamtool.py
# allows you to identify the project you are operating on so that
# the corresponding values are read from the config file.
#
[DEFAULT]
# This project is used if '-p' flag not given to gcamtool
GCAM.DefaultProject =

# Where to find plug-ins. Internal plugin directory is added
# automatically. Use this to add custom plug-ins outside the pygcam
# source tree. The value is a semicolon-delimited (on Windows) or
# colon-delimited (on Unix) string of directories to search for files
# matching the pattern '*_plugin.py' NOTE: This must be set in the
# DEFAULT section.
GCAM.PluginPath =

# Sets the folder holding the symlink "current" which refers
# to a folder holding Main_User_Workspace and ModelInterface.
# (This is one way of setting up the code, but not required.)
GCAM.Root = %(Home)s/GCAM

# Refers to the GCAM folder holding the version of the model
# you want to use. It is convenient to make this a symbolic link.
GCAM.Current = %(GCAM.Root)s/current

# The default location in which to find or create GCAM runtime
# sandboxes
GCAM.SandboxRoot = %(GCAM.Root)s/ws

# The location of the Main_User_Workspace to use. This can refer
# to any folder; GCAM.Current is just an optional convention.
GCAM.RefWorkspace = %(GCAM.Current)s/Main_User_Workspace

# The reference config file to use as a starting point for "setup"
GCAM.RefConfigFile = %(GCAM.RefWorkspace)s/exe/configuration_ref.xml

GCAM.RefQueryDir = %(GCAM.RefWorkspace)s/output/queries

# The location of the ModelInterface to use.
GCAM.ModelInterface = %(GCAM.Current)s/ModelInterface

GCAM.ModelInterfaceLogFile = %(GCAM.TempDir)s/mi.log

# QueryPath is string with one or more colon-delimited elements that
# identify directories or XML files in which to find batch query
# definitions.
GCAM.QueryDir    = %(GCAM.RefQueryDir)s
GCAM.QueryPath   = %(GCAM.QueryDir)s/Main_Queries.xml

# The location of GCAM source code (for the purpose of reading
# the .csv file that defines the current regional aggregation.
GCAM.SourceWorkspace =

# Root directory for where the user keeps project folders
GCAM.ProjectRoot    = %(Home)s/projects

# The name of the XML Starlet program. Use full path if it's not
# found on your usual PATH.
GCAM.XmlStarlet     = xml

# If using the XML "setup" system, this is the root folder for
# setup source files
GCAM.XmlSrc         = %(GCAM.ProjectRoot)s/xmlsrc

# The folders for setup-generated XML files.
GCAM.LocalXml       = %(GCAM.ProjectRoot)s/local-xml
GCAM.DynXml         = %(GCAM.ProjectRoot)s/dyn-xml

# The default input file for the runProj sub-command
GCAM.ProjectXmlFile = %(GCAM.ProjectRoot)s/etc/project.xml

# Whether GCAM should generate a debug file (no value => no change)
GCAM.WriteDebugFile     =

# Whether GCAM should generate a price file
GCAM.WritePrices        =

# Whether GCAM should generate the large XML file with the combined data
# from all input files.
GCAM.WriteXmlOutputFile =

# Whether GCAM should generate outFile.csv
GCAM.WriteOutputCsv     =

# Path to an XML file describing land protection scenarios
GCAM.LandProtectionXmlFile =

# Default location in which to look for scenario directories
GCAM.ScenariosDir =

# The location of the libraries needed by ModelInterface
GCAM.JavaLibPath = %(GCAM.RefWorkspace)s/libs/basex

# Arguments to java to ensure that ModelInterface has enough
# heap space.
GCAM.JavaArgs = -Xms512m -Xmx2g

# The name of the database file (or directory, for BaseX)
GCAM.DbFile	  = database_basexdb

# Columns to drop when processing results of XML batch queries
GCAM.ColumnsToDrop = scenario,Notes,Date

# Change this if desired to increase or decrease diagnostic messages.
# A default value can be set here, and a project-specific value can
# be set in the project's config file section.
# Possible values (from most to least verbose) are:
# DEBUG, INFO, WARNING, ERROR, CRITICAL
GCAM.LogLevel   = WARNING

# Save log messages in the indicated file
GCAM.LogFile    =

# Show log messages on the console (terminal)
GCAM.LogConsole = True

# The name of the queue used for submitting batch jobs on a cluster.
GCAM.DefaultQueue = standard

GCAM.QsubCommand = qsub -q {queueName} -N {jobName} -l walltime={walltime} \
  -d {exeDir} -e {logFile} -m n -j oe -l pvmem=6GB -v %(GCAM.OtherBatchArgs)s \
  QUEUE_GCAM_CONFIG_FILE='{configs}',QUEUE_GCAM_WORKSPACE='{workspace}',QUEUE_GCAM_NO_RUN_GCAM={noRunGCAM}

# --signal=USR1@15 => send SIGUSR1 15s before walltime expires
GCAM.SlurmCommand = sbatch -p {queueName} --nodes=1 -J {jobName} -t {walltime} \
  -D {exeDir} --get-user-env=L -s --mem=6000 --tmp=6000 %(GCAM.OtherBatchArgs)s \
  --export=QUEUE_GCAM_CONFIG_FILE='{configs}',QUEUE_GCAM_WORKSPACE='{workspace}',QUEUE_GCAM_NO_RUN_GCAM={noRunGCAM}

# Arbitrary arguments to add to the selected batch command
GCAM.OtherBatchArgs =

GCAM.BatchCommand = %(GCAM.SlurmCommand)s

# Set this to a command to run when the -l flag is passed to gcamtool's
# "run" sub-command. The same options are available for substitution as
# for the GCAM.BatchCommand.
GCAM.LocalCommand =

# Arguments to qsub's "-l" flag that define required resources
GCAM.QsubResources = pvmem=6GB

# Environment variables to pass to qsub. (Not needed by most users.)
GCAM.QsubEnviroVars =

# For qsub, the default number of minutes to allocate per task.
GCAM.Minutes = 20

# Whether to use the "virtual buffer", allowing ModelInterface to
# run without generating pop-up windows on Linux.
GCAM.UseVirtualBuffer = yes

# A script to run by queueGCAM after GCAM completes. The script is
# called with 3 arguments: workspace directory, XML configuration
# file, and scenario name.
GCAM.PostProcessor =

# A file that maps GCAM regions to rename them or to aggregate
# them. Each line consists of a GCAM region name, some number of
# tabs, and the name to map the region to.
GCAM.RegionMapFile =

# Where to create temporary files
GCAM.TempDir = /tmp

# For Windows users without permission to create symlinks
GCAM.CopyAllFiles = False

# For debugging purposes: gcamtool.py can show a stack trace on error
GCAM.ShowStackTrace = False
"""

def _getCommentedDefaults():
    '''
    Returns a copy of the _SystemDefault string with all variable
    assignments commented out. This allows the user to see what's
    possible, but also demonstrates that these are the defaults.
    '''
    import re

    def comment(match):
        '''Comment out any line starting with GCAM.* ='''
        return '# ' + match.group()

    p = re.compile('^(GCAM\.\S+\s*=)', re.MULTILINE)
    result = p.sub(comment, _SystemDefaults)

    # Add dynamically generated vars (as "raw" values so the obey user's settings of referenced variables)
    dynamic  = "\n# User's home directory\n# Home = %s\n\n" % getParam('Home', raw=True)
    dynamic += "# Name of gcam executable relative to 'exe' dir\n# GCAM.Executable = %s\n\n" % getParam('GCAM.Executable', raw=True)
    dynamic += "# Location of ModelInterface jar file\n# GCAM.JarFile = %s\n\n" % getParam('GCAM.JarFile', raw=True)
    dynamic += "# Whether to use a virtual display when running ModelInterface\n# GCAM.UseVirtualBuffer = %s\n\n" % getParam('GCAM.UseVirtualBuffer', raw=True)

    return result + dynamic

_ConfigParser = None

# This is set in readConfigFiles
_ProjectSection = None

def getSection():
    return _ProjectSection

def configLoaded():
    return bool(_ConfigParser)

def getConfig(section=DEFAULT_SECTION, reload=False):
    """
    Return the configuration object. If one has been created already via
    `readConfigFiles`, it is returned, unless force == True; otherwise
    a new one is created and the configuration files are read.

    :param section: (str) the name of a section to read from
    :param reload: (bool) if True, re-read the config section
    :return: a `SafeConfigParser` instance.
    """
    if not reload and _ConfigParser:
        return _ConfigParser

    return readConfigFiles(section=section)

def readConfigFiles(section):
    """
    Read the pygcam configuration file, ``~/.pygcam.cfg``. "Sensible" default values are
    established first, which overwritten by values found in the user's configuration
    file.

    :param section: (str) the name of the config file section to read from.
    :return: a populated SafeConfigParser instance
    """
    global _ConfigParser, _ProjectSection

    _ProjectSection = section
    platformName = platform.system()

    # HOME exists on all Unix-like systems; for Windows it's HOMEPATH
    if platformName == 'Windows':
        home = os.path.realpath(os.getenv('HOMEPATH'))  # adds home drive
        home = home.replace('\\', '/')                  # avoids '\' quoting issues
    else:
        home = os.getenv('HOME')

    if platformName == 'Darwin':
        jarFile = '%(GCAM.ModelInterface)s/ModelInterface.app/Contents/Resources/Java/ModelInterface.jar'
        exeFile = 'Release/objects'
        useXvfb = 'False'
    elif platformName == 'Linux':
        jarFile = '%(GCAM.ModelInterface)s/ModelInterface.jar'
        exeFile = './gcam.exe'
        useXvfb = 'True'
    elif platformName == 'Windows':
        jarFile = '%(GCAM.ModelInterface)s/ModelInterface.jar'
        exeFile = 'Objects-Main.exe'
        useXvfb = 'False'
    else:
        # unknown what this might be, but just in case
        jarFile = '%(GCAM.ModelInterface)s/ModelInterface.jar'
        exeFile = 'gcam.exe'
        useXvfb = 'False'

    # Initialize config parser with default values
    _ConfigParser = SafeConfigParser()

    _ConfigParser.optionxform = str     # don't force all names to lower-case

    _ConfigParser.readfp(io.BytesIO(_SystemDefaults))
    _ConfigParser.set(DEFAULT_SECTION, 'Home', home)
    _ConfigParser.set(DEFAULT_SECTION, 'GCAM.Executable', exeFile)
    _ConfigParser.set(DEFAULT_SECTION, 'GCAM.JarFile', jarFile)
    _ConfigParser.set(DEFAULT_SECTION, 'GCAM.UseVirtualBuffer', useXvfb)

    # Customizations are stored in ~/.pygcam.cfg
    usrConfigPath = os.path.join(home, USR_CONFIG_FILE)

    # os.path.exists doesn't always work on Windows, so just try opening it.
    try:
        fp = open(usrConfigPath)
        _ConfigParser.readfp(fp)
        fp.close()
    except IOError as e:
        # create a file with the system defaults if no file exists
        with open(usrConfigPath, 'w') as fp:
            commented = _getCommentedDefaults()
            fp.write(commented)

    return _ConfigParser

def getConfigDict(section, raw=False):
    """
    Return all variables defined in `section` as a dictionary.

    :param section: (str) the name of a section in the config file
    :return: (dict) all variables defined in the section (which includes
       those defined in DEFAULT.)
    """
    if not _ConfigParser.has_section(section):
        section = DEFAULT_SECTION

    d = {key : value for key, value in _ConfigParser.items(section, raw=raw)}
    return d

def getParam(name, section=None, raw=False):
    """
    Get the value of the configuration parameter `name`. Calls
    :py:func:`getConfig` if needed.

    :param name: (str) the name of a configuration parameters. Note
       that variable names are case-insensitive.
    :param section: (str) the name of the section to read from, which
      defaults to the value used in the first call to ``getConfig``,
      ``readConfigFiles``, or any of the ``getParam`` variants.
    :return: (str) the value of the variable
    """
    section = section or _ProjectSection

    if not section:
        raise PygcamException('getParam was called without setting "section"')

    if not _ConfigParser:
        getConfig(section)

    return _ConfigParser.get(section, name, raw=raw)

def getParamAsBoolean(name, section=None):
    """
    Get the value of the configuration parameter `name`, coerced
    into a boolean value, where any (case-insensitive) value in the
    set ``{'true','yes','on','1'}`` are converted to ``True``, and
    any value in the set ``{'false','no','off','0'}`` is converted to
    ``False``. Any other value raises an exception.
    Calls :py:func:`getConfig` if needed.

    :param name: (str) the name of a configuration parameters.
    :param section: (str) the name of the section to read from, which
      defaults to the value used in the first call to ``getConfig``,
      ``readConfigFiles``, or any of the ``getParam`` variants.
    :return: (bool) the value of the variable
    :raises: :py:exc:`pygcam.error.ConfigFileError`
    """
    true = ('true', 'yes', 'on', '1')
    false = ('false', 'no', 'off', '0')

    value = getParam(name, section=section)
    value = str(value).lower()

    if value in true:
        return True

    if value in false:
        return False

    raise ConfigFileError("The value of variable '%s' could not converted to boolean." % name)


def getParamAsInt(name, section=None):
    """
    Get the value of the configuration parameter `name`, coerced
    to an integer. Calls :py:func:`getConfig` if needed.

    :param name: (str) the name of a configuration parameters.
    :param section: (str) the name of the section to read from, which
      defaults to the value used in the first call to ``getConfig``,
      ``readConfigFiles``, or any of the ``getParam`` variants.
    :return: (int) the value of the variable
    """
    value = getParam(name, section=section)
    return int(value)

def getParamAsFloat(name, section=None):
    """
    Get the value of the configuration parameter `name` as a
    float. Calls :py:func:`getConfig` if needed.

    :param name: (str) the name of a configuration parameters.
    :param section: (str) the name of the section to read from, which
      defaults to the value used in the first call to ``getConfig``,
      ``readConfigFiles``, or any of the ``getParam`` variants.
    :return: (float) the value of the variable
    """
    value = getParam(name, section=section)
    return float(value)


class ConfigCommand(SubcommandABC):
    VERSION = '0.1'

    def __init__(self, subparsers):
        kwargs = {'help' : '''List the contents of the ~/.pygcam configuration file or
                              the value of a single parameter.'''}

        super(ConfigCommand, self).__init__('config', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('-d', '--useDefault', action='store_true',
                            help='''Indicates to operate on the DEFAULT
                                    section rather than the project section.''')

        parser.add_argument('-v', '--variable',
                            help='''Show the value of a single configuration variable.
                            The argument must be a variable name.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + self.VERSION)

        return parser

    def run(self, args, tool):
        section = 'DEFAULT' if args.useDefault else args.configSection

        if args.variable:
            value = getParam(args.variable, section=section)
            if value is not None:
                print value
        else:
            if section == 'DEFAULT' or _ConfigParser.has_section(section):
                print "[%s]" % section
                for var, value in sorted(_ConfigParser.items(section)):
                    print "%22s = %s" % (var, value)
            else:
                raise CommandlineError("Unknown configuration file section '%s'" % section)


PluginClass = ConfigCommand
