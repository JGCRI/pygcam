from abc import ABCMeta, abstractmethod
import json
import math
import os
import numpy as np
import pandas as pd

try:
    from SALib.analyze.delta import analyze as delta_analyzer
    from SALib.analyze.dgsm import analyze as dgsm_analyzer

    from SALib.analyze import fast, morris, sobol
    from SALib.sample import saltelli, fast_sampler
    from SALib.sample import morris as morris_sampler
    from SALib.sample.latin import sample as latin_sampler
    from SALib.sample.finite_diff import sample as finite_diff_sampler

    from SALib.test_functions import Ishigami
except:
    print("WARNING: Failed to import from SALib; dummy function names defined. SALib features are unusable.")
    delta_analyzer = dgsm_analyzer = None
    fast = morris = sobol = Ishigami = None
    morris_sampler = latin_sampler = finite_diff_sampler = None

# TBD: Save data compressed (opt), with zlib or gzip pkgs.

DFLT_PROBLEM_FILE = 'problem.csv'
DFLT_INPUTS_FILE  = 'inputs.csv'
DFLT_RESULTS_FILE = 'results.csv'
DFLT_GROUPS_FILE  = 'groups.csv'
DFLT_LINKED_FILE  = 'linkedCols.json'

# From https://waterprogramming.wordpress.com/2013/08/05/running-sobol-sensitivity-analysis-using-salib/
# If the confidence intervals of your dominant indices are larger than
# roughly 10% of the value itself, you may want to consider increasing
# your sample size as computation permits. For total-order indices to be
# important, they will usually need to be above 0.05 at the very least
# (the most dominant parameters will have values upward of 0.8).
#
# The cross-sampling scheme creates a total of 2N(p+1) total parameter
# sets to be run in your model, where N is the initial number of Sobol
# sequence values generated, and p is the number of parameters.

# Approach: use Spearman method to identify the top 5 or 6 parameters, then
# use Sobol analysis to zero in on them?? Maybe the Sobol approach is simply
# intractable with a model like GCAM? For 39 parameters, 2400 runs doesn't
# come close to adequate. Say we use a Sobol sequence of len 500, this would
# require 39,000 trials. (Of course the CB manual suggests 10,000 runs...)


class SAException(Exception):
    pass

