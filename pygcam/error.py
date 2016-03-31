'''
.. pygcam's Exception classes

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
class PygcamException(Exception):
    """
    Base class for pygcam Exceptions.
    """
    pass

class FileFormatError(PygcamException):
    """
    Indicate a syntax error in a user-managed file.
    """
    pass

class ConfigFileError(FileFormatError):
    """
    Raised when an error is found in the configuration file ``~/.pygcam.cfg``.
    """
    pass


class CommandlineError(Exception):
    """
    Command-line arguments were missing or incorrectly specified.
    """
    pass

class ProgramExecutionError(PygcamException):
    def __init__(self, command, exitCode):
        self.command = command
        self.exitCode = exitCode

    def __str__(self):
        return "Command '%s' failed with exit code %s" % (self.command, self.exitCode)

class SetupException(Exception):
    """
    Raised from the setup sub-system.
    """
    pass
