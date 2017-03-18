#
# Signal handling
#
import signal
from .windows import IsWindows

# Windows has only SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, or SIGTERM
if IsWindows:
    signal.SIGALRM = signal.SIGTERM
    signal.SIGQUIT = signal.SIGTERM

_sigmap = {
    signal.SIGALRM: 'SIGALRM',
    signal.SIGTERM: 'SIGTERM',
    signal.SIGQUIT: 'SIGQUIT',
    signal.SIGINT:  'SIGINT',
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

def raiseSignalException(signum, _frame):
    if signum == signal.SIGALRM:
        raise AlarmSignalException(signum)

    elif signum == signal.SIGTERM:      # TBD: this is sent by SLURM. Same for PBS??
        raise TimeoutSignalException(signum)

    else:
        raise SignalException(signum)


def catchSignals(handler=raiseSignalException):
    signals = [signal.SIGTERM, signal.SIGINT]
    signals.append(signal.SIGABRT if IsWindows else signal.SIGQUIT)

    for sig in signals:
        signal.signal(sig, handler)