class SensitivityAnalysis(object):
    """
    Abstract superclass for Sensitivity Analysis methods from SALib. Stores sets
    of method name and args, parameter descriptions, samples, and model results
    in a directory "package" with an ".sa" extension. Ensures that analysis
    methods are called with the same arguments used to produce the samples.
    """
    __metaclass__ = ABCMeta

    def __init__(self, pkgPath, problemFile=None, inputsFile=None, resultsFile=None):
        self.pkgPath   = pkgPath
        self.problem   = None
        self.inputs    = None
        self.inputsDF  = None
        self.results   = None
        self.resultsDF = None
        self.s2df      = None
        self.kwargs    = {}

        self.argsFile    = os.path.join(pkgPath, 'args.json')
        self.problemFile = os.path.join(pkgPath, problemFile or DFLT_PROBLEM_FILE)
        self.inputsFile  = os.path.join(pkgPath, inputsFile  or DFLT_INPUTS_FILE)
        self.resultsFile = os.path.join(pkgPath, resultsFile or DFLT_RESULTS_FILE)

        if os.path.lexists(self.problemFile):
            self.loadProblem()

    def loadProblem(self, filename=None, sep=','):
        self.problemFile = filename or self.problemFile
        data = pd.read_table(self.problemFile, sep=sep)

        self.problem = {'num_vars' : len(data),
                        'names'  : list(data.name),
                        'bounds' : data.as_matrix(columns=['low','high']),
                        #'groups' : None # required for Morris
                        }
        return self.problem

    def loadResults(self, resultName, resultsFile=None, sep=','):
        """
        Load model results from a CSV file.

        :param resultName: (str) the name of the model output
        :param resultsFile: (str) the path of the results file
        :param sep: (str) column separator
        :return: (pandas.DataFrame) contents of the results file
        """
        self.resultsFile = resultsFile or self.resultsFile
        self.resultsDF = pd.read_table(self.resultsFile, sep=sep)
        self.results = self.resultsDF[resultName].as_matrix()
        self.resultName = resultName
        return self.results

    def saveResults(self, results):
        self.results = results
        self.resultsDF = pd.DataFrame(data=results)
        self.resultsDF.to_csv(self.resultsFile, sep=',')

    def saveInputs(self, inputs=None, filename=None):
        inputs = inputs or self.inputs
        filename = filename or self.inputsFile
        varNames = self.problem['names']
        df = self.inputsDF = pd.DataFrame(data=inputs, columns=varNames)
        df['trialNum'] = df.index
        df.to_csv(filename, index=False, sep=',')

    def loadInputs(self, filename=None, sep=','):
        filename = filename or self.inputsFile
        if not filename:
            raise SAException("Can't loadInputs: filename is None")

        self.inputsDF = pd.read_table(filename, sep=sep, index_col='trialNum')
        self.inputs  = self.inputsDF.as_matrix()

    def saveArgs(self):
        with open(self.argsFile, 'w') as f:
            json.dump(self.kwargs, f)
            f.write('\n')

    def loadArgs(self):
        with open(self.argsFile) as f:
            self.kwargs = json.load(f)
        return self.kwargs

    def storeKwargs(*args, **kwargs):
        self = args[0]
        self.kwargs.update(kwargs)

    def getKwarg(self, key, kwargs):
        return kwargs.get(key, self.kwargs[key])

    def sample(*args, **kwargs):
        args = list(args)
        self = args.pop(0)
        self.trials = kwargs.get('trials', 1000)
        self.calcSecondOrder = kwargs.get('calc_second_order', True)
        self.N = kwargs.get('N', self.predictN(self.trials, self.calcSecondOrder))

        self.inputs = self._sample(*args, **kwargs)
        self.saveInputs()
        self.saveArgs()
        return self.inputs

    def analyze(*args, **kwargs):
        args = list(args)
        self = args.pop(0)
        self.loadInputs()
        self.loadArgs()

        # Handle nan values by replacing them with the mean of all other results
        Y = self.results
        nans = np.isnan(Y)
        if nans.any():
            Y[nans] = Y[~nans].mean()

        if kwargs.get('print_to_console', False):
            print("\n%s:" % self.__class__.__name__)

        analysisDict = self._analyze(*args, **kwargs)

        if 'S2' in analysisDict:
            S2 = analysisDict['S2']
            del analysisDict['S2']
            S2_conf = analysisDict['S2_conf']
            del analysisDict['S2_conf']

            names = self.problem['names']
            D = len(names)
            s2Dict = {'name1' : [], 'name2' : [], 'S2': [], 'S2_conf' : []}

            for j in range(D):
                name1 = names[j]
                for k in range(j + 1, D):
                    s2Dict['name1'].append(name1)
                    s2Dict['name2'].append(names[k])
                    s2Dict['S2'].append(S2[j, k])
                    s2Dict['S2_conf'].append(S2_conf[j, k])

            self.s2df = df = pd.DataFrame(data=s2Dict, columns=['name1', 'name2', 'S2', 'S2_conf'])
            #df.set_index(['name1', 'name2'], inplace=True)
            df.sort_values(by='S2', ascending=False, inplace=True)

        df = self.analysis = pd.DataFrame(data=analysisDict)
        df['names'] = self.problem['names']
        df['abs_S1'] = abs(df['S1'])
        df.set_index('names', inplace=True)
        df.sort_values(by='abs_S1', ascending=False, inplace=True)
        return df

    def predictN(self, trials, calcSecondOrder=False):
        '''
        Computes the value of N required to produce the given number
        of samples, per SA method.

        :param trials: (int) the number of total samples desired
        :param calcSecondOrder: (bool) whether to calculate second-order
           sensitivity indices (for Sobol method only).
        :return: (int) the value of N to use to produce `trials`
        '''
        nVars = self.problem['num_vars']
        return self._predictN(trials, nVars, calcSecondOrder)

    @abstractmethod
    def _predictN(self, trials, nVars, calcSecondOrder):
        pass

    @abstractmethod
    def _sample(self, **kwargs):
        """
        _sample() methods must set self.kwargs to hold all values that
        must be the same in _analyze(). These are saved to disk.
        """
        pass

    @abstractmethod
    def _analyze(self, **kwargs):
        pass

# TBD: Implement this
class MonteCarlo(SensitivityAnalysis):
    def __init__(self, pkgPath, problemFile=None, inputsFile=None, resultsFile=None):
        super(MonteCarlo, self).__init__(pkgPath, problemFile=problemFile,
                                         inputsFile=inputsFile, resultsFile=resultsFile)

    def _sample(*args, **kwargs):
        self = args[0]
        self.storeKwargs(**kwargs)
        return None # sample(self.problem, self.N, calc_second_order=self.calcSecondOrder)

    def _analyze(*args, **kwargs):
        '''
        Returns a dictionary with key 'S1', which is a list of size D (the
        number of parameters) containing the indices in the same order as in
        the parameter file. The values are the normalized rank correlations
        of each parameter to the designated output variable.
        :param args:
        :param kwargs:
        :return:
        '''
        self = args[0]
        print_to_console = kwargs.get('print_to_console', False)

        return None # analyze(self.problem, self.results, print_to_console=print_to_console)

    def _predictN(self, trials, nVars, calcSecondOrder):
        return trials

