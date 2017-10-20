#!/usr/bin/env python

import dash
import dash_html_components as html
from pygcam.tool import GcamTool
from pygcam.gui.widgets import Page, RootPage, PageSet, ActionInfo, actionTable, Terminal

def subcommandHelp(subcmd):
    tool = GcamTool.getInstance(reload=True)
    subcmds = tool.subparsers._choices_actions
    help = next((s.help for s in subcmds if s.dest == subcmd), '')
    return help

def smartCaps(s):
    return s.upper() if s in ('mi', 'mcs', 'gcam') else s.capitalize()

def subpage(subcmd):
    tool = GcamTool.getInstance()
    parser = tool.subparsers.choices[subcmd]
    actions = map(ActionInfo, parser._actions)
    helpText = subcommandHelp(subcmd)
    layout = html.Div(actionTable('Options for "%s"' % subcmd, actions, helpText=helpText))
    return layout

def runPage():
    tool = GcamTool.getInstance()
    subcmd = 'run'
    parser = tool.subparsers.choices[subcmd]
    actions = map(ActionInfo, parser._actions)
    helpText = subcommandHelp(subcmd)
    layout = html.Div(actionTable('Options for "%s"' % subcmd, actions, helpText=helpText))
    page = Page('run', layout, label='Run')
    return page

def commandGroupPage(group, default, label=None):
    subcmds = GcamTool.pluginGroup(group, namesOnly=True)
    pages = [Page(s, subpage(s), label=smartCaps(s)) for s in subcmds]
    pageSet = PageSet(group, pages, default)
    page = Page(group, None, label=label or smartCaps(group), pageSet=pageSet)
    return page

def projectPage():
    return commandGroupPage('project', 'new')

def mcsPage():
    return commandGroupPage('mcs', 'runsim')

def utilitiesPage():
    return commandGroupPage('utils', 'mi', label='Utilities')

def settingsPage():
    tool = GcamTool.getInstance()
    actions = map(ActionInfo, tool.parser._actions)
    layout = html.Div(actionTable('Global arguments', actions))
    page = Page('settings', layout, label='Global args')
    return page

def driver(args):
    app = dash.Dash(csrf_protect=False)
    # app.config.supress_callback_exceptions = True
    app.css.append_css({"external_url": "https://codepen.io/plevin/pen/MvpeNV.css"})

    test = False

    if test:
        import sys
        term = Terminal()
        app.layout = term.layout
        term.registerCallbacks(app)
        app.run_server(debug=args.debug)
        sys.exit(0)

    pages = [runPage(), projectPage(), mcsPage(), utilitiesPage(), settingsPage()]
    root = RootPage(app, pages)

    app.run_server(debug=True)

if __name__ == '__main__':
    driver()
