import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from six.moves import shlex_quote

from pygcam.log import getLogger

_logger = getLogger(__name__)


class ActionInfo(object):
    """
    Converts argparse "actions" into HTML widgets.
    """
    ignoredActions = ('_VersionAction', '_HelpAction', '_SubParsersAction')

    def __init__(self, pageId, action, default=None):
        self.action = action
        self.actionClass = type(action).__name__

        opt_strings = action.option_strings
        self.name = ', '.join(opt_strings) if opt_strings else action.dest

        # For constructing command line
        self.option = opt_strings[0] if opt_strings else action.dest
        self.default = default
        self.pageId = pageId
        self.widget = None
        self.value  = None   # set in generated callback
        self.checkDefaultFunc = None # function to decide whether to render option (i.e., not default value)

        t = action.type
        if t == str:
            self.dataType = 'text'
        elif t in (int, float):
            self.dataType = t.__name__
        else:
            self.dataType = 'text'

        self.display = self.actionClass not in self.ignoredActions and self.name != '--VERSION'

        self.layout = None

    def __str__(self):
        return "<ActionInfo %s %s>" % (self.actionClass, self.name)

    def setPageId(self, id):
        self.pageId = id

    def getWidgetId(self):
        return "%s-%s" % (self.pageId, self.action.dest)

    def getWidgetSinkId(self):
        return "_%s-storage_" % self.getWidgetId()

    def generateCallback(self, app):
        """
        Generate a callback function to set this ActionInfo state when the corresponding
        HTML widget is changed. This allows us to interrogate ActionInfo classes for values.

        :param app: a Dash app instance
        :return: none
        """
        inputId  = self.getWidgetId()
        outputId = self.getWidgetSinkId()

        def saveChange(value):
            _logger.debug("Setting value of %s in %s to %r" % (inputId, id(self), value))
            self.value = value
            return value

        _logger.debug("Generating default-setting callback for %s" % inputId)


        # install a callback to the function created above
        app.callback(Output(outputId, 'children'),
                     [Input(inputId, 'value')])(saveChange)

    def radio(self, options, default='', vertical=False):
        self.default = default
        id = self.getWidgetId()

        return dcc.RadioItems(
            id=id,
            options=[{'label': str(opt), 'value': opt} for opt in options],
            value=default if self.value is None else self.value,
            labelStyle={'display': 'block' if vertical else 'inline-block'})

    def input(self, default=None, placeholder='Enter a value...'):
        self.default = self.action.default if default is None else default
        value = self.default if self.value is None else self.value

        if not value and self.action.metavar:
            placeholder = self.action.metavar

        id = self.getWidgetId()
        return dcc.Input(id=id, placeholder=placeholder, type=self.dataType,
                         value=value, className='option')

    def render(self):
        """
        Render an argparse option as HTML
        """
        Y = 'Yes'
        N = 'No'

        actionClass = self.actionClass

        if actionClass == '_StoreTrueAction':
            widget = self.radio([Y, N], default=N)

        elif actionClass == '_StoreFalseAction':
            widget = self.radio([Y, N], default=Y)

        elif actionClass == '_StoreAction':
            choices = self.action.choices
            if choices:
                widget = self.radio(choices, default=self.action.default, vertical=True)
            else:
                widget = self.input(default=self.action.default)

        elif actionClass == '_AppendAction':
            widget = self.input(default=self.action.default)

        elif actionClass == 'ParseCommaList':
            widget = self.input(default=self.action.default)

        else:
            widget = html.P("%s: unknown action type %s" % (self.name, actionClass))

        self.widget = widget

        name = self.name
        if self.action.required:
            name = html.Span(name + '*', className='required')

        help = "(%s) " % self.dataType if self.dataType != 'text' else ''
        help += (self.action.help or '')

        widgetSinkId = self.getWidgetSinkId()

        layout = html.Tr(children=[
            html.Td(name,   className='lined', style={'width': 150}),
            html.Td(widget, className='lined', style={'width': 200}),
            html.Td(help,   className='lined'),

            # invisible sink to store value just so callback is legit
            html.Div(id=widgetSinkId, style={'display': 'none'})
        ], className='cmd')

        self.layout = layout
        return layout

    def cmdlineArg(self):
        """
        Generate the command-line argument corresponding to the user's data entry, or None if
        the default value is set.
        """
        if self.value is None or self.value == self.default:
            return None

        return self._cmdlineArg()

    def _cmdlineArg(self):
        arg = None

        if self.actionClass in ('_StoreTrueAction', '_StoreFalseAction'):
            arg = self.option   # just the flag itself

        elif self.option[0] not in ('-', '+'):
            arg = shlex_quote(self.value)   # positional; just the value

        elif self.value:
            arg = "%s %s" % (self.option, shlex_quote(self.value))

        return arg

class StoreAction(ActionInfo):
    def __init__(self, pageId, action, default):
        super(StoreAction, self).__init__(pageId, action, default)

class StoreConst(ActionInfo):
    def __init__(self, pageId, action, const, default):
        super(StoreConst, self).__init__(pageId, action, default)
        self.const = const

class AppendAction(ActionInfo):
    def __init__(self, pageId, action, default):
        super(AppendAction, self).__init__(pageId, action, default)


def getActionInstance(pageId, action):
    """
    Factory function to create action subclasses
    """
    actionClass = type(action).__name__

    if actionClass in ('_StoreTrueAction', '_StoreFalseAction'):
        obj = StoreConst(pageId, action, const=action.const, default=action.default)

    elif actionClass in ('_StoreAction', 'ParseCommaList'):
        obj = StoreAction(pageId, action, default=action.default)

    elif actionClass == '_AppendAction':
        obj = AppendAction(pageId, action, default=action.default)

    elif actionClass in ActionInfo.ignoredActions:
        obj = None

    else:
        raise Exception('Unrecognized widget action class "%s"' % action)

    return obj


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
