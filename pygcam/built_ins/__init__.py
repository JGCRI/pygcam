from .chart_plugin import ChartCommand
from .config_plugin import ConfigCommand
from .diff_plugin import DiffCommand
from .gcam_plugin import GcamCommand
from .gui_plugin import GUICommand
from .init_plugin import InitCommand
from .mcs_plugin import MCSCommand
from .mi_plugin import ModelInterfaceCommand
from .new_plugin import NewProjectCommand
from .protect_plugin import ProtectLandCommand
from .query_plugin import QueryCommand
from .res_plugin import RESCommand
from .run_plugin import RunCommand
from .sandbox_plugin import SandboxCommand
from .setup_plugin import SetupCommand
from .compare_plugin import CompareCommand

BuiltinSubcommands = [ChartCommand, CompareCommand, ConfigCommand, DiffCommand,
                      GcamCommand, GUICommand, InitCommand, MCSCommand,
                      ModelInterfaceCommand, NewProjectCommand, ProtectLandCommand,
                      QueryCommand, RESCommand, RunCommand, SandboxCommand, SetupCommand]
