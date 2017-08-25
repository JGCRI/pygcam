"""
.. Logging support.
   This module allows modules to register themselves for logging which is
   turned on after the app reads configuration information. Modules call
   logger = pygcam.log.getLogger(__name__) as a top-level statement, evaluated
   at load time. This returns the logger, which may not yet be configured.
   When the configuration file has been read, all registered loggers are
   initialized, and all subsequently registered loggers are initialized
   upon instantiation.

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
import os
import logging
from .config import getParam, getParamAsBoolean, configLoaded
from .error import PygcamException

_logLevel   = None
_verbose    = False

def _debug(msg):
    if _verbose:
        print(msg)

def getLevels(levelStr=None):
    """
    Get log levels for pygcam as a whole or for indicated modules individually.
    Modules not prefixed or starting with 'mcs.' are interpreted to be in pygcam.
    Example: LogLevel = WARNING, tool:DEBUG, utils:INFO, mcs.util:INFO

    :param levelStr: a comma-delimited string of module:logLevel values. If
        no ':' is present, the value is treated as the default logLevel for pygcam.
        If levelStr is None, the value of the variable 'GCAM.LogLevel' is used.
    :return: None
    """
    result = {}

    levelStr = levelStr or getParam('GCAM.LogLevel')

    levels = map(str.strip, levelStr.split(','))
    for level in levels:
        if ':' in level:
            module, lvl = map(str.strip, level.split(':'))
            if '.' not in module or module.startswith('mcs.'):
                module = 'pygcam.' + module
        else:
            module = 'pygcam'
            lvl = level.strip()

        result[module] = lvl

    return result


#
# Copied here from utils.py to avoid an import loop
#
def _mkdirs(newdir, mode=0o770):
    """
    Try to create the full path `newdir` and ignore the error if it already exists.
    """
    from errno import EEXIST

    try:
        os.makedirs(newdir, mode)
    except OSError as e:
        if e.errno != EEXIST:
            raise

# Loggers for top-level package names, e.g., 'pygcam'.
# TBD: Revise this to set log levels for packages and for indiv modules if user so specifies
_PkgLoggers = {}

# TBD: set propagate to False only for explicitly set module or package loggers
def _createPkgLogger(dotspec):
    pkgName = dotspec.split('.')[0]

    if pkgName and pkgName not in _PkgLoggers:
        _debug('_createPkgLogger("%s") from %s' % (pkgName, dotspec))
        logger = logging.getLogger(pkgName)
        # Note: 'traitlets' library uses root logger, which we don't want to enable here
        logger.propagate = False
        _PkgLoggers[pkgName] = logger
        _configureLogger(pkgName)

def getLogger(name):
    '''
    Register a logger, which will be set up after the configuration
    file is read.

    :param name: the name of the logger, conventionally passed as __name__.
    :return: a logging logger instance
    '''
    _debug('getLogger("%s")' % name)
    logger = logging.getLogger(name)
    _createPkgLogger(name)
    return logger

def _addHandler(logger, formatStr, logFile=None):
    if logFile:
        _mkdirs(os.path.dirname(logFile))

    handler = logging.FileHandler(logFile, mode='a') if logFile else logging.StreamHandler()
    handler.setFormatter(logging.Formatter(formatStr))
    logger.addHandler(handler)
    _debug("Added %s handler to '%s' logger" % ('file' if logFile else 'console', logger.name))

def _configureLogger(name, force=False):
    try:
        logger = _PkgLoggers[name]
    except KeyError:
        raise PygcamException("Can't configure unknown logger '%s'" % name)

    # If not forcing, skip loggers that already have handlers installed
    if not force and logger.handlers:
        return

    global _logLevel
    if not _logLevel:
        # TBD: parse LogLevel to a dict via getLevels and cache that instead
        _logLevel = getParam('GCAM.LogLevel').upper() or 'ERROR'

    _debug("Configuring %s, level=%s" % (name, _logLevel))
    logger.setLevel(_logLevel)

    for handler in logger.handlers:
        if not isinstance(handler, logging.NullHandler):
            handler.flush()
        logger.removeHandler(handler)

    logConsole = getParamAsBoolean('GCAM.LogConsole')
    if logConsole:
        consoleFormat = getParam('GCAM.LogConsoleFormat')
        _addHandler(logger, consoleFormat)

    logFile = getParam('GCAM.LogFile')
    if logFile:
        fileFormat = getParam('GCAM.LogFileFormat')
        _addHandler(logger, fileFormat, logFile=logFile)

    if not logger.handlers:
        logger.addHandler(logger, logging.NullHandler())
        _debug("Added NullHandler to root logger")


def configureLogs(force=False):
    '''
    Do basicConfig setup and configure package loggers based on the information
    in the config instance given. Unless force == True, loggers with handlers will
    not be reconfigured.

    :param force: (bool) if True, reconfigure the logs even if already configured.
    :return: none
    '''
    if not configLoaded():
        return

    # TBD: use getLevels() instead
    for name in _PkgLoggers.keys():
        _configureLogger(name, force=force)


# TBD: obsolete once per-module levels can be set
def getLogLevel():
    """
    Get the currently set LogLevel.

    :return: (str) one of ``'DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL'``
    """
    return _logLevel

# TBD: modify to parse level str. (Used only pygcam.tool currently.)
# TBD: fix doc string to reference format in getLevels()
def setLogLevel(level):
    '''
    Set the logging level for all defined loggers.

    :param level: (str) one of ``'DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL'`` (case insensitive)
    :return: none
    '''
    global _logLevel
    _logLevel = level.upper()
    logger = logging.getLogger()
    logger.setLevel(_logLevel)

# Deprecated
# def resetLogLevel():
#     '''
#     Set the log level to the current value of GCAM.LogLevel, which may be
#     different once the default project name has been set.
#
#     :return: none
#     '''
#     level = getParam('GCAM.LogLevel')
#     setLogLevel(level)
