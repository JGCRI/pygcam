# Separate "high-level" utilities that imports from several modules, avoiding
# import cycles.
from .context import McsContext
from .mcsSandbox import McsSandbox
from .simulation import Simulation

def sim_and_sbx_from_context(ctx : McsContext, create=True):
    sim = Simulation.from_context(ctx)
    sbx = McsSandbox(ctx.scenario, sim=sim, projectName=ctx.projectName,
                     scenario_group=ctx.groupName, parent=ctx.baseline,
                     create_dirs=create)
    return sim, sbx

