'''
.. pygcam's Exception classes

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
class PygcamException(Exception):
    """
    Base class for pygcam Exceptions.
    """
    pass

class FileMissingError(PygcamException):
    """
    Indicate that a required file was not found or not readable.
    """

    def __init__(self, filename, reason):
        self.filename = filename
        self.reason   = reason

    def __str__(self):
        return "Can't read %s: %s" % (self.filename, self.reason)

class FileFormatError(PygcamException):
    """
    Indicate a syntax error in a user-managed file.
    """
    pass

class XmlFormatError(FileFormatError):
    pass

class FileExistsError(PygcamException):
    """
    Raised when trying to write a file that already exists (if not allowed)
    """
    def __init__(self, filename):
        self.filename = filename

    def __str__(self):
        return "Refusing to overwrite file: %s" % self.filename

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
    """
    Raised when attempt to execute a program (e.g., the GCAM model or ModelInterface) fails.
    """
    def __init__(self, command, exitCode=None):
        self.command = command
        self.exitCode = exitCode

    def __str__(self):
        return "Command '%s' failed with exit code %s" % (self.command, self.exitCode)

class GcamError(PygcamException):
    """
    The gcamWrapper detected and error and terminated the model run.
    """
    pass

class GcamSolverError(GcamError):
    """
    The gcamWrapper detected and error and terminated the model run.
    """
    pass

class SetupException(Exception):
    """
    Raised from the setup sub-system.
    """
    pass
