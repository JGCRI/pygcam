# Copyright (c) 2016  Richard Plevin
# See the https://opensource.org/licenses/MIT for license details.

# python 3 compatibility version
from six.moves import xrange
import os
from pygcam.config import getParam, setParam, pathjoin
from pygcam.log import getLogger
from pygcam.utils import mkdirs, getResource
from ..context import getSimDir
from .McsSubcommandABC import McsSubcommandABC, clean_help

_logger = getLogger(__name__)

def genSALibData(trials, method, paramFileObj, args):
    from ..error import PygcamMcsUserError
    from ..sensitivity import DFLT_PROBLEM_FILE, Sobol, FAST, Morris # , MonteCarlo
    from pygcam.utils import ensureExtension, removeTreeSafely, mkdirs

    SupportedDistros = ['Uniform', 'LogUniform', 'Triangle', 'Linked']

    outFile = args.outFile or os.path.join(getSimDir(args.simId), 'data.sa')
    outFile = ensureExtension(outFile, '.sa')

    if os.path.lexists(outFile):
        # Attempt to mv an existing version of the file to the same name with '~'
        backupFile = outFile + '~'
        if os.path.isdir(backupFile):
            removeTreeSafely(backupFile)

        elif os.path.lexists(backupFile):
            raise PygcamMcsUserError("Refusing to delete '%s' since it's not a file package." % backupFile)

        os.rename(outFile, backupFile)

    mkdirs(outFile)

    linked = []

    problemFile = pathjoin(outFile, DFLT_PROBLEM_FILE)
    with open(problemFile, 'w') as f:
        f.write('name,low,high\n')

        for elt in paramFileObj.tree.iterfind('//Parameter'):
            name = elt.get('name')
            distElt = elt.find('Distribution')
            distSpec = distElt[0]   # should have only one child as per schema
            distName = distSpec.tag

            # These 3 distro forms specify min and max values, which we use with SALib
            legal = SupportedDistros + ['Linked']
            if distName not in legal:
                raise PygcamMcsUserError("Found '%s' distribution; must be one of %s for use with SALib." % (distName, legal))

            if distName == 'Linked':        # TBD: ignore these and figure it out when loading the file?
                linked.append((name, distSpec.get('parameter')))
                continue

            # Parse out the various forms: (max, min), (factor), (range), and factor for LogUniform
            attrib = distSpec.attrib
            if 'min' in attrib and 'max' in attrib:
                minValue = float(attrib['min'])
                maxValue = float(attrib['max'])
            elif 'factor' in attrib:
                value = float(attrib['factor'])
                if distName == 'LogUniform':
                    minValue = 1/value
                    maxValue = value
                else:
                    minValue = 1 - value
                    maxValue = 1 + value
            elif 'range' in attrib:
                value = float(attrib['range'])
                minValue = -value
                maxValue =  value

            f.write("%s,%f,%f\n" % (name, minValue, maxValue))

    methods = (Sobol, FAST, Morris) # , MonteCarlo)
    methodMap = {cls.__name__.lower(): cls for cls in methods}

    cls = methodMap[method]
    sa = cls(outFile)

    # saves to input.csv in file package
    sa.sample(trials=trials, calc_second_order=args.calcSecondOrder)
    return sa.inputsDF


def genTrialData(simId, trials, paramFileObj, args):
    """
    Generate the given number of trials for the given simId, using the objects created
    by parsing parameters.xml. Return a DataFrame of values.
    """
    from pandas import DataFrame
    from ..distro import linkedDistro
    from ..LHS import lhs, lhsAmend
    from ..XMLParameterFile import XMLRandomVar, XMLCorrelation
    from ..util import writeTrialDataFile

    rvList = XMLRandomVar.getInstances()

    linked = [obj for obj in rvList if obj.param.dataSrc.isLinked()]

    method = args.method
    if method == 'montecarlo':
        # legacy Monte Carlo method. Supporting numerous distributions and correlations.

        corrMatrix = XMLCorrelation.corrMatrix()

        # TBD: this is currently broken. Only "shared" RVs are supported with the DataFrame
        # TBD: approach since a Parameter can have multiple RVs which appear as separate
        # TBD: data columns. This is ok for the current analysis, but needs to be rewritten
        # TBD: on integration with pygcam. (getName() will fail on XMLVariable instances)

        paramNames = [obj.getParameter().getName() for obj in rvList]
        trialData = lhs(rvList, trials, corrMat=corrMatrix, columns=paramNames, skip=linked)
    else:
        # SALib methods
        trialData = genSALibData(trials, method, paramFileObj, args)

    linkedDistro.storeTrialData(trialData)  # stores trial data in class so its ppf() can access linked values
    lhsAmend(trialData, linked, trials, shuffle=False)

    if method == 'montecarlo':
        writeTrialDataFile(simId, trialData)

    df = DataFrame(data=trialData)
    return df


