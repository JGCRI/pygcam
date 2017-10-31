#!/usr/bin/env python

import dash
import dash_html_components as html
import flask
import requests

from pygcam.subcommand import SubcommandABC
from pygcam.tool import GcamTool
from pygcam.gui.widgets import Page, RootPage, PageSet
from pygcam.gui.terminal import Terminal
from pygcam.gui.actions import actionTable, getActionInstance

_actions = {}

# Action list is used by the GUI
def saveActions(cmd, actions):
    _actions[cmd] = actions

def getActions(cmd):
    return _actions.get(cmd)

def subcommandHelp(cmd):
    tool = GcamTool.getInstance(reload=True)
    cmds = tool.subparsers._choices_actions
    help = next((s.help for s in cmds if s.dest == cmd), '')
    return help

def actionsFromParser(cmd, parser):
    actions = getActions(cmd)
    if not actions:
        actions = map(lambda action: getActionInstance(cmd, action), parser._actions)
        actions = filter(None, actions)    # remove Nones
        saveActions(cmd, actions)

    return actions

def _subpage(app, cmd):
    subcmd = SubcommandABC.getInstance(cmd)
    if subcmd.guiSuppress:
        return None

    parser = subcmd.parser
    actions = actionsFromParser(cmd, parser)

    helpText = subcommandHelp(cmd)
    layout = html.Div(actionTable('Options for "%s"' % cmd, actions, helpText=helpText))
    return cmd, layout, actions

def commandGroupPage(app, group, default, label=None):
    cmds = GcamTool.pluginGroup(group, namesOnly=True)
    tups = [_subpage(app, cmd) for cmd in cmds]
    tups = filter(None, tups)   # eliminate suppressed subcmds

    pages = [Page(app, cmd, layout, actions=actions) for cmd, layout, actions in tups]
    pageSet = PageSet(group, pages, default)
    page = Page(app, group, None, label=(label or group.capitalize()), pageSet=pageSet)
    return page

def runPage(app):
    cmd = 'run'
    subcmd = SubcommandABC.getInstance(cmd)
    parser = subcmd.parser

    actions = actionsFromParser(cmd, parser)

    helpText = subcommandHelp(cmd)
    layout = html.Div(actionTable('Options for "%s"' % cmd, actions, helpText=helpText))
    page = Page(app, 'run', layout, actions=actions)
    return page

def projectPage(app):
    return commandGroupPage(app, 'project', 'new')

def mcsPage(app):
    return commandGroupPage(app, 'mcs', 'runsim', label='MCS')

def utilitiesPage(app):
    return commandGroupPage(app, 'utils', 'mi', label='Utilities')

def settingsPage(app):
    tool = GcamTool.getInstance()
    cmd = 'globalArgs'
    actions = actionsFromParser(cmd, tool.parser)

    layout = html.Div(actionTable('Global arguments', actions))
    page = Page(app, cmd, layout, label='Global args', actions=actions)
    return page


def driver(args):
    from pkg_resources import resource_string, resource_filename

    app = dash.Dash(csrf_protect=False)
    app.config['suppress_callback_exceptions'] = True

    serve_locally = True

    if serve_locally:
        # app.css.config.serve_locally = True
        # app.scripts.config.serve_locally = True

        #
        # Modified from: https://community.plot.ly/t/how-do-i-use-dash-to-add-local-css/4914/2
        #
        files = ('stylesheet.css', 'googlefonts.css', 'terminal_scroller.js')
        map_to_remote = {'googlefonts.css': "https://fonts.googleapis.com/css?family=Dosis:regular,semi-bold|Lato"}

        @app.server.route('/static/<path:path>')
        def serve_static(path):
            print('Serving "%s"' % path)

            # Serve only known files
            if not path in files:
                raise Exception('Unknown static file: "{}"'.format(path))

            url = map_to_remote.get(path)
            if url:
                # Download content from corresponding remote URL
                content = requests.get(url).content
            else:
                # Grab files from the gui/static folder in the pygcam package
                resource_path = 'gui/static/' + path
                content = resource_string('pygcam', resource_path)

            mimetype = "text/css" if path.endswith('.css') else "text/javascript"
            response = flask.Response(content, mimetype=mimetype)

            return response

        for filename in files:
            arg_dict = {'external_url' : '/static/' + filename}

            if filename.endswith('.css'):
                app.css.append_css(arg_dict)
            else:
                app.scripts.append_script(arg_dict)
    else:
        # this version uses external files...
        app.scripts.append_script({'external_url': 'https://codepen.io/plevin/pen/MvpeNV.js'})
        app.css.append_css({"external_url": "https://fonts.googleapis.com/css?family=Dosis:regular,semi-bold|Lato"})
        app.css.append_css({"external_url": "https://codepen.io/plevin/pen/MvpeNV.css"})

    debug = args.debug
    term = Terminal(toConsole=True)

    pages = [runPage(app), projectPage(app), mcsPage(app), utilitiesPage(app), settingsPage(app)]
    RootPage(app, term, pages)

    term.registerCallbacks(app)
    app.run_server(debug=debug)

if __name__ == '__main__':
    driver()
