#
# Author: rich@plevin.com
# 2023/2024

_instructions = """Before generating XML, make sure data system has been set up by running:

  gt moirai --create-baseline      # run drake to create the baseline against which changes are detected
  gt moirai --save-moirai-summary  # run the data system for each of 6 carbon statistics and collect the data into one CSV
  gt moirai --save-beta-args	   # uses min, q1, q3, and max values to generate params defining Beta distros for each GLU

You can then generate xml using the files created above:

  gt moirai --gen-xml -t "PATH"    # generate the XML files using the saved draws from the Beta distributions
"""

import os
import pandas as pd
from pathlib import Path
from scipy import stats, optimize
import shutil

from pygcam.error import PygcamException
from pygcam.subcommand import SubcommandABC
from pygcam.log import getLogger
from pygcam.config import getParam, mkdirs
from pygcam.utils import Timer
from pygcam.mcs.gcamdata import GcamDataSystem, load_R_code, str_replace_from_dict

_logger = getLogger('moirai_plugin')

HOME = os.getenv('HOME')

# TBD: make this a config variable. Default should probably be "renv-GCAM"

# default dir where the lockfile for the required renv is found
DEFAULT_RENV_DIR = f'{HOME}/renv-GCAM-T'

# added to the base names of XML files that are updated by driver_drake()
DEFAULT_MODIFIER = '__drake'

USER_MOD_FUNC_NAME = 'usermod_stochastic_C'

STATIC_LAND_TYPES = ('UrbanLand', 'RockIceDesert', 'Tundra')

# For GCAMv7, the module name to stop after (in the string below) changed to
# 'module_aglu_L120.LC_GIS_R_LTgis_Yh_GLU', whereas previously it was
# 'module_aglu_LB120.LC_GIS_R_LTgis_Yh_GLU' (now "L" rather than "LB").
# The value must be set in the config parameter 'OTAQ.MoiraiModuleToStopAfter'.
def r_code_save_carbon_data():
    module_name = getParam('Moirai.ModuleToStopAfter')
    return f"""
save_carbon_data <- function(data_dir, stat_name) {{
  # stat_name can be one of {{'min', 'max', 'median', 'q1', 'q3', 'avg'}}

  carbon_state <- ifelse(stat_name == 'avg', 'weighted_average', paste0(stat_name, '_value'))

  ns = getNamespace('gcamdata')
  ns[['aglu.CARBON_STATE']] = carbon_state

  driver(stop_after="{module_name}", write_outputs=TRUE)

  # Rename the file written by save_chunkdata() to append the chosen statistic
  # to the name and copy to another directory for saving since they get deleted.
  basename <- "L120.LC_soil_veg_carbon_GLU"
  from <- paste0(OUTPUTS_DIR, basename, '.csv')
  to <- paste0(data_dir, '/', basename, '-', stat_name, '.csv')
  file.copy(from, to, overwrite=TRUE)
}}
"""

def save_all_carbon_stats(data_dir, renv_dir):
    """
    Run the GCAM data system 6 times to generate aggregated C density data using each
    of the 6 statistics available at the country level. The six files will then be
    combined into a single CSV with all these statistics to use as an input to an MCS.
    """
    from rpy2 import robjects
    from rpy2.robjects.packages import importr
    from pygcam.mcs.gcamdata import load_R_code

    mkdirs(data_dir)

    renv = importr("renv")
    _logger.info(f"Activating R environment '{renv}'")
    renv.activate(renv_dir)

    gcamdata_dir = getParam('GCAM.RefGcamData')
    devtools = importr('devtools')
    devtools.load_all(gcamdata_dir)

    load_R_code(r_code_save_carbon_data())
    save_carbon_data = robjects.r["save_carbon_data"]

    for stat_name in ('q1', 'q3', 'min', 'max', 'median', 'avg'):
        _logger.debug(f"Saving soil data for '{stat_name}' to '{data_dir}'")
        save_carbon_data(data_dir, stat_name)

