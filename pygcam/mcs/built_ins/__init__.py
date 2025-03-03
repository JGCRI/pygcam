from .addexp_plugin import AddExpCommand
from .analyze_plugin import AnalyzeCommand
from .cluster_plugin import ClusterCommand
from .defresults_plugin import DefResultsCommand
from .delsim_plugin import DelSimCommand
from .discrete_plugin import DiscreteCommand
from .engine_plugin import EngineCommand
from .explore_plugin import ExploreCommand
from .gensim_plugin import GensimCommand
from .ippsetup_plugin import IppSetupCommand
from .iterate_plugin import IterateCommand
from .moirai_plugin import MoiraiCommand
from .parallelPlot_plugin import ParallelPlotCommand
from .runsim_plugin import RunSimCommand

MCSBuiltins = [AddExpCommand, AnalyzeCommand, ClusterCommand,
               DelSimCommand, DefResultsCommand, DiscreteCommand,
               EngineCommand, ExploreCommand, GensimCommand,
               IppSetupCommand, IterateCommand, MoiraiCommand,
               ParallelPlotCommand, RunSimCommand]
