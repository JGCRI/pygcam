#
# Signal handling
#
import signal
from .windows import IsWindows

# Windows has only SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, or SIGTERM
_sigmap = {signal.SIGABRT: 'SIGABRT',
           signal.SIGTERM: 'SIGTERM',
           signal.SIGINT:  'SIGINT'}

if not IsWindows:
    _sigmap[signal.SIGHUP]  = 'SIGHUP'
    _sigmap[signal.SIGUSR1] = 'SIGUSR1'
    _sigmap[signal.SIGUSR2] = 'SIGUSR2'
    _sigmap[signal.SIGALRM] = 'SIGALRM'
    _sigmap[signal.SIGQUIT] = 'SIGQUIT'


def _signame(signum):
    return _sigmap[signum] if signum in _sigmap else 'signal %d' % signum


class SignalException(Exception):
    def __init__(self, signum):
        self.signum = signum
        self.signame = _signame(signum)

    def __str__(self):
        return "SignalException: process received %s" % self.signame


def raiseSignalException(signum, _frame):
    raise SignalException(signum)


def catchSignals(handler=raiseSignalException):
    signals = [signal.SIGTERM, signal.SIGINT]
    signals.append(signal.SIGABRT if IsWindows else signal.SIGQUIT)

    for sig in signals:
        signal.signal(sig, handler)
