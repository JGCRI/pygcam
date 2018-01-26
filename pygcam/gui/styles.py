Skin1 = 1
Skin2 = 2

Skin = Skin1

#
# Fonts
#
LatoFont  = 'Lato,arial,sans-serif'
DosisFont = 'Dosis,arial,sans-serif'
LabelFont = LatoFont

FontDict = {
    'PlotText' : LatoFont,
    'LabelFont': LatoFont,
    'HelpText' : DosisFont,
}

def getFont(name):
    return FontDict[name]

#
# Colors
#
_pageBgColor         = '#EEEEEE'
_plotBgColor         = '#191A1A'
_plotPaperBgColor    = '#020202'
_plotTextColor       = '#CCCCCC'
_widgetBgColor       = '#c5e8ed'

_widgetBgLight       = '#DAEAE2'
_pageBgLight         = 'whitesmoke'
_plotBgLight         = 'whitesmoke'
_plotPaperBgLight    = _widgetBgLight
_plotTextLight       = '#020202'


_helpTextColor       = '#888888'

_distBarsActiveColor   = 'rgb(192, 255, 245)'
_distBarsInactiveColor = 'rgba(192, 255, 245, 0.2)'

_distBarsActiveLight   = 'seagreen' # RGB(46, 139, 87)
_distBarsInactiveLight = 'rgba(46, 139, 87, 0.3)'

#
# Colors
#
ColorDict = {
    'PageBg' : _pageBgColor,
    'ChooserBgColor': _widgetBgColor,
    'DistBarsActive': _distBarsActiveColor,
    'DistBarsInactive' : _distBarsInactiveColor,
    'PaperBg' : _plotPaperBgColor,
    'PlotBg' : _plotBgColor,
    'PlotText' : _plotTextColor,
    'ResetButton' : _distBarsActiveColor,
    'ResetButtonText' : _plotPaperBgColor,
    'TornadoPlotBar' : 'goldenrod',
    'TornadoPlotLine' : _plotTextColor,
    'HelpText' : _helpTextColor,
    'MeanLineColor': 'red',
    'MedianLineColor': 'orange',
    'KDE': 'gold',
    'ScatterPoints': _distBarsActiveColor,
}

ColorDict2 = {
    'PageBg' : _pageBgLight,
    'ChooserBgColor': _widgetBgLight,
    'DistBarsActive': _distBarsActiveLight,
    'DistBarsInactive' : _distBarsInactiveLight,
    'PaperBg' : _widgetBgLight,
    'PlotBg' : _plotBgLight,
    'PlotText' : _plotTextLight,
    'ResetButton' : _distBarsActiveLight,
    'ResetButtonText' : 'white', #_plotPaperBgLight,
    'TornadoPlotBar' : _distBarsActiveLight,
    'TornadoPlotLine' : _plotTextLight,
    'HelpText' : _helpTextColor,
    'MeanLineColor': 'darkred',
    'MedianLineColor': 'navy',
    'KDE': 'goldenrod',
    'ScatterPoints': _distBarsActiveLight,
}

PlotMargin = dict(l=35, r=35, t=70, b=30, pad=4)
PlotMarginWithXTitle = dict(l=35, r=35, t=70, b=40, pad=4)

def getColor(name):
    d = ColorDict if Skin == Skin2 else ColorDict2
    return d[name]

#
# Styles
#
StyleDict = {
    'Page' : {
        'text-align': 'center',
        'background-color': getColor('PageBg'),
    },
    'Label' : {
        'font-family': LabelFont,
        'font-size'  : '14px',
        'font-weight': 'bold',
        'margin-top' : 20,
    },
    'HelpText' : {
        'font-family': getFont('HelpText'),
        'font-size': 11,
        'font-style': 'italic',
        'color': getColor('HelpText'),
    },
    'Chooser' : {
        'margin-right': 'auto',
        'margin-left' : 'auto',
    },
    'AutoMargins': {
        'margin-right': 'auto',
        'margin-left': 'auto',
    },
    'Button' : {
        'color'     : getColor('ResetButtonText'),
        'font-size' : 10,
        'box-shadow': '0 6px 10px 0 rgba(0, 0, 0, 0.24), 0 17px 50px 0 rgba(0, 0, 0, 0.19)',
        'border'    : 'none',
        'padding'   : '2px 4px',
        'text-align': 'center',
        'background-color': getColor('ResetButton'),
        'text-decoration' : None,
    },
    'PlotMargin': PlotMargin,
    'PlotMarginWithXTitle' : PlotMarginWithXTitle,

    'Plot' : dict(
        autosize=True,
        height=450,
        width=550,
        font=dict(family=getFont('PlotText'),
                  color=getColor('PlotText')),
        titlefont=dict(color=getColor('PlotText'),
                       size='16'),
        margin=PlotMargin,
        hovermode="closest",
        plot_bgcolor=getColor('PlotBg'),
        paper_bgcolor=getColor('PaperBg'),
        legend=dict(font=dict(size=10), orientation='h', bgcolor=getColor('PlotBg')),
        title='',
    ),
}

def getStyle(name):
    return StyleDict[name]

def updateStyle(style, **kwargs):
    """Update a copy of a dict or the dict for the given style"""
    if not isinstance(style, dict):
        style = getStyle(style)    # look up the style by name

    style = style.copy()
    style.update(**kwargs)
    return style
