from __future__ import print_function
from collections import OrderedDict
import os
import select
import subprocess as subp
import time

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, Event

#
# Class to support multi-page applications with dash
#

class Page(object):
    """
    Defines one app page, which may support a set of subpages
    """
    def __init__(self, id, layout, label=None, pageSet=None):
        self.layout = layout
        self.id = id
        self.label = label or id       # use object's ID if no label is provided
        self.pageSet = pageSet

    def __str__(self):
        return "<Page id='%s' label='%s'>" % (self.id, self.label)

    def render(self):
        pageSet = self.pageSet
        layout = html.Div([pageSet.render(), self.layout]) if pageSet else self.layout
        return layout

    def pageId(self):
        return self.id

    def select(self, id):
        return self.pageSet.select(id) if self.pageSet else None

class PageSet(object):
    def __init__(self, id, pages, default):
        self.id = id
        self.contentId = id + '-content'

        self.pages = OrderedDict()
        for page in pages:
            self.pages[page.id] = page

        self.default = default
        self.selected = self.select(self.default)
        self.navPrefix = 'sub-nav-'  # non-Root (lower-level) menu items


    def __str__(self):
        return "<PageSet %s default:%s selected:%s>" % (self.pages.keys(), self.default, self.selected)

    def select(self, id):
        self.selected = self.pages[id or self.default]
        return self.selected

    def navbar(self):
        pages = self.pages.values()
        prefix = self.navPrefix

        def pageURL(page):
            return "/%s/%s" % (self.id, page.id) if self.id else '/' + page.id

        def buttonClass(page):
            return prefix + ('selected' if page == self.selected else 'button')

        layout = html.Div([
            html.Div([dcc.Link(pg.label, href=pageURL(pg), className=buttonClass(pg)) for pg in pages],
                     className=(prefix + 'bar'))],
            className=(prefix + 'bg'))
        return layout

    def render(self):
        page = self.selected
        contents = page.render() if page else ''
        layout = html.Div([self.navbar(), contents])
        return layout


class RootPage(PageSet):
    def __init__(self, app, pages, default=None):
        url = dcc.Location(id='url', refresh=False)
        app.layout = html.Div([url, html.Div(id='root-content')])

        default = default or pages[0].id
        super(RootPage, self).__init__('', pages, default)
        self.navPrefix = 'nav-'  # Root (top-level) menu items (must set after super.__init__)

        @app.callback(Output('root-content', 'children'),
                      [Input('url', 'pathname')])
        def displayPage(pathname):
            print("Pathname is", pathname)
            id = pathname[1:] if pathname else self.default
            elts = id.split('/')
            pageId = elts[0]
            page = self.select(pageId)
            if page and len(elts) > 1:
                subpage = elts[1]
                page.select(subpage)

            layout = self.render()
            return [layout]

def dataStore(id):
    return html.Div(id=id, style={'display': 'none'})

class Terminal(object):

    counter = 0     # to create unique ids

    def __init__(self, updateSeconds=1):
        self.status  = None
        self.proc    = None
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
        app.scripts.append_script({'external_url': 'https://codepen.io/plevin/pen/MvpeNV.js'})

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
                return '[No process is running]\n\n' + self.text

            fd = self.proc.stdout.fileno()
            newText = ''

            # Loop while there is data to read
            while len(select.select([fd], [], [], 0)[0]) == 1:
                print("reading...")
                buf = os.read(fd, 2048)     # Read up to a 2 KB chunk of data
                if buf == '':
                    break

                newText += buf

            self.text += newText

            self.status = self.proc.poll()
            self.running = self.status is None
            if not self.running:
                self.text += "\n[Process exited]\n"
                self.proc = None

            return self.text


        @app.callback(Output('button-div', 'children'),     # writing to this is a no-op
                      [Input(buttonId, 'n_clicks')])
        def processClick(clicks):
            if clicks is None:
                # print("Ignoring click=None")
                return ''

            # print("Real button click")
            if self.running:
                self.stopCommand()
            else:
                command = 'gt run -S baseline'
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
            # print('Setting ms=%s' % ms)
            return ms

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
            self.proc = None
            self.text += "[Terminated process %d]\n" % pid

        self.running = False

    def runCommand(self, command):
        if self.running:
            print('Already running a command')
            return

        self.status = None
        self.text = '$ ' + command + '\n'
        self.proc = subp.Popen(command, stdout=subp.PIPE, stderr=subp.STDOUT, shell=True,   # for now...
                               bufsize=1,    # line buffered
                               universal_newlines=True, cwd=None, env=None)
        self.running = True
        print('Running "%s"' % command)


class ActionInfo(object):
    """
    Converts argparse "actions" into HTML widgets.
    """
    def __init__(self, action):
        self.action = action
        self.actionClass = type(action).__name__

        self.name = ', '.join(action.option_strings) if action.option_strings else action.dest

        t = action.type
        if t == str:
            self.dataType = 'text'
        elif t in (int, float):
            self.dataType = t.__name__
        else:
            self.dataType = 'text'

        self.display = self.actionClass not in ('_VersionAction', '_HelpAction', '_SubParsersAction') and \
            self.name != 'VERSION'

    def __str__(self):
        return "<ActionInfo %s %s>" % (self.actionClass, self.name)

    def radio(self, options, default='', vertical=False):
        return dcc.RadioItems(
                    options=[{'label': str(opt), 'value': opt} for opt in options],
                    value=default,
                    labelStyle={'display': 'block' if vertical else 'inline-block'})

    def input(self, placeholder='Enter a value...', value=''):
        if not value and self.action.metavar:
            placeholder = self.action.metavar

        return dcc.Input(placeholder=placeholder, type=self.dataType, value=value, className='option')

    def render(self):
        """
        Render an argparse option as HTML
        """
        Y = 'Yes'
        N = 'No'

        if self.actionClass == '_StoreTrueAction':
            widget = self.radio([Y, N], N)

        elif self.actionClass == '_StoreFalseAction':
            widget = self.radio([Y, N], Y)

        elif self.actionClass == '_StoreAction':
            default = self.action.default
            choices = self.action.choices
            widget = self.radio(choices, default, vertical=True) if choices else self.input(value=default)

        elif self.actionClass == '_AppendAction':
            default = self.action.default
            widget = self.input(value=default)

        else:
            widget = html.P("%s: unknown action type %s" % (self.name, self.actionClass))

        name = self.name
        if self.action.required:
            name = html.Span(name + '*', className='required')

        help = "(%s) " % self.dataType if self.dataType != 'text' else ''
        help += (self.action.help or '')

        return html.Tr(children=[
            html.Td(name,   className='lined', style={'width': 150}),
            html.Td(widget, className='lined', style={'width': 200}),
            html.Td(help,   className='lined')
        ], className='cmd')

def actionTable(sectionName, actions, helpText=None):
    """
    Generate a table with option names and option data entry widgets
    """
    elements = [html.H3(sectionName, className='band')]
    if helpText:
        elements.append(html.Div(helpText, className='helptext'))

    def th(value):
        return html.Th(value, className='lined')

    headings = html.Tr([th('Option'), th('Value'), th('Description')])
    rows = [headings] + [a.render() for a in actions if a.display]
    elements.append(html.Table(children=rows, className='cmd'))
    return elements
