# Copyright (c) 2016-2022  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

import os

from ...config import getParam
from ...constants import McsMode
from ...log import getLogger
from ...project import Project

from ..sim_file_mapper import SimFileMapper
from ..util import saveDict

from .McsSubcommandABC import McsSubcommandABC, clean_help

_logger = getLogger(__name__)


def genFullFactorialData(trials, paramFileObj):
    from numpy import linspace
    import pandas as pd
    from itertools import product
    from ..error import PygcamMcsUserError

    # any of the discrete distributions
    supported_distros = ['Constant', 'Binary', 'Integers', 'Grid', 'Sequence']

    N = 1        # the number of trials req'd for full factorial
    var_names = []    # variable names
    var_values = []   # variable values

    for elt in paramFileObj.tree.iterfind('//Parameter'):
        name = elt.get('name')
        distElt = elt.find('Distribution')
        distSpec = distElt[0]   # should have only one child as per schema
        distName = distSpec.tag

        # These 3 distro forms specify min and max values, which we use with SALib
        if distName not in supported_distros:
            raise PygcamMcsUserError("Found '{}' distribution; must be one of {} for use with SALib.".format(distName, supported_distros))

        # Count the elements in each discrete distro
        attrib = distSpec.attrib

        if distName == 'Constant':
            values = [float(attrib['value'])]
            count = 1

        elif distName == 'Binary':
            values = [0, 1]
            count = 2

        elif distName == 'Integers':
            # <Integers min='1' max='3'>
            min   = int(attrib['min'])
            max   = int(attrib['max'])
            count = max - min + 1
            values = list(range(min, max + 1))

        elif distName == 'Grid':
            # <Grid min=1 max=10 count=5>
            min   = int(attrib['min'])
            max   = int(attrib['max'])
            count = int(attrib['count'])
            values = linspace(min, max, count)

        elif distName == 'Sequence':
            # <Sequence values="1, 2, 3">
            v_str = attrib['values']
            values = [float(item) for item in v_str.split(',')]
            count = len(values)

        else:
            raise PygcamMcsUserError(f"Distribution name '{distName}' is not allowed with full factorial")

        var_names.append(name)
        var_values.append(values)
        N *= count

    # User can specify exact multiples of N trials
    if trials % N != 0:
        raise PygcamMcsUserError(f"Trial count {trials} is not an exact multiple of the number of full-factorial combinations ({N})")

    inputsDF = pd.DataFrame(list(product(*var_values)), columns=var_names)
    return inputsDF


def genTrialData(mapper : SimFileMapper, paramFileObj, method):
    """
    Generate the given number of trials for the given simId, using the objects created
    by parsing parameters.xml. Return a DataFrame of values.
    """
    from pandas import DataFrame
    from ..error import PygcamMcsUserError
    from ..distro import linkedDistro
    from ..LHS import lhs, lhsAmend
    from ..XMLParameterFile import XMLRandomVar, XMLCorrelation

    trials = mapper.trial_count

    rvList = XMLRandomVar.getInstances()

    linked = [obj for obj in rvList if obj.param.dataSrc.isLinked()]

    if method == 'montecarlo':
        # legacy Monte Carlo method. Supporting numerous distributions and correlations.

        corrMatrix = XMLCorrelation.corrMatrix()

        # TBD: this is currently broken. Only "shared" RVs are supported with the DataFrame
        # TBD: approach since a Parameter can have multiple RVs which appear as separate
        # TBD: data columns. This is ok for the current analysis, but needs to be rewritten
        # TBD: on integration with pygcam. (getName() will fail on XMLVariable instances)

        paramNames = [obj.getParameter().getName() for obj in rvList]
        trialData = lhs(rvList, trials, corrMat=corrMatrix, columns=paramNames, skip=linked)

    elif method == 'full-factorial':
        trialData = genFullFactorialData(trials, paramFileObj)
    else:
        raise PygcamMcsUserError(f"'{method}' is not a supported method of simulation data generation")

    linkedDistro.storeTrialData(trialData)  # stores trial data in class so its ppf() can access linked values
    lhsAmend(trialData, linked, trials, shuffle=False)

    if method in ('montecarlo', 'full-factorial'):
        mapper.write_trial_data_file(trialData)

    df = DataFrame(data=trialData)
    return df


