'''
.. Signal Handling

.. Adapted from pygcam.
   Added to opgee on 3/29/21.

.. Copyright (c) 2016-2021 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import signal
from .windows import IsWindows

# Windows has only SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, or SIGTERM
_sigmap = {
    signal.SIGABRT: 'SIGABRT',
    signal.SIGINT:  'SIGINT',
    signal.SIGTERM: 'SIGTERM',
} if IsWindows else {
    signal.SIGINT:  'SIGINT',
    signal.SIGALRM: 'SIGALRM',
    signal.SIGTERM: 'SIGTERM',
    signal.SIGQUIT: 'SIGQUIT',
}

def _signame(signum):
    return _sigmap[signum] if signum in _sigmap else 'signal %d' % signum


class SignalException(Exception):
    def __init__(self, signum):
        self.signum = signum
        self.signame = _signame(signum)

    def __str__(self):
        return "Process received %s" % self.signame

class AlarmSignalException(SignalException):
    pass

class TimeoutSignalException(SignalException):
    pass

class UserInterruptException(SignalException):
    pass

def raiseSignalException(signum, _frame):
    if not IsWindows and signum == signal.SIGALRM:
        raise AlarmSignalException(signum)

    elif signum == signal.SIGTERM:      # this is sent by SLURM to kill engines
        raise TimeoutSignalException(signum)

    elif signum == signal.SIGINT:       # control-c by user
        raise UserInterruptException(signum)

    else:
        raise SignalException(signum)


def catchSignals(handler=raiseSignalException):
    for sig in _sigmap:
        signal.signal(sig, handler)