def saveTrialData(df, simId, start=0):
    """
    Save the trial data in `df` to the SQL database, for the given simId.
    """
    from ..Database import getDatabase
    from ..XMLParameterFile import XMLRandomVar
    from six.moves import xrange

    trials = df.shape[0]

    # Delete all Trial entries for this simId and this range of trialNums
    db = getDatabase()

    paramValues = []

    for trial in xrange(trials):
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

    # Write the tuples (simId, trialNum, paramId, value) to the database
    db.saveParameterValues(simId, paramValues)

    # SALib methods may not create exactly the number of trials requested
    # so we update the database to set the record straight.
    db.updateSimTrials(simId, trials)
    _logger.info('Saved %d trials for simId %d', trials, simId)


def runStaticSetup(runWorkspace, project, groupName):
    """
    Run the --staticOnly setup in the MCS copy of the workspace, for all scenarios.
    This is called from gensim, so we fake the "context" for trial 0, since all
    trials have local-xml symlinked to RunWorkspace's local-xml.
    """
    import pygcam.tool
    from pygcam.utils import mkdirs
    from pygcam.constants import LOCAL_XML_NAME
    from ..util import symlink
    from ..error import GcamToolError

    projectName = project.projectName

    scenarios = project.getKnownScenarios()
    scenariosArg = ','.join(scenarios)

    useGroupDir = project.scenarioGroup.useGroupDir
    groupSubdir = groupName if useGroupDir else ''

    # create symlinks from all the scenarios' local-xml dirs to shared one
    # under {projectName}/Workspace
    sandboxDir = os.path.join(runWorkspace, groupSubdir)
    mkdirs(sandboxDir)

    wsXmlDir = os.path.join(runWorkspace, LOCAL_XML_NAME)
    mkdirs(wsXmlDir)

    for scenario in scenarios:
        dirname = os.path.join(sandboxDir, scenario)
        mkdirs(dirname)
        linkname  = os.path.join(dirname, LOCAL_XML_NAME)
        symlink(wsXmlDir, linkname)

    # N.B. RunWorkspace for gensim is pygcam's RefWorkspace
    toolArgs = ['+P', projectName, '--mcs=gensim', 'run', '-s', 'setup',
                '-S', scenariosArg, '--sandboxDir=' + sandboxDir]

    # if useGroupDir:
    if groupName:
        toolArgs += ['-g', groupName]

    _logger.debug('Running: %s', 'gt ' + ' '.join(toolArgs))
    status = pygcam.tool.main(argv=toolArgs, raiseError=True)

    if status != 0:
        msg = '"gt setup" exited with status %d' % status
        raise GcamToolError(msg)

    return status