def saveTrialData(mapper : SimFileMapper, df, start=0):
    """
    Save the trial data in `df` to the SQL database, for the given sim_id.
    """
    from ..database import getDatabase
    from ..XMLParameterFile import XMLRandomVar

    trials = df.shape[0]

    # Delete all Trial entries for this sim_id and this range of trialNums
    db = getDatabase()

    paramValues = []

    for trial in range(trials):
        trialNum = trial + start

        # Save all RV values to the database
        instances = XMLRandomVar.getInstances()
        for var in instances:
            varNum = var.getVarNum()
            param = var.getParameter()
            pname = param.getName()
            value = df[pname][trial]
            paramId = db.getParamId(pname)
            paramValues.append((trialNum, paramId, value, varNum))

    sim_id = mapper.sim_id

    # Write the tuples (sim_id, trialNum, paramId, value) to the database
    db.saveParameterValues(sim_id, paramValues)

    # SALib methods may not create exactly the number of trials requested,
    # so we update the database to set the record straight.
    db.updateSimTrials(sim_id, trials)
    _logger.info(f'Saved {trials} trials for sim_id {sim_id}')

# Deprecated? Or may need to be called by runsim
def runStaticSetup(mapper : SimFileMapper, project : Project):
    """
    Run the --staticOnly setup in the MCS copy of the workspace, for all scenarios.
    This is called from gensim, so we fake the "context" for trial 0, since all
    trials have local-xml symlinked to the simulation's local-xml.
    """
    # TBD: not sure the comment above remains accurate when running the data system

    from ... import tool
    from ..error import GcamToolError

    projectName = project.projectName
    scenarios = project.getKnownScenarios()
    scenarios_arg = ','.join(scenarios)

    # useGroupDir = project.scenarioGroup.useGroupDir
    # groupSubdir = groupName if useGroupDir else ''
    #
    # create symlinks from all the scenarios' local-xml dirs to shared one
    # under {projectName}/Workspace
    # sandboxDir = mapper.sandbox_dir
    #
    # wsXmlDir = pathjoin(runWorkspace, LOCAL_XML_NAME, create=True)
    #
    # for scenario in scenarios:
    #     dirname = pathjoin(sandboxDir, scenario, create=True)
    #     linkname  = pathjoin(dirname, LOCAL_XML_NAME)
    #     symlink(wsXmlDir, linkname)

     # N.B. RunWorkspace for gensim is pygcam's RefWorkspace
    toolArgs = ['--projectName', projectName,
                '--mcs', McsMode.GENSIM.value,
                'run',
                '--step', 'setup2',    # TBD: switch back to "setup" when pygcam 2.0 is released
                '--scenario', scenarios_arg,
                '--sandboxDir', mapper.get_sim_local_xml()]

    group = mapper.get_scenario_group()
    if group:
        toolArgs.extend(['-g', group])

    command = 'gt ' + ' '.join(toolArgs)
    _logger.debug(f'Running: {command}')
    status = tool.main(argv=toolArgs, mapper=mapper, raiseError=True)

    if status != 0:
        raise GcamToolError(f'"{command}" exited with status {status}')

    return status

