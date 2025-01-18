# Copyright (c) 2025  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

from ...log import getLogger
from .McsSubcommandABC import McsSubcommandABC

_logger = getLogger(__name__)


class DefResultsCommand(McsSubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : '''Delete all rows from 'output' and 'outvalue' tables in sqlite 
            database and redefine model outputs from the current results.xml file. Copy the
            results.xml file to the MCS run directory.'''}
        super(DefResultsCommand, self).__init__('defresults', subparsers, kwargs)

    def addArgs(self, parser):
        return parser   # for auto-doc generation


    def run(self, args, tool):
        from ...config import getParam
        from ..database import getDatabase
        from ..sim_file_mapper import SimFileMapper
        from ..XMLResultFile import XMLResultFile

        db = getDatabase()
        db.deleteOutputs()
        XMLResultFile.addOutputs()

        project_name = getParam("GCAM.ProjectName")
        mapper = SimFileMapper(project_name=project_name)
        mapper.copy_app_xml_files(results_only=True)
