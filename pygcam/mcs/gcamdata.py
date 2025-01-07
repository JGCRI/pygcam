import os
from pathlib import Path
import shutil

from ..config import getParamAsPath, getParamAsBoolean
from ..constants import TRIAL_XML_NAME, FileVersions
from ..log import getLogger
from ..file_utils import pushd
from ..XMLConfigFile import XMLConfigFile
from .sim_file_mapper import SimFileMapper
from .util import parseTrialString, parseMcsDir

_logger = getLogger(__name__)

# added to the base names of XML files that are updated by driver_drake()
DEFAULT_MODIFIER = '__drake'

def load_R_code(code_str):
    """
    Loads a string containing R code into the R interpreter running within Python.

    :param code_str: (str) R code string
    :return: none
    """
    from rpy2 import robjects   # imported in func to avoid starting R when this module loads

    robjects.r(code_str)

class GcamDataSystem(object):
    """
    Class to run the GCAM data system within a Monte Carlo simulation
    """

    def __init__(self, mapper : SimFileMapper, renv_dir=None, xml_modifier=None):
        """
        Class to manage running the GCAM data system in Monte Carlo Simulations.
        Designed to be subclassed with key methods handling application-specific
        requirements.

        :param mapper: (subclass of pygcam.AbstractFileMapper) pathname and directory info.
        :param renv_dir: (str) the directory in which an renv (an R environment lockfile)
            will be activated.
        :param xml_modifier: (str) The suffix to add to XML files generated by running
            "driver_drake". Default is "__drake".
        """
        self.mapper = mapper
        self.renv_dir = renv_dir
        self.xml_modifier = xml_modifier or DEFAULT_MODIFIER

        self.trial_sandbox_dict = dict()  # key = trial num; value is pathname of temp dir

        # Try loading R devtools at the start
        gcamdata_dir = mapper.ref_gcamdata_dir
        with pushd(gcamdata_dir):
            from rpy2.robjects.packages import importr
            devtools = importr('devtools')
            _logger.debug(f"Calling load_all('{gcamdata_dir}')")
            devtools.load_all(gcamdata_dir)

    def trial_func(self, trial_num):
        """
        A function to call for each Monte Carlo trial. Does nothing in ``GcamDataSystem``;
        subclass can define this if needed.

        :param trial_num: (int) the trial being run
        :return: none
        """
        return None

    def activate_renv(self):
        """
        Activate the "renv" at directory ``self.renv_dir``.

        :return: none
        """
        if self.renv_dir:
            from rpy2.robjects.packages import importr

            #importr('assertthat')
            renv = importr("renv")
            _logger.debug(f'Activating renv "{self.renv_dir}"')
            renv.activate(self.renv_dir)

    def load_gcamdata(self):
        """
        Call devtools::load_all(self.ref_gcamdata_dir).

        :return: none
        """
        from rpy2.robjects.packages import importr

        gcamdata_dir = self.mapper.ref_gcamdata_dir

        with pushd(gcamdata_dir):
            devtools = importr('devtools')
            _logger.debug(f"Calling load_all('{gcamdata_dir}')")
            devtools.load_all(gcamdata_dir)

    def run_drake(self, gcamdata_dir):
        """
        Run the gcamdata (R) function "driver_drake" in the given workspace.
        This is used to create the baseline drake information before running
        it with user modifications, and thus before copying the reference
        workspace to temporary trial sandboxes.

        :param gcamdata_dir: (str) the pathname of the gcamdata dir in which
            to run "driver_drake".
        :return: none
        """
        from rpy2 import robjects

        driver_drake = robjects.r["driver_drake"]
        with pushd(gcamdata_dir):
            driver_drake()

    def run_drake_with_mods(self, func_names):
        """
        Run the gcamdata (R) function "driver_drake", passing in the
        user modification functions in ``func_names``

        :param func_names: (str or list(str)) the function name or list of function
            names to pass as the "user_modifications" to "driver_drake".
        :return: none
        """
        from rpy2 import robjects
        from rpy2.robjects.packages import importr

        drake = importr('drake')
        drake.clean(list=func_names)

        driver_drake = robjects.r["driver_drake"]
        driver_drake(user_modifications=func_names, xml_suffix=self.xml_modifier)

    def trial_sandbox(self, trial_num, delete=True):
        """
        Return the path to a temporary sandbox directory in which to build dependent
        XML files. A cache of these is maintained so on subsequent calls with the same
        ``trial_num``, the cached path is returned and no other action is taken.

        :param trial_num: (int) the number of the trial being run
        :param delete: (bool) whether to delete the temporary directory created
            by this function at program exit.
        :return: (str) the trial's sandbox dir
        """
        from pygcam.temp_file import getTempDir

        # If we've already set it up, just return the pathname
        trial_sandbox_dir = self.trial_sandbox_dict.get(trial_num)
        if trial_sandbox_dir is not None:
            return trial_sandbox_dir

        gcamdata_dir = self.mapper.ref_gcamdata_dir

        # Use non-networked scratch dir for fastest I/O during the drake build.
        local_scratch = getParamAsPath('GCAM.LocalScratchDir')
        trial_sandbox_dir = getTempDir(suffix=f"-trial_{trial_num}",
                                       tmpDir=local_scratch,
                                       delete=delete) # delete dir when app exits
        _logger.debug(f"Sandbox is {trial_sandbox_dir}")

        # Remember the pathname for subsequent calls
        self.trial_sandbox_dict[trial_num] = trial_sandbox_dir

        # Can't hard link across file systems, so make mod time of the symlink
        # that the original to avoid confusing drake.
        to_link_with_times = ('data', 'data-raw', 'R', 'xml')

        for subdir in to_link_with_times:
            src_dir = Path(gcamdata_dir, subdir)
            dst_dir = Path(trial_sandbox_dir, subdir)
            dst_dir.mkdir(parents=True, exist_ok=True)

            src_files = src_dir.glob("*.*")
            for src_file in src_files:
                dst_file = Path(dst_dir, src_file.parts[-1])    # parts[-1] is basename
                dst_file.symlink_to(src_file)

                # Copy access and modification times from original to the symlink to convince drake
                stat = src_file.stat()
                os.utime(dst_file, times=(stat.st_atime, stat.st_mtime), follow_symlinks=False)

        # symlink all the read-only stuff not involved in dependencies; no need to bother setting times
        to_sym_link = ('DESCRIPTION', 'NAMESPACE', 'chunk-generator', 'inst', 'gcamdata.Rproj')
        for file in to_sym_link:
            src_file = Path(gcamdata_dir, file)
            dst_file = Path(trial_sandbox_dir, src_file.parts[-1])
            dst_file.symlink_to(src_file)

        src_dot_drake = Path(gcamdata_dir,  '.drake')
        dst_dot_drake = Path(trial_sandbox_dir, '.drake')
        shutil.copytree(src_dot_drake, dst_dot_drake)  # uses copy2 so it copies modification times

        return trial_sandbox_dir

    def run_data_system(self, trials, user_modifications, delete=True):
        """
        Run the GCAM data system using "driver_drake" to generate XML files with ``user_modifications``.

        :param trials: ("PATH" or a comma-delimited list of ints or hyphen-separated numbers
            indicating the trials to run. (Example: "1,4,7-11,2,21-50")
        :param user_modifications: (str or list of str) names of "user modification" R functions
            to insert into the GCAM data system for use with drake. If None, just run the data
            system in the reference workspace, without any modifications to create the baesline.
        :param delete: (bool) whether to delete the temporary directory in which the data system
            is run. Can be helpful to set to False for debugging.
        :return: none
        """

        # Apparently, this is not re-entrant, so activating causes some MCS trials
        # to abort. Skipping this works on the cluster but not locally on RP's Mac.
        # Not clear why this is the case...
        if getParamAsBoolean('GCAM.Renv.Activate'):
            self.activate_renv()

        #self.load_gcamdata()
        mapper = self.mapper

        if user_modifications is None:
            self.run_drake(mapper.ref_gcamdata_dir)
            return

        if trials == 'PATH':
            # extract the trial number from the current pathname (an "exe" dir)
            cur_dir = Path(os.curdir).absolute()
            trial_num = parseMcsDir(cur_dir, trialNum_only=True)
            trial_list = [trial_num]
        else:
            trial_list = parseTrialString(trials)

        trial_rel_xml = Path(f'{TRIAL_XML_NAME}/input/gcamdata/xml')

        for trial in trial_list:
            _logger.info(f'Generating XML for trial {trial}')

            # sim_dir = getSimDir(sim_id)
            # trial_dir = dirFromNumber(trial, prefix=sim_dir, create=True)
            trial_dir = mapper.trial_dir(create=True)

            # sandbox_dir = self.trial_sandbox(trial)
            # sandbox_dir = mapper.trial_scenario_dir()

            self.trial_func(trial)

            # trial_sandbox returns the path to a temporary sandbox directory in which
            # to build dependent XML files. It's created on demand and cached for re-use.
            tmp_sandbox_dir = self.trial_sandbox(trial, delete=delete)

            # run driver_drake() in the reference workspace with user_modification established above
            with pushd(tmp_sandbox_dir):
                self.run_drake_with_mods(user_modifications)

            # Move XML files into the trial-xml directory
            sandbox_xml_dir = Path(tmp_sandbox_dir, 'xml')
            dst_dir = Path(trial_dir, trial_rel_xml)
            dst_dir.mkdir(parents=True, exist_ok=True)
            abs_paths = self.move_modified_xml_files(sandbox_xml_dir, dst_dir)

            rel_dir = Path('../..', trial_rel_xml)
            self.update_scenario_config(rel_dir, abs_paths)

    def update_scenario_config(self, rel_dir: Path, abs_paths):
        """
        Update the configuration XML file for the ``simId`` and ``scenario`` found in
        the saved ``mapper``,  substituting the path to the modified XML for the file
        ending with the same basename. This assumes basenames within the config file
        are unique.

        :param rel_dir: (Path) the directory that holds the modified XML files,
            relative to the "exe" directory for the given scenario, suitable
            for insertion into the configuration XML file.)
        :param abs_paths: (list of Path) the absolute paths of the modified XML
            files.
        :return: none
        """
        mapper = self.mapper

        # We read and re-write trial-xml/{scenario}/config.xml
        cfg_path = mapper.get_config_version(version=FileVersions.TRIAL_XML)
        _logger.debug(f"gcamdata: reading config file '{cfg_path}'")
        scen_config = XMLConfigFile.get_instance(cfg_path)

        # dict of file_basename => (tag, rel_path) for all ScenarioComponent elements
        file_dict = scen_config.get_component_dict()

        # update the config file, which, for each scenario, is shared across trials
        for abs_path in abs_paths:
            basename = abs_path.parts[-1]
            try:
                tag, rel_path = file_dict[basename]
            except KeyError:
                _logger.warning(
                    f"Ignoring file with basename '{basename}': not found in ref config file '{cfg_path}'")
                continue

            new_path = rel_dir / basename
            _logger.debug(f"gcamdata: updating config component '{tag}' to path '{new_path}'")

            scen_config.update_component_pathname(tag, new_path)

        # Write this to trial-xml dir since each trial will be doing the same thing
        trial_config_path = mapper.get_config_version(version=FileVersions.TRIAL_XML)
        scen_config.write(path=trial_config_path)

    def move_without_stem_modifier(self, src_paths, dst_dir):
        modifier_len = len(self.xml_modifier)

        dst_paths = []
        for src_path in src_paths:
            without_modifier = src_path.stem[:-modifier_len]
            dst_path = Path(dst_dir,  without_modifier + src_path.suffix)
            shutil.move(src_path, dst_path) # renames if same filesystem, else copies & deletes
            dst_paths.append(dst_path)

        return dst_paths

    def move_modified_xml_files(self, src_dir, dst_dir):
        """
        Move modified XML files from the temporary source directory
        ``src_dir`` to the destination directory ``dst_dir``.

        :param src_dir: (str) the source directory
        :param dst_dir: (str) the destination directory
        :return: (list of str) the paths to the modified XML files
           in the destination directory
        """
        src_dir = Path(src_dir)
        modified = src_dir.glob(f'*{self.xml_modifier}.xml')
        if not modified:
            _logger.warn(f"No modified XML files found in '{src_dir}' (modifier='{self.xml_modifier}')")
            return

        dst_paths = self.move_without_stem_modifier(modified, dst_dir)
        return dst_paths
