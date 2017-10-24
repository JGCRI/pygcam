#!/usr/bin/env python

import dash
import dash_html_components as html
from pygcam.tool import GcamTool
from pygcam.gui.widgets import Page, RootPage, PageSet
from pygcam.gui.terminal import Terminal
from pygcam.gui.actions import actionTable, getActionInstance

def subcommandHelp(subcmd):
    tool = GcamTool.getInstance(reload=True)
    subcmds = tool.subparsers._choices_actions
    help = next((s.help for s in subcmds if s.dest == subcmd), '')
    return help

# TBD: Have guiInfo element for this to push it back onto the subcommands
def smartCaps(s):
    return s.upper() if s in ('mi', 'mcs', 'gcam') else s.capitalize()

def actionsFromParser(subcmd, parser):
    actions = map(lambda action: getActionInstance(subcmd, action), parser._actions)
    return filter(None, actions)    # remove Nones


def _subpage(app, subcmd):
    tool = GcamTool.getInstance()
    parser = tool.subparsers.choices[subcmd]
    actions = actionsFromParser(subcmd, parser)

    helpText = subcommandHelp(subcmd)
    layout = html.Div(actionTable('Options for "%s"' % subcmd, actions, helpText=helpText))
    return subcmd, layout, actions

def commandGroupPage(app, group, default, label=None):
    subcmds = GcamTool.pluginGroup(group, namesOnly=True)
    tups  = [_subpage(app, s) for s in subcmds]
    pages = [Page(app, s, layout, label=smartCaps(s), actions=actions) for s, layout, actions in tups]
    pageSet = PageSet(group, pages, default)
    page = Page(app, group, None, label=label or smartCaps(group), pageSet=pageSet)
    return page

def runPage(app):
    tool = GcamTool.getInstance()
    subcmd = 'run'
    parser = tool.subparsers.choices[subcmd]
    actions = actionsFromParser(subcmd, parser)

    helpText = subcommandHelp(subcmd)
    layout = html.Div(actionTable('Options for "%s"' % subcmd, actions, helpText=helpText))
    page = Page(app, 'run', layout, label='Run', actions=actions)
    return page


def projectPage(app):
    return commandGroupPage(app, 'project', 'new')

def mcsPage(app):
    return commandGroupPage(app, 'mcs', 'runsim')

def utilitiesPage(app):
    return commandGroupPage(app, 'utils', 'mi', label='Utilities')

def settingsPage(app):
    tool = GcamTool.getInstance()
    subcmd = 'settings'
    actions = actionsFromParser(subcmd, tool.parser)

    layout = html.Div(actionTable('Global arguments', actions))
    page = Page(app, subcmd, layout, label='Global args', actions=actions)
    return page


def driver(args):
    app = dash.Dash(csrf_protect=False)
    # app.config.supress_callback_exceptions = True
    app.css.append_css({"external_url": "https://codepen.io/plevin/pen/MvpeNV.css"})

    debug = args.debug
    term = Terminal()

    pages = [runPage(app), projectPage(app), mcsPage(app), utilitiesPage(app), settingsPage(app)]
    root = RootPage(app, term, pages)

    term.registerCallbacks(app)
    app.run_server(debug=debug)

if __name__ == '__main__':
    driver()
