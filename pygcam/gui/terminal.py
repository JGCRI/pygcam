from __future__ import print_function
import subprocess as subp
import time

from pygcam.log import getLogger
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, Event

_logger = getLogger(__name__)

class Terminal(object):

    counter = 0     # to create unique ids

    def __init__(self, updateSeconds=2, toConsole=False):
        self.status = None
        self.proc   = None
        self.page   = None
        self.queue  = None
        self.toConsole = toConsole

        self.counter += 1
        self.intervalId = intervalId = 'interval-%d' % self.counter
        self.terminalId = terminalId = 'terminal' # 'terminal-%d' % self.counter
        self.buttonId   = buttonId   = 'button-%d'   % self.counter

        self.running = False
        self.ms = 1000 * updateSeconds
        self.text = ''
        self.layout = html.Div([
            # Non-displayed divs are useful for chaining events & inputs
            html.Div(id='timer-div',  style={'display': 'none'}),
            html.Div(id='button-div', style={'display': 'none'}),

            dcc.Interval(id=intervalId, interval=1e6), # initially a long interval

            html.Button('Run', id=buttonId, className='shadow'),
            html.Br(),
            html.Div(children="[No process is running]",
                     id=terminalId,
                     className='terminal')
        ], className='centered')


    def registerCallbacks(self, app):
        terminalId = self.terminalId
        intervalId = self.intervalId
        buttonId   = self.buttonId

        # Add support for staying scrolled to bottom of 'terminal' div
        # app.scripts.append_script({'external_url': 'https://codepen.io/plevin/pen/MvpeNV.js'})

        # Since events aren't handled as well as inputs, we convert the
        # timer event into an input by setting the value in a hidden <div>.
        @app.callback(Output('timer-div', 'children'),
                      events=[Event(intervalId, 'interval')])
        def timerToInput():
            return str(time.time())     # because it changes each call

        @app.callback(Output(terminalId, 'children'),
                      [Input('timer-div', 'children')])
        def updateTerminal(timer):
            # print("updateTerminal(%s)" % timer)
            if not self.proc:
                return self.text

            newText = ''

            # Loop while there is data to read
            q = self.queue
            while q.qsize() > 0:
                buf = q.get_nowait()
                if buf == '':
                    break

                newText += buf.decode('utf-8')

            self.text += newText

            self.status = self.proc.poll()
            self.running = self.status is None
            if not self.running:
                self.text += "\n[Process exited]\n"
                self.proc = self.fd = None

            return self.text


        @app.callback(Output('button-div', 'children'),     # writing to this is a no-op
                      [Input(buttonId, 'n_clicks')])
        def processClick(clicks):
            if clicks is None:
                return ''

            if self.running:
                self.stopCommand()
            else:
                command = self.page.getCommand()
                self.runCommand(command)

            return str(time.time())

        # Set button text to match running state, on click or timer.
        @app.callback(Output(buttonId, 'children'),
                      [Input('button-div', 'children'),
                       Input('timer-div', 'children')])
        def clicks(buttonInfo, timerInfo):
            # print("clicks: button:%s, timer:%s" % (buttonInfo, timerInfo))
            return 'Stop' if self.running else 'Run'


        # Set a short interval timer when a proc is running, otherwise
        # set it to an hour (effectively disabling it.)
        @app.callback(Output(intervalId, 'interval'),
                      [Input('button-div', 'children'),
                       Input('timer-div', 'children')])
        def setTimer(buttonInfo, timerInfo):
            # print("setTimer: button:%s, timer:%s" % (buttonInfo, timerInfo))
            oneHour = 60 * 60 * 1000
            ms = self.ms if self.running else oneHour
            return ms

    def setPage(self, page):
        # print("Setting page to %s" % page)
        self.page = page

    def stopCommand(self):
        import time
        proc = self.proc

        if proc:
            pid = proc.pid
            self.text += "\n[Sending SIGTERM to process %d]\n" % pid
            proc.terminate()
            time.sleep(2)
            if proc.poll() is None:  # follow with SIGKILL if process is persistent
                time.sleep(3)
                self.text += "[Sending SIGKILL to process %d]\n" % pid
                proc.kill()

            proc.wait()
            self.proc = self.fd = None
            self.text += "[Terminated process %d]\n" % pid

        self.running = False

    def runCommand(self, command):
        from ..utils import queueForStream

        if self.running:
            _logger.warning('Already running a command')
            return

        self.status = None
        self.text = '$ ' + command + '\n'

        _logger.info('Running "%s"' % command)
        if self.toConsole:
            subp.call(command, shell=True)
        else:
            self.proc = subp.Popen(command, stdout=subp.PIPE, stderr=subp.STDOUT, shell=True,   # for now...
                                   bufsize=1,    # line buffered
                                   universal_newlines=True, cwd=None, env=None)

            self.queue = queueForStream(self.proc.stdout)
            self.running = True