#
# This is not the final R code; it requires substitution of '{{SAVED-DRAWS-CSV}}'
# with the actual pathname of the file, passed as arguments to run_drake_with_mods().
#
r_code_template = """
{{USER-MOD-FUNC-NAME}} <- function(command, ...) {
  if(command == driver.DECLARE_MODIFY) {
    return(c(FILE = "L120.LC_soil_veg_carbon_GLU"))

  } else if(command == driver.DECLARE_INPUTS) {
    # In addition to the objects users want to modify we can also ask for any other
    # inputs we need to do our operations but won't be modified
    return(NULL)

  } else if(command == driver.MAKE) {
    all_data <- list(...)[[1]]
    L120.LC_soil_veg_carbon_GLU <- get_data(all_data, "L120.LC_soil_veg_carbon_GLU")

    # Read C density values drawn from generated Beta distributions and overwrite q3 values
    draws = readr::read_csv("{{SAVED-DRAWS-CSV}}")

    # Overwrite carbon values based on draws from distributions
    L120.LC_soil_veg_carbon_GLU['soil_c'] = draws['soil_c']
    L120.LC_soil_veg_carbon_GLU['veg_c']  = draws['veg_c']

    # NOTE: we have to match the original object name we asked for in driver.DECLARE_MODIFY,
    # which means including the file path for input files
    # i.e. "energy/A322.subsector_shrwt" not "A322.subsector_shrwt"
    # Other objects can be listed out just like for `return_data`
    return_modified("L120.LC_soil_veg_carbon_GLU" = L120.LC_soil_veg_carbon_GLU)

  } else {
    stop("Unknown command")
  }
}
"""

##############################################################################################
# From https://www.codeproject.com/KB/recipes/ParameterPercentile/parameter_percentile.zip
def beta_parameters(x1, p1, x2, p2):
    """
    Find parameters for a beta random variable X so that P(X < x1) = p1 and P(X < x2) = p2.
    """
    def objective(v):
        (a, b) = v
        temp  = pow(stats.beta.cdf(x1, a, b) - p1, 2) # expression ^ 2
        temp += pow(stats.beta.cdf(x2, a, b) - p2, 2)
        return temp

    # arbitrary initial guess of (3, 3) for parameters
    xopt = optimize.fmin(objective, (3, 3), disp=False)  # don't display noisy output
    return (xopt[0], xopt[1])
##############################################################################################

def run_drake_with_mods(modifier=DEFAULT_MODIFIER):
    timer = Timer('moirai_plugin::run_drake_with_mods')

    from rpy2 import robjects
    from rpy2.robjects.packages import importr

    func_name = 'usermod_stochastic_C'

    # Ensure that drakes knows to run usermod_stochastic_C
    drake = importr('drake')

    drake.clean(list=func_name)

    driver_drake = robjects.r["driver_drake"]
    driver_drake(user_modifications=func_name, xml_suffix=modifier)

    _logger.info(timer.stop())

def get_stat_name(filename):
    import re
    m = re.match('.*-(.*)\.csv', filename)
    return m[1]

def remove_stem_modifier(path, modifier=DEFAULT_MODIFIER):
    chars = len(modifier)
    no_suffix = Path(path.parent, path.stem[:-chars] + path.suffix)
    return no_suffix.name

def move_modified_xml_files(src_dir, dst_dir, modifier=DEFAULT_MODIFIER):
    src_dir = Path(src_dir)
    modified = src_dir.glob(f'*{modifier}.xml')
    if not modified:
        _logger.warn(f"No modified XML files found in '{src_dir}' (modifier='{modifier}')")
        return

    dst_paths = []
    for src_path in modified:
        dst_path = Path(dst_dir, remove_stem_modifier(src_path, modifier=modifier))
        shutil.move(src_path, dst_path) # renames if same filesystem, else copies & deletes
        dst_paths.append(dst_path)

    return dst_paths

