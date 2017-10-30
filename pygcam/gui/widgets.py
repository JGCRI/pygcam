from __future__ import print_function
from collections import OrderedDict

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from pygcam.log import getLogger

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
        self.label = label or id    # use object's ID if no label is provided
        self.pageSet = pageSet
        self.actions = actions

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

    def getCommand(self):
        """
        Return the command implied by the values in the GUI
        """
        args = [action.cmdlineArg() for action in self.actions]
        #args = filter(None, args)   # remove Nones
        cmd  = "gt %s %s" % (self.id, ' '.join(args))
        return cmd

    def generateCallbacks(self, app):
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

    def generateCallbacks(self, app):
        for page in self.pages.values():
            page.generateCallbacks(app)


class RootPage(PageSet):
    def __init__(self, app, term, pages, default=None):
        url = dcc.Location(id='url', refresh=False)
        app.layout = html.Div([url,
                               html.Div(id='root-content'),
                               html.Div([html.H3('Command terminal'),
                                         term.layout]
                                        )
                               ])

        self.navPrefix = 'nav-'  # Root (top-level) menu items (must set after super.__init__)
        default = default or pages[0].id

        super(RootPage, self).__init__('', pages, default)

        app.config['suppress_callback_exceptions']=True
        self.generateCallbacks(app) # callbacks for generated widgets

        @app.callback(Output('root-content', 'children'),
                      [Input('url', 'pathname')])
        def displayPage(pathname):
            print("Pathname is", pathname)
            id = pathname[1:] if pathname else self.default
            elts = id.split('/')
            pageId = elts[0]
            page = self.select(pageId)
            subpage = None

            if page and len(elts) > 1:
                subpage = elts[1]
                page.select(subpage)

            layout = self.render()
            selected = subpage or (page.pageSet.selected if page.pageSet else page)
            term.setPage(selected)
            return [layout]
