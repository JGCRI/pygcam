'''
.. codeauthor:: Richard Plevin

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
from ..error import PygcamException
from ..subcommand import SubcommandABC, clean_help

DefaultProperties = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<properties>
    <comment>TODO: add comments</comment>
    <entry key="queryFile">{queryFile}</entry>
</properties>
'''

class ModelInterfaceCommand(SubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : '''Run ModelInterface for the current project.'''}

        super(ModelInterfaceCommand, self).__init__('mi', subparsers, kwargs, group='utils', label='MI')

    def addArgs(self, parser):
        parser.add_argument('-d', '--useDefault', action='store_true',
                            help=clean_help('''Use the Main_Queries.xml file from the GCAM
                            reference workspace.'''))
        parser.add_argument('-g', '--glimpse', action='store_true',
                            help=clean_help('''Use the GLIMPSE-ModelInterface rather than the standard one.'''))
        parser.add_argument('-u', '--updateProperties', action='store_true',
                            help=clean_help('''Update the "model_interface.properties" file in the directory
                            indicated by config var file GCAM.QueryDir so it refers to the query file
                            indicated by config var GCAM.MI.QueryFile, or if this does not refer
                            to an existing file, by var GCAM.MI.RefQueryFile.'''))
        parser.add_argument('-q', '--queryFile',
                            help=clean_help('''Specify the XML file to read query definitions from.'''))
        return parser

    def run(self, args, tool):
        import os
        from ..config import getParam
        from ..file_utils import pushd
        from ..log import getLogger
        from ..xmlEditor import xmlEdit
        from ..utils import shellCommand

        _logger = getLogger(__name__)

        if args.queryFile:
            queryFile = args.queryFile
        else:
            queryFile = (getParam('GCAM.MI.RefQueryFile') if args.useDefault
                         else  getParam('GCAM.MI.QueryFile'))

        if not os.path.lexists(queryFile):
            raise PygcamException(f"Query file '{queryFile}' does not exist")

        queryDir = getParam('GCAM.QueryDir')

        propFile = 'model_interface.properties'

        with pushd(queryDir):
            # Create the default file if none exists
            if not os.path.lexists(propFile):
                with open(propFile, 'w') as f:
                    text = DefaultProperties.format(queryFile=queryFile)
                    f.write(text)

            # Update the file if so requested
            if args.updateProperties:
                pairs = [('//entry[@key="queryFile"]', queryFile)]
                xmlEdit(propFile, pairs, useCache=False)

            # run ModelInterface
            if args.glimpse:
                cmd = getParam('GLIMPSE.MI.Command')
                _logger.debug('GLIMPSE.MI.Command: %s', cmd)

            else:
                cmd = getParam('GCAM.MI.Command')

            _logger.debug(cmd)
            shellCommand(cmd, shell=True, raiseError=True)


PluginClass = ModelInterfaceCommand