def save_moirai_summary(pathname, renv_dir):
    """
    Create a CSV file containing the 6 aggregate versions of C density
    created by running the GCAM data system 6 times, once using each
    statistical choice as the value of aglu.CARBON_STATE in constants.R.
    """
    from glob import glob

    # Run the data system for each of the statistics, writing CSVs to the tmp directory
    tmp = os.environ.get('TMPDIR', '/tmp')
    tmp_dir = Path(tmp, 'moirai-data').as_posix()

    _logger.debug("Running data system to generate CSV for each statistic")
    save_all_carbon_stats(tmp_dir, renv_dir)

    def read_csv(filename):
        _logger.debug(f"Reading '{filename}'")
        df = pd.read_csv(filename, index_col=False, skiprows=1)
        return df

    # read the data from generated CSV files
    filenames = glob(tmp_dir + '/*.csv')
    df_dict = {get_stat_name(filename) : read_csv(filename) for filename in filenames}

    for stat_name, df in df_dict.items():
        df.drop('mature age', axis='columns', inplace=True)

    for stat_name, df in df_dict.items():
        df.rename({'soil_c': 'soil_c_' + stat_name,
                   'veg_c' : 'veg_c_'  + stat_name},
                                 inplace=True, axis='columns')
        df.set_index(['GCAM_region_ID', 'Land_Type', 'GLU'], inplace=True)

    wide_df = pd.concat(df_dict.values(), axis="columns").reset_index()

    _logger.debug(f"Writing '{pathname}'")
    wide_df.to_csv(pathname, index=False)

def scaled_beta_parameters(x1, p1, x2, p2, min, max):
    """
    Scale Beta distribution parameters by subtracting the min value and dividing by the
    max value to achieve values in the required range, [0, 1].
    :param x1: value at percentile p1
    :param p1: first percentile
    :param x2: value at percentile p2
    :param p2: second percentile
    :param min: minimum value (used for scaling)
    :param max: maximum value (used for scaling)
    :return: the two Beta distribution shape parameters, alpha and beta.
    """
    delta = max - min

    if delta == 0:
        return -1.0, -1.0   # sentinel value indicating not a beta distribution

    def _scale(x):
        return (x - min) / delta

    alpha, beta = beta_parameters(_scale(x1), p1, _scale(x2), p2)
    return alpha, beta

_anomalies = []
_bad_minimum = []

def save_anomaly(row, soil_or_veg, mn, q1, q2, q3, mx):
    s = pd.Series(data=[row.GCAM_region_ID, row.Land_Type, row.GLU, soil_or_veg, mn, q1, q2, q3, mx],
                  index=['region_ID', 'Land_Type', 'GLU', 'pool', 'min', 'q1', 'q2', 'q3', 'max'],
                  name='Anomaly')
    return s

def get_beta_params_from_row(row, soil_or_veg):
    """
    Get the Beta distribution parameters associated with a row of composite moirai data,
    based on the Q1 and Q3 values, and scaling the distribution based on the min and max values.

    :param row: (pd.Series) one row of composite moirai data
    :param soil_or_veg: one of "soil" or "veg" -- which carbon pool we're estimating parameters for
    :return: (tuple of 2 floats) the Beta distribution shape parameters, alpha and beta
    """
    c_min = soil_or_veg + '_c_min'
    c_q1  = soil_or_veg + '_c_q1'
    c_med = soil_or_veg + '_c_median'
    c_q3  = soil_or_veg + '_c_q3'
    c_max = soil_or_veg + '_c_max'

    mn = row[c_min]
    q1 = row[c_q1]
    q2 = row[c_med]
    q3 = row[c_q3]
    mx = row[c_max]

    not_beta = (-1.0, -1.0)

    if row['Land_Type'] in STATIC_LAND_TYPES or mx == 0.0:
        return not_beta

    if q1 == q3:
        return not_beta

    if mn > q1:
        s = save_anomaly(row, soil_or_veg, mn, q1, q2, q3, mx)
        _bad_minimum.append(s)
        mn = 0.2 * q1   # replace bad value with a feasible one

    if not (mn <= q1 <= q2 <= q3 <= mx):
        # moirai data do not represent logical statistics, so we'll just use default (Q3) value
        s = save_anomaly(row, soil_or_veg, mn, q1, q2, q3, mx)
        _anomalies.append(s)
        return not_beta

    a, b = scaled_beta_parameters(q1, 0.25, q3, 0.75, mn, mx)
    return a, b