def genSimulation(mapper : SimFileMapper, data_file, method):
    '''
    Generate a simulation based on the given parameters.
    '''
    from ..database import getDatabase
    from ..XMLParameterFile import XMLParameterFile
    from ...xmlScenario import XMLScenario

    # TBD: this structure needs to be reconsidered
    # Add symlink to workspace's input dir so we can find XML files using rel paths in config files
    # symlink(mapper.sandbox_workspace_input_dir, mapper.sim_input_dir)
    # symlink(mapper.workspace_local_xml, mapper.sim_local_xml)

    project = Project.readProjectFile(mapper.project_name, groupName=mapper.scenario_group)

    # TBD: Should not be needed here. Setup must be run *after* datasystem runs (optional)
    #  to generate the base XML files the setup operates on.
    # Run static setup for all scenarios in the given group
    # runStaticSetup(mapper, project)

    group_name = mapper.scenario_group or project.scenarioSetup.defaultGroup

    xml_scenario = XMLScenario.get_instance(mapper.get_scenarios_file())
    scenarioNames = xml_scenario.scenariosInGroup(group_name)
    baseline = xml_scenario.baselineForGroup(group_name)

    # Copy the project's parameters.xml and results.xml files to {simDir}/app-xml
    mapper.copy_app_xml_files()

    paramFileObj = XMLParameterFile(mapper.get_param_file())

    # TBD: Do we really need to load input files at this point? Commenting this out seems ok.
    # context = McsContext(projectName=mapper.project_name, simId=mapper.sim_id, groupName=group_name)
    # paramFileObj.loadInputFiles(mapper, context, scenarioNames, writeConfigFiles=True)

    # Define the experiments (scenarios) in the database
    db = getDatabase()
    db.addExperiments(scenarioNames, baseline, mapper.get_scenarios_file())

    if not mapper.trial_count:
        _logger.warn("Simulation meta-data has been copied.")
        if not data_file:
            return

    paramFileObj.generateRandomVars()

    if data_file:
        from pandas import read_table
        df = read_table(data_file, sep=',', index_col='trialNum')
        rows = df.shape[0]
        _logger.info(f"Loaded data for {rows} trials from {data_file}")
    else:
        _logger.info(f"Generating {mapper.trial_count} trials to {mapper.sim_dir}")
        df = genTrialData(mapper, paramFileObj, method)

    # Save generated values to the database for post-processing
    saveTrialData(mapper, df)

def _simplifyDistro(dataSrc):
    '''
    Convert uniform and triangle distros declared with logfactor, factor, or range to
    min/mode/max format for documentation purposes.
    '''
    name = dataSrc.distroName
    if not name in ('triangle', 'uniform'):
        return

    argDict = dataSrc.argDict
    keys = list(argDict.keys())

    if len(keys) > 1:
        return

    key = keys[0]
    value = argDict[key]
    del argDict[key]

    if name == 'triangle':
        if key == 'factor':
            argDict['min']  = 1 - value
            argDict['mode'] = 1
            argDict['max']  = 1 + value

        elif key == 'logfactor':
            argDict['min']  = round(1.0/value, 3)
            argDict['mode'] = 1
            argDict['max']  = value

        elif key == 'range':
            argDict['min']  = -value
            argDict['mode'] = 0
            argDict['max']  = value

    elif name == 'uniform':
        if key == 'factor':
            argDict['min']  = 1 - value
            argDict['max']  = 1 + value

        elif key == 'logfactor':
            argDict['min']  = round(1.0/value, 3)
            argDict['max']  = value

        elif key == 'range':
            argDict['min']  = -value
            argDict['max']  = value


# Deprecated? Unused. Might have been useful from jupyter notebooks?
# def _plot_values(values, paramName, plotsDir, bins=250, context='paper'):
#     import seaborn as sns
#
#     outfile = f"{plotsDir}/{paramName}.pdf"
#
#     with sns.plotting_context(context):
#         ax = sns.distplot(values, kde=False, bins=bins, color='navy')
#         fig = ax.get_figure()
#         fig.savefig(outfile, bbox_inches='tight')
#         return ax