class Sobol(SensitivityAnalysis):
    """
    Provides an interface to SALib's Sobol Sensitivity sampling and analysis methods.
    """
    def __init__(self, pkgPath, problemFile=None, inputsFile=None, resultsFile=None):
        super(Sobol, self).__init__(pkgPath, problemFile=problemFile,
                                    inputsFile=inputsFile, resultsFile=resultsFile)

    def _sample(*args, **kwargs):
        self = args[0]
        self.storeKwargs(calc_second_order=self.calcSecondOrder)
        return saltelli.sample(self.problem, self.N, calc_second_order=self.calcSecondOrder)

    def _analyze(*args, **kwargs):
        self = args[0]

        calc_second_order = self.getKwarg('calc_second_order', kwargs)

        num_resamples     = kwargs.get('num_resamples', 100)
        conf_level        = kwargs.get('conf_level', 0.95)
        print_to_console  = kwargs.get('print_to_console', False)
        parallel          = kwargs.get('parallel', False)
        n_processors      = kwargs.get('n_processors', None)

        return sobol.analyze(self.problem, self.results, calc_second_order=calc_second_order,
                             num_resamples=num_resamples, conf_level=conf_level,
                             print_to_console=print_to_console, parallel=parallel,
                             n_processors=n_processors)

    def _predictN(self, trials, nVars, calcSecondOrder):
        multiple = 2 if calcSecondOrder else 1
        return int(math.ceil(trials / (multiple * nVars + 2)))


class FAST(SensitivityAnalysis):
    """
    Provides an interface to SALib's Fourier Amplitude Sensitivity Test (FAST)
    sampling and analysis methods.
    """
    def __init__(self, pkgPath, problemFile=None, inputsFile=None, resultsFile=None):
        super(FAST, self).__init__(pkgPath, problemFile=problemFile,
                                   inputsFile=inputsFile, resultsFile=resultsFile)

    def _sample(*args, **kwargs):
        self = args[0]

        N = self.N
        M = kwargs.get('M', 4)
        self.storeKwargs(N=N, M=M)

        return fast_sampler.sample(self.problem, N=N, M=M)

    def _analyze(*args, **kwargs):
        self = args[0]

        M = self.getKwarg('M', kwargs)
        print_to_console = kwargs.get('print_to_console', False)

        return fast.analyze(self.problem, self.results, M=M,
                            print_to_console=print_to_console)

    def _predictN(self, trials, nVars, calcSecondOrder):
        return int(math.ceil(trials / nVars))


class Morris(SensitivityAnalysis):
    """
    Provides an interface to SALib's Method of Morris sampling and analysis methods.
    """
    def __init__(self, pkgPath, problemFile=None, inputsFile=None, resultsFile=None,
                 groupsFile=None):
        super(Morris, self).__init__(pkgPath, problemFile=problemFile,
                                     inputsFile=inputsFile, resultsFile=resultsFile)

        # TBD: test 'groups' functionality
        self.groupsFile = self.groupsDF = None
        groupsFile = os.path.join(self.pkgPath, groupsFile or DFLT_GROUPS_FILE)

        if groupsFile and os.path.lexists(groupsFile):
            self.groupsFile = groupsFile
            self.groupsDF = pd.read_table(self.groupsFile)

        # set the 'groups' to None if no groups since sample method requires this
        if self.problem:
            self.problem['groups'] = self.groupsDF.as_matrix() if self.groupsDF else None

    # Maybe write kwargs to json file and reload this in analyze() to ensure same args used
    def _sample(*args, **kwargs):
        self = args[0]
        N = self.N
        num_levels           = kwargs.get('num_levels', 4)
        grid_jump            = kwargs.get('grid_jump', 2)
        optimal_trajectories = kwargs.get('optimal_trajectories', None)
        local_optimization   = kwargs.get('local_optimization', False)

        X = morris_sampler.sample(self.problem, N, num_levels, grid_jump,
                                  optimal_trajectories=optimal_trajectories,
                                  local_optimization=local_optimization)

        self.storeKwargs(num_levels=num_levels, grid_jump=grid_jump)
        return X

    def _analyze(*args, **kwargs):
        self = args[0]

        num_levels       = self.getKwarg('num_levels', kwargs)
        grid_jump        = self.getKwarg('grid_jump', kwargs)
        num_resamples    = kwargs.get('num_resamples', 1000)
        conf_level       = kwargs.get('conf_level', 0.95)
        print_to_console = kwargs.get('print_to_console', False)

        return morris.analyze(self.problem, self.inputs, self.results, num_resamples=num_resamples,
                              conf_level=conf_level, print_to_console=print_to_console,
                              grid_jump=grid_jump, num_levels=num_levels)

    def _predictN(self, trials, nVars, calcSecondOrder):
        return int(math.ceil(trials / (nVars + 1)))