def save_beta_args(summary_csv, beta_args_csv):
    """
    Read the summary statistics from ``summary_csv``. Compute the best matching alpha
    and beta arguments for a Beta distribution, and save these to ``beta_args_csv``.

    :param summary_csv: (str) pathname of CSV with 6 different stats for each row
    :param beta_args_csv: (str) pathname of CSV file holding computed Beta
        distribution arguments.
    :return: none
    """
    _logger.debug(f"Reading '{summary_csv}'")
    df = pd.read_csv(summary_csv)

    col_order = ['GCAM_region_ID', 'Land_Type', 'GLU',
                 'soil_c_min', 'soil_c_q1', 'soil_c_median',
                 'soil_c_avg', 'soil_c_q3', 'soil_c_max',
                 'veg_c_min', 'veg_c_q1', 'veg_c_median',
                 'veg_c_avg', 'veg_c_q3', 'veg_c_max'
                 ]
    df = df[col_order]

    # start with empty lists
    _anomalies.clear()
    _bad_minimum.clear()

    def extract_params(soil_or_veg):
        params = df.apply(lambda row: get_beta_params_from_row(row, soil_or_veg),
                          axis='columns', result_type='expand')
        params.rename({0: soil_or_veg + '_alpha', 1: soil_or_veg + '_beta'}, axis='columns', inplace=True)
        return params

    _logger.debug("Extracting parameters for veg_c...")
    veg_params = extract_params("veg")

    _logger.debug("Extracting parameters for soil_c...")
    soil_params = extract_params("soil")

    df = pd.concat([df, soil_params, veg_params], axis='columns', sort=False)
    _logger.info(f"Writing '{beta_args_csv}'")
    df.to_csv(beta_args_csv, index=False)

    if _bad_minimum:
        bad_min_csv = f'{HOME}/tmp/moirai/moirai-beta-args-bad-min.csv'
        _logger.warning(f"Writing {len(_bad_minimum)} rows to '{bad_min_csv}'")
        bad_min_df = pd.DataFrame(data=_bad_minimum)
        bad_min_df.to_csv(bad_min_csv, index=False)

    if _anomalies:
        anomalies_csv = f'{HOME}/tmp/moirai/moirai-beta-args-anomalies.csv'
        _logger.warning(f"Writing {len(_anomalies)} rows to '{anomalies_csv}'")
        anom = pd.DataFrame(data=_anomalies)
        anom.to_csv(anomalies_csv, index=False)
    else:
        _logger.info("No data anomalies detected.")

def var_name(land, pool):
    return f"{land}-{pool}-c"

