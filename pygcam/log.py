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

# TBD: Allow user to configure logLevel at the package or module level
# TBD: using something like LogLevels = pkg.module:DEBUG pkg:INFO and so on
# TBD: and similarly for LogConsole and LogFile?

_configured = False
_logLevel   = None

_verbose    = False

def _debug(msg):
    if _verbose:
        print(msg)

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


def getLogger(name):
    '''
    Register a logger, which will be set up after the configuration
    file is read.

    :param name: the name of the logger, conventionally passed as __name__.
    :return: a logging logger instance
    '''
    _debug('getLogger("%s")' % name)
    logger = logging.getLogger(name)
    configureLogs()
    return logger


def configureLogs(force=False):
    '''
    Do basicConfig setup and configure root logger based on the information
    in the config instance given. If already configured, just return, unless
    force == True.

    :param force: (bool) if True, reconfigure the logs even if already configured.
    :return: none
    '''
    global _configured, _logLevel

    if not force and _configured:
        return

    if not configLoaded():
        return

    fileFormat    = getParam('GCAM.LogFileFormat')
    consoleFormat = getParam('GCAM.LogConsoleFormat')

    logger = logging.getLogger()

    if force:
        # Remove all handlers from root logger
        for handler in logger.handlers:
            logger.removeHandler(handler)


    logConsole = getParamAsBoolean('GCAM.LogConsole')
    logFile    = getParam('GCAM.LogFile')

    _logLevel = _logLevel or getParam('GCAM.LogLevel').upper() or 'ERROR'
    if _logLevel:
        logger.setLevel(_logLevel)

    _debug("\nConfiguring root, level=%s" % _logLevel)

    def addHandler(formatStr, logFile=None):
        if logFile:
            _mkdirs(os.path.dirname(logFile))

        handler = logging.FileHandler(logFile, mode='a') if logFile else logging.StreamHandler()
        handler.setFormatter(logging.Formatter(formatStr))
        logger.addHandler(handler)
        _debug("Added %s handler to root logger" % ('file' if logFile else 'console'))

    if logConsole:
        addHandler(consoleFormat)
    else:
        _debug("Console logging is disabled")

    if logFile:
        addHandler(fileFormat, logFile=logFile)
    else:
        _debug("File logging is disabled")

    if not logger.handlers:
        # Add a null handler if there are no others
        logger.addHandler(logging.NullHandler())
        _debug("Added NullHandler to root logger")

    _configured = True


def getLogLevel():
    """
    Get the currently set LogLevel.

    :return: (str) one of ``'DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL'``
    """
    return _logLevel

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


def resetLogLevel():
    '''
    Set the log level to the current value of GCAM.LogLevel, which may be
    different once the default project name has been set.

    :return: none
    '''
    level = getParam('GCAM.LogLevel')
    setLogLevel(level)
