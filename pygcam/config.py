'''
.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from __future__ import print_function
import os
import platform
from pkg_resources import resource_string
from backports import configparser
from .error import ConfigFileError, PygcamException

DEFAULT_SECTION = 'DEFAULT'
USR_CONFIG_FILE = '.pygcam.cfg'
CONFIG_VAR_NAME = 'QUEUE_GCAM_CONFIG_FILE'
WORKSPACE_VAR_NAME   = 'QUEUE_GCAM_WORKSPACE'
NO_RUN_GCAM_VAR_NAME = 'QUEUE_GCAM_NO_RUN_GCAM'

PlatformName = platform.system()

_instructions = '''#
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
# square brackets. For example for the project PROJECT0, you would
# add [PROJECT0]. All settings after this until the next section
# declaration (or end of file) taken as values for "PROJECT0". The
# "gt" script allows you to identify the project you are operating
# on so that the corresponding values are read from the config file.
#
'''

def _getCommentedDefaults(systemDefaults):
    '''
    Returns a copy of the _SystemDefault string with all variable
    assignments commented out. This allows the user to see what's
    possible, but also demonstrates that these are the defaults.
    '''
    import re

    def comment(match):
        '''Comment out any line starting with GCAM.* ='''
        return '# ' + match.group()

    result = _instructions

    p = re.compile('^(GCAM\.\S+\s*=)', re.MULTILINE)
    result += p.sub(comment, systemDefaults)

    # Add dynamically generated vars (as "raw" values so the obey user's settings of referenced variables)
    result += "\n# For up-to-date documentation of configuration variables, see the\n"
    result += "# listing at the end of https://pygcam.readthedocs.io/en/latest/config.html\n\n"
    result += "# User's home directory\n# Home = %s\n\n" % getParam('Home', raw=True)
    result += "# Name of gcam executable relative to 'exe' dir\n# GCAM.Executable = %s\n\n" % getParam('GCAM.Executable', raw=True)
    result += "# Location of ModelInterface jar file\n# GCAM.MI.JarFile = %s\n\n" % getParam('GCAM.MI.JarFile', raw=True)
    result += "# Whether to use a virtual display when running ModelInterface\n# GCAM.MI.UseVirtualBuffer = %s\n\n" % getParam('GCAM.MI.UseVirtualBuffer', raw=True)
    result += "# Editor command to invoke by 'gt config -e'\n# GCAM.TextEditor = %s\n\n" % getParam('GCAM.TextEditor', raw=True)


    if PlatformName == 'Windows':   # convert line endings from '\n' to '\r\n'
        result = result.replace(r'\n', '\r\n')

    return result

_ConfigParser = None

_ProjectSection = DEFAULT_SECTION

def getSection():
    return _ProjectSection

def setSection(section):
    """
    Set the name of the default config file section to read from.

    :param section: (str) a config file section name.
    :return: none
    """
    global _ProjectSection
    _ProjectSection = section

def configLoaded():
    return bool(_ConfigParser)

def getConfig():
    """
    Return the configuration object. If one has been created already via
    `readConfigFiles`, it is returned; otherwise a new one is created
    and the configuration files are read. Applications generally do not
    need to use this object directly since the single instance is stored
    internally and referenced by the other API functions.

    :return: a `ConfigParser` instance.
    """
    return _ConfigParser or readConfigFiles()


def _readConfigResourceFile(filename, package='pygcam', raiseError=True):
    try:
        data = resource_string(package, filename)
    except IOError:
        if raiseError:
            raise
        else:
            return None

    data = unicode(data)
    _ConfigParser.read_string(data, source=filename)
    return data

_usingMCS = None

def setUsingMCS(value):
    global _usingMCS
    _usingMCS = value

def usingMCS():
    """
    Check if the user environment is configured to use pygcam-mcs, which requires
    that the pygcammcs package is installed and that the file ~/.no_pycam_mcs is
    NOT found. This lets gcamtool know whether to load the corresponding
    built-in sub-commands.

    :return: (bool) True if user environment indicates to use pygcam-mcs.
    """
    global _usingMCS

    if _usingMCS is None:
        path = os.path.join(os.getenv('HOME'), '.no_pygcam_mcs')
        if os.path.exists(path):
            import sys
            # let user know this hidden file is active
            sys.stderr.write('Not using pygcam-mcs: found sentinel file %s\n' % path)
            setUsingMCS(False)
        else:
            try:
                import pygcammcs
                setUsingMCS(True)

            except ImportError:
                setUsingMCS(False)

    return _usingMCS

def readConfigFiles():
    """
    Read the pygcam configuration files, starting with ``pygcam/etc/system.cfg``,
    followed by ``pygcam/etc/{platform}.cfg`` if present. If the environment variable
    ``PYGCAM_SITE_CONFIG`` is defined, its value should be a config file, which is
    read next. Finally, the user's config file, ``~/.pygcam.cfg``, is read. Each
    successive file overrides values for any variable defined in an earlier file.

    :return: a populated ConfigParser instance
    """
    global _ConfigParser

    if PlatformName == 'Windows':
        # HOME exists on all Unix-like systems; for Windows it's HOMEPATH or HOMESHARE.
        # If set, we use PYGCAM_HOME to identify the folder with the config file;
        # otherwise, we use HOMESHARE if set, or HOMEPATH, in that order.
        env = os.environ
        homedir = env.get('PYGCAM_HOME') or env.get('HOMESHARE') or env.get('HOMEPATH')
        drive, path = os.path.splitdrive(homedir)
        drive = drive or env.get('HOMEDRIVE') or 'C:'
        home = os.path.realpath(drive + path)
        home = home.replace('\\', '/')            # avoids '\' quoting issues
    else:
        home = os.getenv('HOME')

    # Strict mode prevents duplicate sections, which we do not restrict
    _ConfigParser = configparser.ConfigParser(comment_prefixes=('#'), strict=False,
                                              empty_lines_in_values=False)

    # don't force keys to lower-case
    _ConfigParser.optionxform = lambda option: option

    # Initialize config parser with default values
    _ConfigParser.set(DEFAULT_SECTION, 'Home', home)
    systemDefaults = _readConfigResourceFile('etc/system.cfg')

    # Read platform-specific defaults, if defined. No error if file is missing.
    _readConfigResourceFile('etc/%s.cfg' % PlatformName, raiseError=False)

    # if user is working with pygcam.mcs, we load additional defaults. The
    # function usingMCS() imports the package as part of the test...
    if usingMCS():
        _readConfigResourceFile('etc/mcs.cfg', package='pygcammcs', raiseError=True)

    siteConfig = os.getenv('PYGCAM_SITE_CONFIG')
    if siteConfig:
        try:
            with open(siteConfig) as f:
               _ConfigParser.read_file(f)
        except Exception as e:
            print("WARNING: Failed to read site config file: %s" % e)

    # Customizations are stored in ~/.pygcam.cfg
    usrConfigPath = os.path.join(home, USR_CONFIG_FILE)

    # os.path.exists doesn't always work on Windows, so just try opening it.
    try:
        with open(usrConfigPath) as f:
           _ConfigParser.read_file(f)

    except IOError as e:
        # TBD: rather than this, write a file .pygcam.defaults for ref
        # TBD: and invoke the "init" sub-command. Then write a basic config
        # TBD: file with user's values in [DEFAULT] and section for default proj.
        # create a file with the system defaults if no file exists
        with open(usrConfigPath, 'w') as f:
            commented = _getCommentedDefaults(systemDefaults)
            f.write(commented)

    # Create (if not defined) GCAM.ProjectName in each section, holding the
    # section (i.e., project) name. If user has set this, the value is unchanged.
    projectNameVar = 'GCAM.ProjectName'
    for section in _ConfigParser.sections():
        if not (_ConfigParser.has_option(section, projectNameVar) and   # var must exist
                _ConfigParser.get(section, projectNameVar)):            # and not be blank
            _ConfigParser.set(section, projectNameVar, section)

    projectName = getParam('GCAM.DefaultProject', section=DEFAULT_SECTION)
    if projectName:
        setSection(projectName)

    return _ConfigParser

def getConfigDict(section=DEFAULT_SECTION, raw=False):
    """
    Return all variables defined in `section` as a dictionary.

    :param section: (str) the name of a section in the config file
    :return: (dict) all variables defined in the section (which includes
       those defined in DEFAULT.)
    """
    # if not _ConfigParser.has_section(section):
    #     section = DEFAULT_SECTION

    d = {key : value for key, value in _ConfigParser.items(section, raw=raw)}
    return d

def setParam(name, value, section=None):
    """
    Set a configuration parameter in memory.

    :param name: (str) parameter name
    :param value: (any, coerced to str) parameter value
    :param section: (str) if given, the name of the section in which to set the value.
       If not given, the value is set in the established project section, or DEFAULT
       if no project section has been set.
    :return: none
    """
    section = section or getSection()
    _ConfigParser.set(section, name, value)

def getParam(name, section=None, raw=False, raiseError=True):
    """
    Get the value of the configuration parameter `name`. Calls
    :py:func:`getConfig` if needed.

    :param name: (str) the name of a configuration parameters. Note
       that variable names are case-insensitive.
    :param section: (str) the name of the section to read from, which
      defaults to the value used in the first call to ``getConfig``,
      ``readConfigFiles``, or any of the ``getParam`` variants.
    :return: (str) the value of the variable, or None if the variable
      doesn't exist and raiseError is False.
    :raises NoOptionError: if the variable is not found in the given
      section and raiseError is True
    """
    section = section or _ProjectSection

    if not section:
        raise PygcamException('getParam was called without setting "section"')

    if not _ConfigParser:
        getConfig()

    try:
        return _ConfigParser.get(section, name, raw=raw)

    except configparser.NoSectionError:
        if raiseError:
            raise PygcamException('getParam: unknown section "%s"' % section)
        else:
            return None

    except configparser.NoOptionError:
        if raiseError:
            raise PygcamException('getParam: unknown variable "%s"' % name)
        else:
            return None

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