class MoiraiDataSystem(GcamDataSystem):

    def __init__(self, mapper, moirai_beta_args_csv=None, **kwargs):
        from itertools import product

        super().__init__(mapper, **kwargs)

        self.moirai_beta_args_csv = moirai_beta_args_csv

        self.trial_data = mapper.read_trial_data_file()

        self.land_types = ('cropland', 'forest', 'pasture', 'grass-shrub')
        self.c_pools = ('veg', 'soil')

        # Maps GCAM data system land types into names used in MCS variables
        self.land_type_map = {'Cropland'  : 'cropland',
                              'Forest'    : 'forest',
                              'Pasture'   : 'pasture',
                              'Grassland' : 'grass-shrub',
                              'Shrubland' : 'grass-shrub',
                              'RockIceDesert' : None,   # for these we always use median from Beta distro
                              'Tundra'        : None,
                              'UrbanLand'     : None,
                              }

        # Check that required cols are present (e.g., "cropland-veg-c", "forest-soil-c", ...)
        required = {var_name(land, pool) for land, pool in product(self.land_types, self.c_pools)}

        present = set(self.trial_data.columns)
        missing = required - present
        if missing:
            raise PygcamException(f"{__name__}: trial_data is missing columns {missing}")

    def saved_draws_csv_for_trial(self, trial_num):
        # Performs setup if needed. Set delete=False to debug moirai-draws.csv.
        tmp_sandbox_dir = self.trial_sandbox(trial_num)
        saved_draws_csv = Path(tmp_sandbox_dir, 'moirai-draws.csv')
        return saved_draws_csv

    def trial_func(self, trial_num):
        """
        Called for each trial identified when calling the run() method, before
        running drake to build the dependent XML files.
        """
        # the pathname of a CSV file into which to store values to use for
        # carbon densities, stored in columns 'soil-c' and 'veg-c'.
        self.saved_draws_csv = self.saved_draws_csv_for_trial(trial_num)

        # Insert the pathname of the CSV file containing the draws to use into the R string
        r_code_str = str_replace_from_dict(r_code_template,
                                           {'{{SAVED-DRAWS-CSV}}': self.saved_draws_csv,
                                            '{{USER-MOD-FUNC-NAME}}': USER_MOD_FUNC_NAME})

        _logger.info(f"trial_func: loading R code to read C values from '{self.saved_draws_csv}'")
        load_R_code(r_code_str)

        # Save a trial-specific CSV file with soil and veg C densities for all GLU / land type combos
        self.draw_carbon(trial_num)

    def draw_carbon(self, trial_num):
        """
        Draw values for soil carbon for all rows in the DataFrame df based on the assumed
        Beta distribution defined by the Q1 and Q3 values, scaled using the max and min values.

        :param trial_num: (int) the number of the trial being run.
        :return: none (the DataFrame is updated to include a column 'soil_c' containing
            the draw for each row.
        """
        def _draw_c(row, soil_or_veg, percentile):
            alpha = row[soil_or_veg + '_alpha']
            beta = row[soil_or_veg + '_beta']
            c_max = row[soil_or_veg + '_c_max']
            c_min = row[soil_or_veg + '_c_min']
            delta = c_max - c_min
            q3 = row[soil_or_veg + '_c_q3']

            if percentile is None or alpha < 0.0:
                return q3     # return the GCAM default

            if c_max == 0:
                return 0.0

            if delta == 0:
                return c_min  # or c_max; they're the same

            rv = stats.beta(alpha, beta)
            raw = rv.ppf(percentile)
            carbon = raw * delta + c_min
            return carbon

        args_df = pd.read_csv(self.moirai_beta_args_csv)
        percentiles = self.trial_data.loc[trial_num]

        # create the CSV file with C values to be read by the data system R script
        draws_df = args_df[['GCAM_region_ID', 'Land_Type', 'GLU']].copy()

        for gcam_land_type, var_land_type in self.land_type_map.items():
            # For RockIceDesert, UrbanLand, and Tundra, we always draw the median value from the Beta distro
            soil_percentile = percentiles[var_name(var_land_type, 'soil')] if var_land_type else None
            veg_percentile  = percentiles[var_name(var_land_type, 'veg')]  if var_land_type else None

            rows = args_df.query('Land_Type == @gcam_land_type')

            draws_df.loc[rows.index, 'soil_c'] = rows.apply(lambda row: _draw_c(row, 'soil', soil_percentile), axis='columns')
            draws_df.loc[rows.index, 'veg_c']  = rows.apply(lambda row: _draw_c(row, 'veg', veg_percentile),   axis='columns')

        _logger.info(f"Writing '{self.saved_draws_csv}'")
        draws_df.to_csv(self.saved_draws_csv, index=None)

