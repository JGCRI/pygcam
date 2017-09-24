# Created on 10/25/14
#
# @author : Rich Plevin
#
# @Copyright 2015 Richard Plevin

class PygcamMcsException(Exception):
    'Base class for application-related errors.'
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

class PygcamMcsUserError(PygcamMcsException):
    'The user provided an incorrect parameter or failed to provide a required one.'
    pass

class PygcamMcsSystemError(PygcamMcsException):
    'Some application-related runtime error.'
    pass

class IpyparallelError(PygcamMcsSystemError):
    pass

class FileExistsError(PygcamMcsSystemError):
    def __init__(self, filename):
        self.message = "File %r already exists" % filename

    # def __str__(self):
    #     return repr(self.message)

class FileMissingError(PygcamMcsSystemError):
    def __init__(self, filename):
        self.message = "File %r is missing" % filename

class ShellCommandError(PygcamMcsSystemError):
    def __init__(self, msg, exitStatus=0):
        self.message = msg
        self.exitStatus = exitStatus

    def __str__(self):
        statusMsg = " exit status %d" % self.exitStatus if self.exitStatus else ""
        return "ShellCommandError: %s%s" % (statusMsg, self.exitStatus)

class GcamToolError(PygcamMcsSystemError):  # TBD: define in pygcam?
    pass

class BaseSpecError(PygcamMcsSystemError):
    filename = ''
    lineNum = 0

    def __init__(self, message):
        if self.filename and self.lineNum:
            self.message = 'File %s, line %i: ' % (self.filename, self.lineNum) + message
        else:
            self.message = message

class DistributionSpecError(BaseSpecError):
    pass