class LatinSampler(SensitivityAnalysis):
    def __init__(self, pkgPath, analyzeFn=None, problemFile=None, inputsFile=None, resultsFile=None):
        super(LatinSampler, self).__init__(pkgPath, problemFile=problemFile,
                                     inputsFile=inputsFile, resultsFile=resultsFile)
        self.analyzeFn = analyzeFn
        self.defaultResamples = 10
        self.defaultConfLevel = 0.95
        self.defaultPrint = False

    def _sample(*args, **kwargs):
        self = args[0]
        N = self.N
        self.storeKwargs(N=N)
        X = latin_sampler(self.problem, N)
        return X

    def _analyze(*args, **kwargs):
        self = args[0]

        num_resamples    = kwargs.get('num_resamples', self.defaultResamples)
        conf_level       = kwargs.get('conf_level', self.defaultConfLevel)
        print_to_console = kwargs.get('print_to_console', self.defaultPrint)

        return self.analyzeFn(self.problem, self.inputs, self.results,
                              num_resamples=num_resamples,
                              conf_level=conf_level,
                              print_to_console=print_to_console)

class Delta(LatinSampler):
    """
    Provides an interface to SALib's Delta moment-independent measure
    sampling and analysis methods.
    """
    def __init__(self, pkgPath, problemFile=None, inputsFile=None, resultsFile=None):
        super(Delta, self).__init__(pkgPath,
                                    analyzeFn=delta_analyzer, problemFile=problemFile,
                                    inputsFile=inputsFile, resultsFile=resultsFile)

    def _predictN(self, trials, nVars, calcSecondOrder):
        return trials


class DGSM(LatinSampler):
    """
    Provides an interface to SALib's Derivative-based Global Sensitivity
    Measure (DGSM) sampling and analysis methods.
    """
    def __init__(self, pkgPath, problemFile=None, inputsFile=None, resultsFile=None):
        super(DGSM, self).__init__(pkgPath,
                                   analyzeFn=dgsm_analyzer, problemFile=problemFile,
                                   inputsFile=inputsFile, resultsFile=resultsFile)
        self.defaultResamples = 1000

    def _predictN(self, trials, nVars, calcSecondOrder):
        return int(math.ceil(trials / (nVars + 1)))

    def _sample(*args, **kwargs):
        self = args[0]
        N = self.N
        delta = kwargs.get('delta', 0.01)
        self.storeKwargs(N=N)
        X = finite_diff_sampler(self.problem, N, delta=delta)
        return X

if __name__ == "__main__":
    mcsTest = True

    if mcsTest:
        sa = Sobol('/Users/rjp/mcs/paper1/sims/s001/data.sa')
        sa.loadResults('corn-ci-all')
        df = sa.analyze(print_to_console=True)
        pd.set_option('display.width', 300)
        print(df)
        print(sa.s2df)

    else:
        for cls in (Sobol, FAST, Morris, Delta, DGSM):
            sa = cls('../tests/test.sa')

            kwargs = {'num_samples': 1000}

            if cls == Sobol:
                pass
            elif cls == FAST:
                kwargs['M'] = 4
            elif cls == Morris:
                kwargs['num_levels'] = 4
                kwargs['grid_jump'] = 2
                kwargs['optimal_trajectories'] = None
                kwargs['local_optimization'] = False
            elif cls == DGSM:
                pass
            elif cls == Delta:
                pass
            else:
                raise SAException("Unknown SA class")

            # Generate samples
            param_values = sa.sample(**kwargs)

            # Run model (example)
            results = Ishigami.evaluate(param_values)
            sa.saveResults(results)

            # Perform analysis
            # Si is a Python dict with the keys "S1", "S2", "ST", "S1_conf",
            # "S2_conf", and "ST_conf". The _conf keys store the corresponding
            # confidence intervals, typically with a confidence level of 95%.
            Si = sa.analyze(print_to_console=True)

            # Print the first-order sensitivity indices
            # print Si['S1']