class MoiraiCommand(SubcommandABC):
    def __init__(self, subparsers):
        import argparse

        kwargs = {'help' : '''Setup up an MCS to use moirai data.''',
                  'description' : f'''Perform various processing steps with data 
                  from Moirai for use in an MCS with GCAM.
                    
{_instructions}''',
                  'formatter_class': argparse.RawDescriptionHelpFormatter}

        super().__init__('moirai', subparsers, kwargs)

    def addArgs(self, parser):
        data_dir = getParam('Moirai.DataDir') or '.'

        summary_csv   = Path(data_dir, 'moirai-summary-wide.csv')
        beta_args_csv = Path(data_dir, 'moirai-beta-args.csv')

        parser.add_argument('-b', '--save-beta-args', action='store_true',
                            help='''Compute alpha and beta for each row and save composite moirai data 
                            with these columns''')

        parser.add_argument('-B', '--moirai-beta-args-csv', default=beta_args_csv,
                            help=f'''The pathname of the CSV file with the alpha and beta parameters
                                     defining each row's Beta distribution. Default is "{beta_args_csv}".''')

        ref_gcamdata = getParam('GCAM.RefGcamData')
        parser.add_argument('-c', '--create-baseline', action='store_true',
                            help=f'''Run drake in the reference workspace's gcamdata directory (the 
                                value of config variable "GCAM.RefGcamData", currently "{ref_gcamdata}"), 
                                without user modifications, to create the baseline drake data against 
                                which modifications are made.''')

        parser.add_argument('-G', '--gen-xml', action='store_true',
                            help='''Generate XML files for each of the trials in trialData.csv''')

        parser.add_argument('-g', '--group', default='',
                            help='''The name of a scenario group to process.''')

        parser.add_argument('-l', '--soil', default=0.5, type=float, dest='soil_percentile',
                            help='''The percentile value to draw for each row of moirai soil C data. Data
                                are written to the file indicated by the --saved-draws-csv parameter''')

        parser.add_argument('-v', '--veg', default=0.5, type=float, dest='veg_percentile',
                            help='''The percentile value to draw for each row of moirai vegetative C data. Data
                                are written to the file indicated by the --saved-draws-csv parameter''')

        parser.add_argument('-m', '--save-moirai-summary', action='store_true',
                            help=f'''Run the data system 6 times to produce C densities using each of the 6 
                                available statistics and save the results to the path indicated by 
                                --moirai-summary-csv.''')

        parser.add_argument('-M', '--moirai-summary-csv', default=summary_csv,
                            help=f'''The pathname of the CSV file containing composite moirai statistics.
                                Default is "{summary_csv}"''')

        parser.add_argument('-N', '--no-delete', action='store_true',
                            help='''Don't delete the temporary directory in which the data system is run.
                            May be useful for debugging.''')

        parser.add_argument('-r', '--renv', default=DEFAULT_RENV_DIR,
                            help=f'''An renv to load. Default is "{DEFAULT_RENV_DIR}".''')

        parser.add_argument('-s', '--simId', type=int, default=1,
                            help="The integer ID for the simulation to operate on. Default is 1.")

        parser.add_argument('-S', '--scenario', default='base',
                            help="The name of the scenario to generate XML for (where to copy moirai-depended XMLs)")

        parser.add_argument('-T', '--trialData', default=None,
                            help='''The pathname of the trialData.csv file. If not specified, uses the 
                                standard trialData.csv path for the indicated simulation.''')

        parser.add_argument('-t', '--trials', type=str,
                             help='''Comma-separated list of trial numbers and/or hyphen-separated 
                             ranges of trial numbers for which to generate XML. Ex: 1,4,6-10,3.
                             As a special case, the string "PATH" is recognized and parsed to extract
                             the trial number.''')
        return parser

    def run(self, args, tool):
        from pygcam.mcs.sim_file_mapper import SimFileMapper

        mapper = (tool.mapper or
                  SimFileMapper(project_name=args.projectName,
                                scenario=args.scenario,         # TBD: added this; need to test
                                scenario_group=args.group,
                                sim_id=args.simId))

        moirai_summary_csv = args.moirai_summary_csv
        moirai_beta_args_csv = args.moirai_beta_args_csv
        create_baseline = args.create_baseline
        delete = not args.no_delete

        if args.save_moirai_summary:
            save_moirai_summary(moirai_summary_csv, args.renv)

        if args.save_beta_args:
            save_beta_args(moirai_summary_csv, moirai_beta_args_csv)

        if args.gen_xml or create_baseline:
            obj = MoiraiDataSystem(mapper,
                                   moirai_beta_args_csv=moirai_beta_args_csv,
                                   renv_dir=args.renv)

            # If we're creating the baseline, run the data system without any user modifications
            obj.run_data_system(args.trials, None if create_baseline else USER_MOD_FUNC_NAME,
                                delete=delete)

            _logger.debug("Finished running data system")


PluginClass = MoiraiCommand
