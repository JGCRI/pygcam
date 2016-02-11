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

class ConfigFileError(PygcamException):
    """
    Raised when an error is found in the configuration file ``~/.pygcam.cfg``.
    """
    pass
