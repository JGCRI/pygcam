'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os
import io
import platform
import re
from pkg_resources import resource_string
from ConfigParser import SafeConfigParser
from .error import ConfigFileError, PygcamException, CommandlineError
from .subcommand import SubcommandABC

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
    result += "\n# User's home directory\n# Home = %s\n\n" % getParam('Home', raw=True)
    result += "# Name of gcam executable relative to 'exe' dir\n# GCAM.Executable = %s\n\n" % getParam('GCAM.Executable', raw=True)
    result += "# Location of ModelInterface jar file\n# GCAM.JarFile = %s\n\n" % getParam('GCAM.JarFile', raw=True)
    result += "# Whether to use a virtual display when running ModelInterface\n# GCAM.UseVirtualBuffer = %s\n\n" % getParam('GCAM.UseVirtualBuffer', raw=True)
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
    and the configuration files are read.

    :return: a `SafeConfigParser` instance.
    """
    return _ConfigParser or readConfigFiles()

def readConfigFiles():
    """
    Read the pygcam configuration file, ``~/.pygcam.cfg``. "Sensible" default values are
    established first, which overwritten by values found in the user's configuration
    file.

    :return: a populated SafeConfigParser instance
    """
    global _ConfigParser

    # HOME exists on all Unix-like systems; for Windows it's HOMEPATH
    if PlatformName == 'Windows':
        home = os.path.realpath(os.getenv('HOMEPATH'))  # adds home drive
        home = home.replace('\\', '/')                  # avoids '\' quoting issues
    else:
        home = os.getenv('HOME')

    if PlatformName == 'Darwin':
        jarFile = '%(GCAM.ModelInterface)s/ModelInterface.app/Contents/Resources/Java/ModelInterface.jar'
        exeFile = 'Release/objects'
        useXvfb = 'False'
        editor  = 'open -e'
    elif PlatformName == 'Linux':
        jarFile = '%(GCAM.ModelInterface)s/ModelInterface.jar'
        exeFile = './gcam.exe'
        useXvfb = 'True'
        editor  = os.getenv('EDITOR', 'vi')
    elif PlatformName == 'Windows':
        jarFile = '%(GCAM.ModelInterface)s/ModelInterface.jar'
        exeFile = 'Objects-Main.exe'
        useXvfb = 'False'
        editor  = os.getenv('EDITOR', 'notepad.exe')
    else:
        # unknown what this might be, but just in case
        jarFile = '%(GCAM.ModelInterface)s/ModelInterface.jar'
        exeFile = 'gcam.exe'
        useXvfb = 'False'
        editor  = os.getenv('EDITOR', 'vi')

    # Initialize config parser with default values
    _ConfigParser = SafeConfigParser()

    _ConfigParser.optionxform = str     # don't force all names to lower-case

    def readConfigResourceFile(filename):
        data = resource_string('pygcam', filename)
        _ConfigParser.readfp(io.BytesIO(data))
        return data

    systemDefaults = readConfigResourceFile('etc/system.cfg')

    _ConfigParser.set(DEFAULT_SECTION, 'Home', home)
    _ConfigParser.set(DEFAULT_SECTION, 'GCAM.Executable', exeFile)
    _ConfigParser.set(DEFAULT_SECTION, 'GCAM.JarFile', jarFile)
    _ConfigParser.set(DEFAULT_SECTION, 'GCAM.UseVirtualBuffer', useXvfb)
    _ConfigParser.set(DEFAULT_SECTION, 'GCAM.TextEditor', editor)

    siteConfig = os.getenv('PYGCAM_SITE_CONFIG')
    if siteConfig:
        try:
            with open(siteConfig) as fp:
                _ConfigParser.readfp(fp)
        except Exception as e:
            print("WARNING: Failed to read site config file: %s" % e)

    # Customizations are stored in ~/.pygcam.cfg
    usrConfigPath = os.path.join(home, USR_CONFIG_FILE)

    # os.path.exists doesn't always work on Windows, so just try opening it.
    try:
        with open(usrConfigPath) as fp:
           _ConfigParser.readfp(fp)

    except IOError as e:
        # create a file with the system defaults if no file exists
        with open(usrConfigPath, 'w') as fp:
            commented = _getCommentedDefaults(systemDefaults)
            fp.write(commented)

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

def setParam(name, value, section=DEFAULT_SECTION):
    """
    Set a configuration parameter in memory. The new value is not
    written to the config file.

    :param name: (str) parameter name
    :param value: (any, coerced to str) parameter value
    :param section: (str) if given, the name of the section in which to set the value.
       If not given, the value is set in the DEFAULT section.
    :return: none
    """
    _ConfigParser.set(section, name, value)

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
        getConfig()

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
    VERSION = '0.2'

    def __init__(self, subparsers):
        kwargs = {'help' : '''List the values of configuration variables from
                  ~/.pygcam.cfg configuration file.'''}

        super(ConfigCommand, self).__init__('config', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('-d', '--useDefault', action='store_true',
                            help='''Indicates to operate on the DEFAULT
                                    section rather than the project section.''')

        parser.add_argument('-e', '--edit', action='store_true',
                            help='''Edit the configuration file. The command given by the
                            value of config variable GCAM.TextEditor is run with the
                            .pygcam.cfg file as an argument.''')

        parser.add_argument('name', nargs='?', default='',
                            help='''Show the names and values of all parameters whose
                            name contains the given value. The match is case-insensitive.
                            If not specified, all variable values are shown.''')

        parser.add_argument('-x', '--exact', action='store_true',
                            help='''Treat the text not as a substring to match, but
                            as the name of a specific variable. Match is case-sensitive.
                            Prints only the value.''')

        parser.add_argument('-t', '--test', action='store_true',
                            help='''Test the settings in the configuration file to ensure
                            that the basic setup is ok, i.e., required parameters have
                            values that make sense. If specified, no variables are displayed.''')

        parser.add_argument('--version', action='version', version='%(prog)s ' + self.VERSION)

        return parser

    def testConfig(self, section):
        requiredDirs = ['SandboxRoot', 'SandboxDir', 'ProjectRoot', 'ProjectDir',
                        'QueryDir', 'ModelInterface', 'RefWorkspace', 'TempDir']
        requiredFiles = ['ProjectXmlFile', 'RefConfigFile', 'JarFile']
        optionalDirs  = ['UserTempDir']
        optionalFiles = ['RegionMapFile', 'RewriteSetsFile']

        dirVars  = requiredDirs  + optionalDirs
        fileVars = requiredFiles + optionalFiles

        optionalVars = optionalDirs + optionalFiles

        for item in dirVars + fileVars:
            var = 'GCAM.' + item
            value = getParam(var)

            if not value:
                if item in optionalVars:
                    continue
                print("Config variable %s is empty" % var)

            elif not os.path.lexists(value):
                print("Config variable %s refers to missing file or directory '%s'" % (var, value))

            elif not os.path.isfile(value) and item in fileVars:
                print("Config variable %s does not refer to a file (%s)" % (var, value))

            elif not os.path.isdir(value) and item in dirVars:
                print("Config variable %s does not refer to a directory (%s)" % (var, value))

            print('OK:', var, '=', value)

    def run(self, args, tool):
        if args.edit:
            import subprocess

            cmd = "%s %s/%s" % (getParam('GCAM.TextEditor'), getParam('Home'), USR_CONFIG_FILE)
            print(cmd)
            exitStatus = subprocess.call(cmd, shell=True)
            if exitStatus != 0:
                raise PygcamException("TextEditor command '%s' exited with status %s\n" % (cmd, exitStatus))
            return

        section = 'DEFAULT' if args.useDefault else args.configSection

        if section != 'DEFAULT' and not _ConfigParser.has_section(section):
            raise CommandlineError("Unknown configuration file section '%s'" % section)

        if args.test:
            self.testConfig(section)
            return

        if args.name and args.exact:
            value = getParam(args.name, section=section)
            if value is not None:
                print(value)
            return

        # if no name is given, the pattern matches all variables
        pattern = re.compile('.*' + args.name + '.*', re.IGNORECASE)

        print("[%s]" % section)
        for name, value in sorted(_ConfigParser.items(section)):
            if pattern.match(name):
                print("%22s = %s" % (name, value))


PluginClass = ConfigCommand
