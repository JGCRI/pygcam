import dash
import flask
import requests

from pygcam.config import usingMCS
from pygcam.log import getLogger
from pygcam.subcommand import SubcommandABC
from pygcam.tool import GcamTool
from pygcam.gui.widgets import Page, PageSet, RootPage, GlobalArgsPage
from pygcam.gui.terminal import Terminal

_logger = getLogger(__name__)

def _showInGUI(cmd):
    subcmd = SubcommandABC.getInstance(cmd)
    return not subcmd.guiSuppress

def commandGroupPage(app, group, default, label=None):
    cmds = GcamTool.pluginGroup(group, namesOnly=True)
    cmds = filter(_showInGUI, cmds)   # eliminate suppressed subcmds

    pages = [Page(app, cmd) for cmd in cmds]
    pageSet = PageSet(group, pages, default)
    page = Page(app, group, label=label, pageSet=pageSet)
    return page

def driver(args):
    from pkg_resources import resource_string

    app = dash.Dash(__name__, csrf_protect=False)
    app.config['suppress_callback_exceptions'] = True

    googleFonts = "https://fonts.googleapis.com/css?family=Dosis:regular,semi-bold|Lato"

    serve_locally = True

    if serve_locally:
        # app.css.config.serve_locally = True
        # app.scripts.config.serve_locally = True

        files = ('stylesheet.css', 'googlefonts.css', 'terminal_scroller.js')
        map_to_remote = {'googlefonts.css': googleFonts}

        @app.server.route('/assets/<path>')
        def serve_static(path):
            _logger.debug('Serving "%s"' % path)

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

            content = content.decode('utf-8')
            mimetype = "text/css" if path.endswith('.css') else "text/javascript"
            response = flask.Response(content, mimetype=mimetype)

            return response

        for filename in files:
            arg_dict = {'external_url' : '/assets/' + filename}

            if filename.endswith('.css'):
                app.css.append_css(arg_dict)
            else:
                app.scripts.append_script(arg_dict)
    else:
        # this version uses external files...
        app.css.append_css({"external_url": googleFonts})
        app.css.append_css({"external_url": "https://codepen.io/plevin/pen/MvpeNV.css"})
        app.scripts.append_script({'external_url': 'https://codepen.io/plevin/pen/MvpeNV.js'})

    debug = args.debug
    term = Terminal(updateSeconds=1.5)

    pages = [Page(app, 'run'),
             commandGroupPage(app, 'project', 'new'),
             commandGroupPage(app, 'mcs', 'runsim', label='MCS') if usingMCS() else None,
             commandGroupPage(app, 'utils', 'mi', label='Utilities'),
             GlobalArgsPage(app)]

    RootPage(app, term, [page for page in pages if page])

    term.registerCallbacks(app)
    app.run_server(debug=debug)

if __name__ == '__main__':
    driver()