def genSimulation(simId, trials, paramPath, args):
    '''
    Generate a simulation based on the given parameters.
    '''
    from ..context import Context
    from ..Database import getDatabase
    from ..XMLParameterFile import XMLParameterFile
    from ..util import getSimParameterFile, getSimResultFile, symlink, filecopy
    from pygcam.constants import LOCAL_XML_NAME
    from pygcam.project import Project
    from pygcam.xmlSetup import ScenarioSetup

    runInputDir = getParam('MCS.RunInputDir')
    runWorkspace = getParam('MCS.RunWorkspace')

    # Add symlink to workspace's input dir so we can find XML files using rel paths in config files
    simDir = getSimDir(simId, create=True)
    simInputDir = os.path.join(simDir, 'input')
    symlink(runInputDir, simInputDir)

    # Ditto for workspace's local-xml
    workspaceLocalXml = os.path.join(runWorkspace, LOCAL_XML_NAME)
    simLocalXmlDir = os.path.join(simDir, LOCAL_XML_NAME)
    symlink(workspaceLocalXml, simLocalXmlDir)

    projectName = getParam('GCAM.ProjectName')
    project = Project.readProjectFile(projectName, groupName=args.groupName)

    args.groupName = groupName = args.groupName or project.scenarioSetup.defaultGroup

    # Run static setup for all scenarios in the given group
    runStaticSetup(runWorkspace, project, groupName)

    # TBD: Use pygcam scenario def and copy pygcam files, too
    scenarioFile = getParam('GCAM.ScenarioSetupFile')
    scenarioSetup = ScenarioSetup.parse(scenarioFile)
    scenarioNames = scenarioSetup.scenariosInGroup(groupName)
    baseline      = scenarioSetup.baselineForGroup(groupName)

    # Copy the user's results.xml file to {simDir}/app-xml
    userResultFile = getParam('MCS.ResultsFile')
    simResultFile = getSimResultFile(simId)
    mkdirs(os.path.dirname(simResultFile))
    filecopy(userResultFile, simResultFile)

    paramFileObj = XMLParameterFile(paramPath)
    context = Context(projectName=args.projectName, simId=simId, groupName=groupName)
    paramFileObj.loadInputFiles(context, scenarioNames, writeConfigFiles=True)

    # Define the experiments (scenarios) in the database
    db = getDatabase()
    db.addExperiments(scenarioNames, baseline, scenarioFile)

    if not trials:
        _logger.warn("Simulation meta-data has been copied.")
        if not args.dataFile:
            return

    paramFileObj.generateRandomVars()

    if args.dataFile:
        from pandas import read_table
        df = read_table(args.dataFile, sep=',', index_col='trialNum')
        _logger.info("Loaded data for %d trials from %s", df.shape[0], args.dataFile)
    else:
        _logger.info("Generating %d trials to %r", trials, simDir)
        df = genTrialData(simId, trials, paramFileObj, args)

    # Save generated values to the database for post-processing
    saveTrialData(df, simId)

    # Also save the param file as parameters.xml, for reference only
    simParamFile = getSimParameterFile(simId)
    filecopy(paramPath, simParamFile)

def _newsim(runWorkspace, trials):
    '''
    Setup the app and run directories for a given user app.
    '''
    from pygcam.scenarioSetup import copyWorkspace
    from ..Database import getDatabase
    from ..error import PygcamMcsUserError
    from ..XMLResultFile import XMLResultFile

    if not runWorkspace:
        raise PygcamMcsUserError("MCS.RunWorkspace was not set in the configuration file")

    srcDir = getParam('GCAM.RefWorkspace')
    dstDir = runWorkspace

    copyWorkspace(dstDir, refWorkspace=srcDir, forceCreate=True, mcsMode=True)

    if trials:
        db = getDatabase()   # ensures database initialization
        XMLResultFile.addOutputs()

        # Load SQL script to create convenient views
        text = getResource('mcs/etc/views.sql')
        db.executeScript(text=text)

def _simplifyDistro(dataSrc):
    '''
    Convert triangle distros declared with logfactor, factor, or range to min/mode/max
    format for documentation purposes.
    '''
    if dataSrc.distroName == 'triangle':
        argDict = dataSrc.argDict
        keys = list(argDict.keys())
        if len(keys) == 1:
            key = keys[0]
            value = argDict[key]
            del argDict[key]

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


def _exportVars(paramFile, outputFile):
    import re
    from itertools import chain
    from pygcam.mcs.XMLParameterFile import XMLDistribution, XMLParameterFile

    paramFileObj = XMLParameterFile(paramFile)
    params = list(chain.from_iterable(map(lambda x: x.parameters.values(), paramFileObj.inputFiles.values())))

    def getDistStr(dataSrc):
        _simplifyDistro(dataSrc)
        argStr = ', '.join(['{}={}'.format(name, value) for name, value in dataSrc.argDict.items()])
        distro = '{}({})'.format(dataSrc.distroName.capitalize(), argStr)
        return distro

    distDict = {p.name : (getDistStr(p.dataSrc), p.dataSrc.modDict, p.desc) for p in params if isinstance(p.dataSrc, XMLDistribution)}

    keys = sorted(distDict.keys(), key=str.casefold) # case insensitive sort

    _logger.info("Writing %s", outputFile)
    with open(outputFile, 'w') as f:
        f.write("Name\tDistribution\tApplication\tDescription\n")

        for name in keys:
            dist, modDict, desc = distDict[name]
            desc = re.sub('\s+', ' ', desc)
            f.write("{}\t{}\t{}\t{}\n".format(name, dist, modDict['apply'], desc))