# TBD: move this where gensim writes out the modified XML
# from ...project import Project
# from ...XMLConfigFile import XMLConfigFile
# from ...XMLFile import XMLFile
#
# projectName = getParam('GCAM.ProjectName')
# project = Project.readProjectFile(projectName, groupName=args.groupName)
# groupName  = args.groupName or project.scenarioSetup.defaultGroup
#
# ctx = McsContext(simId=args.simId, groupName=groupName, scenario=baseline)
# configFile = XMLConfigFile(ctx)
#
# sandboxDir = getParam('GCAM.SandboxDir')
# exe_dir = pathjoin(sandboxDir, baseline, 'exe', abspath=True)

# comp_name = p.parent.getComponentName()     # either *.xml or the name of a config file component
# xml_path = configFile.get_component_pathname(comp_name)
# with pushd(exe_dir):
#     xml_file_obj = XMLFile(xml_path) # loads target file
#
# tree = xml_file_obj.getTree()
# found = tree.xpath(xpath)
# count = len(found)
#
# if plotsDir:
#     # TBD: run query and produce array of values
#     values = None
#     _plot_values(values, pname, plotsDir)


def _exportVars(paramFile, outputFile, plotsDir):
    import re
    from itertools import chain
    from ...file_utils import mkdirs
    from ..XMLParameterFile import XMLDistribution, XMLParameterFile, XMLDataFile

    if plotsDir:
        mkdirs(plotsDir)

    paramFileObj = XMLParameterFile(paramFile)
    params = list(chain.from_iterable(map(lambda x: x.parameters.values(), paramFileObj.inputFiles.values())))

    distDict = {p.name : p for p in params if isinstance(p.dataSrc, XMLDistribution)}

    def getDistStr(dataSrc, withArgNames=False):
        _simplifyDistro(dataSrc)
        # TBD: decide whether to include name arguments on Triangles or just tuple of values
        if withArgNames:
            argStr = ', '.join([f'{name}={value}' for name, value in dataSrc.argDict.items()])
        else:
            argStr = ', '.join([f'{value}' for _, value in dataSrc.argDict.items()])

        distroName = dataSrc.distroName.capitalize()
        distro = f'{distroName}({argStr})'
        return distro

    # Sort by name, within sorted categories
    tuples = [(p.category, pname, p) for pname, p in distDict.items()]
    sorted_params = sorted(tuples, key=lambda x: (x[0], x[1]))

    def clean(s):
        s = re.sub('^\s+', '', s)   # remove leading whitespace
        s = re.sub('\s+$', '', s)   #   and trailing whitespace
        s = re.sub('\s+', ' ', s)   # replace multiples with one space
        return s

    # Non-distribution (e.g., parameter files
    dataFileDict = {p.name : p for p in params if isinstance(p.dataSrc, XMLDataFile)}

    _logger.info(f"Writing '{outputFile}'")
    with open(outputFile, 'w', newline='') as f:
        import csv

        writer = csv.writer(f, dialect='unix')
        writer.writerow(['Category', 'Name', 'Distribution', 'Application', 'Description', 'XPath', 'Evidence', 'Rationale', 'Notes'])

        for category, pname, p in sorted_params:
            dist = getDistStr(p.dataSrc)
            modDict = p.dataSrc.modDict
            apply = modDict['apply']
            xpath = p.query.xpath if p.query else ''

            desc      = clean(p.desc)
            evidence  = clean(p.evidence)
            rationale = clean(p.rationale)
            notes     = clean(p.notes)

            writer.writerow([category, pname, dist, apply, desc, xpath, evidence, rationale, notes])

        for pname, p in dataFileDict.items():
            fname = p.dataSrc.filename
            notes = clean(p.notes)
            notes = f"{notes} {fname}" if notes else fname
            writer.writerow([p.category, pname, 'empirical', 'direct', clean(p.desc), p.query.xpath,
                             clean(p.evidence), clean(p.rationale), notes])


