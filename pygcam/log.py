"""
.. Logging support.
   This module allows modules to register themselves for logging which is
   turned on after the app reads configuration information. Modules call
   logger = pygcam.log.getLogger(__name__) as a top-level statement, evaluated
   at load time. This returns the logger, which may not yet be configured.
   When the configuration file has been read, all registered loggers are
   initialized, and all subsequently registered loggers are initialized
   upon instantiation.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.

"""
import logging
from collections import defaultdict
from .config import getParam, getParamAsBoolean, configLoaded
from .error import PygcamException

_formatter  = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
_configured = False
_loggers  = defaultdict(lambda: None)
_consoles = defaultdict(lambda: False)
_logLevel = None
_verbose  = False

def _debug(msg):
    if _verbose:
        print msg

def _configureLogger(logger):
    '''
    Configure the given logger using the info in the cfg object.
    :param logger: a logger instance to configure
    :return: none
    '''
    if not configLoaded():
        raise PygcamException("Error: Can't configure logger %s: configuration object is None." % logger)

    _debug("Configuring logger %s; level=%s" % (logger.name, _logLevel))
    if _logLevel:
        logger.setLevel(_logLevel)

    logConsole = getParamAsBoolean('GCAM.LogConsole')
    loggerName = logger.name

    if logConsole:
        if _consoles[loggerName]:
            _debug("Console for %s previously added" % loggerName)
        else:
            _debug("Adding console logger for %s" % loggerName)
            _consoles[loggerName] = True
            handler = logging.StreamHandler()
            handler.setFormatter(_formatter)
            logger.addHandler(handler)
    else:
        _debug("Console logging is disabled")

    logFile = getParam('GCAM.LogFile')
    if logFile:
        _debug("Configuring file logger for %s" % loggerName)
        handler = logging.FileHandler(logFile, mode='a')
        handler.setFormatter(_formatter)
        logger.addHandler(handler)

    if not (logConsole or logFile):
        # NullHandler doesn't work: logger code references handler.level, which
        # doesn't exist for NullHandler. Instead we use a "null" FileHandler the
        # old-school UNIX way.
        #handler = logging.NullHandler
        _debug("Configuring null logger for %s" % loggerName)
        handler = logging.FileHandler("/dev/null")
        logger.addHandler(handler)


def getLogger(name):
    '''
    Register a logger, which will be set up after the configuration
    file is read.

    :param name: the name of the logger, conventionally passed as __name__.
    :return: a logging logger instance
    '''
    global _loggers

    logger = _loggers[name]
    if not logger:
        logger = logging.getLogger(name)
        _loggers[name] = logger

    if configLoaded():
        _configureLogger(logger)

    return logger


def configureLogs(force=False):
    '''
    Do basicConfig setup and configure all known loggers based on the information
    in the config instance given. If already configured, just return, unless
    force == True.

    :param force: (bool) if True, reconfigure the logs even if already configured.
    :return: none
    '''
    global _configured, _logLevel

    if not force and _configured:
        return

    _logLevel = _logLevel or getParam('GCAM.LogLevel').upper() or 'ERROR'

    _debug("Configuring all loggers from config")

    for logger in _loggers.values():
        _configureLogger(logger)

    _configured = True

def getLevel():
    return _logLevel

def setLevel(level):
    '''
    Set the logging level for all defined loggers.

    :param level: (str) one of ``{'DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL'}`` (case insensitive)
    :return: none
    '''
    global _logLevel
    _logLevel = level.upper()

    for logger in _loggers.values():
        logger.setLevel(_logLevel)


def resetLevel():
    '''
    Set the log level to the current value of GCAM.LogLevel, which may be
    different once the default project name has been set.

    :return: none
    '''
    level = getParam('GCAM.LogLevel', default='ERROR').upper()
    setLevel(level)