def driver(args, tool):
    '''
    Generate a simulation. Do generic setup, then call genSimulation().
    '''
    from pygcam.utils import removeTreeSafely
    from ..Database import getDatabase
    from ..error import PygcamMcsUserError
    from ..util import saveDict

    paramFile = args.paramFile or getParam('MCS.ParametersFile')

    if args.exportVars:
        _exportVars(paramFile, args.exportVars)
        return

    simId  = args.simId
    desc   = args.desc
    trials = args.trials

    if trials < 0:
        raise PygcamMcsUserError("Trials argument is required: must be an integer >= 0")

    projectName = args.projectName
    runRoot = args.runRoot
    if runRoot:
        # TBD: write this to config file under [project] section
        setParam('MCS.Root', runRoot, section=projectName)
        _logger.info('Please add "MCS.Root = %s" to your .pygcam.cfg file in the [%s] section.',
                     runRoot, projectName)

    runDir = getParam('MCS.RunDir', section=projectName)

    if args.delete:
        removeTreeSafely(runDir, ignore_errors=False)

    runWorkspace = getParam('MCS.RunWorkspace')

    if not os.path.exists(runWorkspace):
        _newsim(runWorkspace, trials)

    # Called with trials == 0 when setting up a local run directory on /scratch
    if trials:
        # The simId can be provided on command line, in which case we need
        # to delete existing parameter entries for this app and simId.
        db = getDatabase()
        simId = db.createSim(trials, desc, simId=simId)

    genSimulation(simId, trials, paramFile, args=args)

    if trials:
        # Save a copy of the arguments used to create this simulation
        simDir = getSimDir(simId)
        argSaveFile = '%s/gcamGenSimArgs.txt' % simDir
        saveDict(vars(args), argSaveFile)


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

        parser.add_argument('-e', '--exportVars', default='',
                            help=clean_help('Export variable and distribution info in a tab-delimited file with the given name and exit.'))

        parser.add_argument('-g', '--groupName', default='',
                            help=clean_help('''The name of a scenario group to process.'''))

        parser.add_argument('-m', '--method', choices=['montecarlo', 'sobol', 'fast', 'morris'],
                            default='montecarlo',
                            help=clean_help('''Use the specified method to generate trial data. Default is "montecarlo".'''))

        parser.add_argument('-o', '--outFile',
                            help=clean_help('''For methods other than "montecarlo". The path to a "package 
                            directory" into which SALib-related data are stored.
                            If the filename does not end in '.sa', this extension is added. The file
                            'problem.csv' within the package directory will contain the parameter specs in
                            SALib format. The file inputs.csv is also generated in the file package using
                            the chosen method's sampling method. If an outFile is not specified, a package
                            of the name 'data.sa' is created in the simulation run-time directory.'''))

        parser.add_argument('-p', '--paramFile', default=None,
                            help=clean_help('''Specify an XML file containing parameter definitions.
                            Defaults to the value of config parameter MCS.ParametersFile
                            (currently %s)''' % getParam('MCS.ParametersFile')))

        runRoot = getParam('MCS.Root')
        parser.add_argument('-r', '--runRoot', default=None,
                            help=clean_help('''Root of the run-time directory for running user programs. Defaults to
                            value of config parameter MCS.Root (currently %s)''' % runRoot))

        parser.add_argument('-S', '--calcSecondOrder', action='store_true',
                            help=clean_help('''For Sobol method only -- calculate second-order sensitivities.'''))

        parser.add_argument('-s', '--simId', type=int, default=1,
                            help=clean_help('The id of the simulation. Default is 1.'))

        parser.add_argument('-t', '--trials', type=int, default=-1,
                            help=clean_help('''The number of trials to create for this simulation (REQUIRED). If a
                            value of 0 is given, scenario setup is performed, scenario names are added to 
                            the database, and meta-data is copied, but new trial data is not generated.'''))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