def driver(args):
    '''
    Generate a simulation. Do generic setup, then call genSimulation().
    '''
    from ...file_utils import removeTreeSafely
    from ..error import PygcamMcsUserError

    simId  = args.simId
    desc   = args.desc
    trials = args.trials

    if trials < 0:
        raise PygcamMcsUserError("Trials argument is required: must be an integer >= 0")

    mapper = SimFileMapper(project_name=args.projectName, scenario_group=args.group,
                           sim_id=args.simId, trial_count=trials,
                           param_file=args.paramFile)

    if args.exportVars:
        _exportVars(mapper.get_param_file(), args.exportVars, args.paramPlots)
        return

    if args.delete:
        removeTreeSafely(mapper.sandbox_dir, ignore_errors=False)

    if not os.path.exists(mapper.sandbox_workspace):
        mapper.copy_ref_workspace()

        if trials:
            mapper.create_database()

    # Called with trials == 0 when setting up a local run directory on /scratch
    if trials:
        # The simId can be provided on command line, in which case we need
        # to delete existing parameter entries for this app and simId.
        mapper.create_sim(desc=desc)

    genSimulation(mapper, args.dataFile, args.method)

    if trials:
        # Save a copy of the arguments used to create this simulation
        saveDict(vars(args), mapper.args_save_file)


class GensimCommand(McsSubcommandABC):

    def __init__(self, subparsers):
        kwargs = {'help' : 'Generate input files for simulations.'}
        super(GensimCommand, self).__init__('gensim', subparsers, kwargs)

    def addArgs(self, parser):
        parser.add_argument('--delete', action='store_true',
                            help=clean_help('''DELETE and recreate the simulation "run" directory.'''))

        parser.add_argument('-d', '--dataFile', type=str, default=None,
                            help=clean_help('Load the trial data from a CSV into the database. Useful for restoring data.'))

        parser.add_argument('-D', '--desc', type=str, default='',
                            help=clean_help('A brief (<= 256 char) description the simulation.'))

        parser.add_argument('-e', '--exportVars', default='', metavar="CSVFILE",
                            help=clean_help('''Export variable and distribution info in a tab-delimited file with 
                                the given name and exit.'''))

        parser.add_argument('-g', '--group', default='',
                            help=clean_help('''The name of a scenario group to process.'''))

        methods = ['montecarlo', 'full-factorial']
        parser.add_argument('-m', '--method', choices=methods,
                            default='montecarlo',
                            help=clean_help('''Use the specified method to generate trial data. Default is "montecarlo".
                                Note that in the only supported distribution types for the 'full-factorial' method, are: 
                                Constant, Binary, Integer, Grid, and Sequence'''))

        # TBD: drop this since it can be set from .pygcam.cfg and runsim has no method to process it
        paramFile = getParam('MCS.ProjectParametersFile')
        parser.add_argument('-p', '--paramFile', default=None,
                            help=clean_help(f'''Specify an XML file containing parameter definitions.
                            Defaults to the value of config parameter MCS.ProjectParametersFile
                            (currently '{paramFile}')'''))

        parser.add_argument('-P', '--paramPlots', default='', metavar="DIRECTORY",
                            help=clean_help('''Export plots of values returned by XPath queries for each parameter 
                                defined by --paramFile or config variable MCS.ProjectParametersFile.'''))

        runRoot = getParam('MCS.SandboxRoot')
        parser.add_argument('-r', '--runRoot', default=None,
                            help=clean_help(f'''Root of the run-time directory for running user programs. Defaults to
                            value of config parameter MCS.SandboxRoot (currently '{runRoot}')'''))

        parser.add_argument('-s', '--simId', type=int, default=1,
                            help=clean_help('The id of the simulation. Default is 1.'))

        # TBD: make this '-N', '--num-trials' to differentiate from runsim's -t / --trials (which is a trial string)
        parser.add_argument('-t', '--trials', type=int, default=-1,
                            help=clean_help('''The number of trials to create for this simulation (REQUIRED). If a
                            value of 0 is given, scenario setup is performed, scenario names are added to 
                            the database, and meta-data is copied, but new trial data is not generated.'''))

        return parser   # for auto-doc generation


    def run(self, args, _tool):
        driver(args)
