from __future__ import print_function
from collections import OrderedDict

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from pygcam.log import getLogger
from pygcam.subcommand import SubcommandABC

_logger = getLogger(__name__)

def dataStore(id):
    """
    Generate an invisible div with the given id
    """
    return html.Div(id=id, style={'display': 'none'})

#
# Class to support multi-page applications with dash
#
class Page(object):
    """
    Defines one app page, which may support a set of subpages
    """
    def __init__(self, app, id, layout, label=None, pageSet=None, actions=None):
        self.app = app
        self.id = id
        self.layout = layout
        self.pageSet = pageSet
        self.actions = actions

        if not label:
            subcmd = SubcommandABC.getInstance(self.id)
            label = subcmd.label

        self.label = label
        self.generateCallbacks() # callbacks for generated widgets

    def __str__(self):
        return "<Page id='%s' label='%s'>" % (self.id, self.label)

    #
    # TBD: regenerate layout from actions (which have state) each time, rather than using initial layout
    #
    def render(self):
        pageSet = self.pageSet
        layout = self.getLayout()
        layout = html.Div([pageSet.render(), layout]) if pageSet else layout
        return layout

    def pageId(self):
        return self.id

    def select(self, id):
        return self.pageSet.select(id) if self.pageSet else None

    def getLayout(self):
        return self.layout  # for now

    def getArgs(self):
        args = [action.cmdlineArg() for action in self.actions]
        args = filter(None, args)   # remove Nones
        return ' '.join(args)

    def getCommand(self):
        """
        Return the command implied by the values in the GUI
        """
        globalArgs = RootPage.globalArgs()
        args = self.getArgs()
        cmd  = "gt %s %s %s" % (self.id, globalArgs, args)
        return cmd

    def generateCallbacks(self):
        app = self.app
        if self.actions:
            for action in self.actions:
                action.generateCallback(app)


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
    instance = None

    def __init__(self, app, term, pages, default=None):
        RootPage.instance = self

        url = dcc.Location(id='url', refresh=False)
        app.layout = html.Div([url,
                               html.Div(id='root-content'),
                               html.Div([html.H3('Command terminal'),
                                         term.layout],
                                        id='terminal-div')
                               ])

        self.navPrefix = 'nav-'  # Root (top-level) menu items (must set after super.__init__)
        default = default or pages[0].id

        super(RootPage, self).__init__('', pages, default)

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
            selected = page.pageSet.selected if page.pageSet else page

            term.setPage(selected)
            return [layout]

        @app.callback(Output('terminal-div', 'style'),
                      [Input('url', 'pathname')])
        def showTerminal(pathname):
            # we don't show terminal for globalArgs since it's not a sub-command
            value = 'none' if pathname == '/globalArgs' else 'inline'
            style = {'display': value}
            return style

    @classmethod
    def globalArgs(cls):
        self = RootPage.instance
        globalArgsPage = self.pages['globalArgs']
        return globalArgsPage.getArgs()
