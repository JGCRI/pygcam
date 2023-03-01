import os
from pathlib import Path
from rpy2 import robjects
from rpy2.robjects.packages import importr
import shutil

from ..log import getLogger
from ..config import getParam
from ..file_utils import pushd
from .util import parseTrialString, parseMcsDir, getSimDir, dirFromNumber

_logger = getLogger(__name__)

# added to the base names of XML files that are updated by driver_drake()
DEFAULT_MODIFIER = '__drake'

def str_replace_from_dict(s, d):
    """
    Return a copy of ``s`` after replacing each key in the ``d`` dict found
    in the ``s`` with the corresponding value.

    :param s: (str) the string into which substitutions are made
    :param d: (dict) dictionary of values that should be substituted
        in the ``s``. Each instance of a key is replaced, if found, with its value.
    :return:
    """
    for key, value in d.items():
        s = s.replace(key, str(value))

    return s

def load_R_code(code_str):
    robjects.r(code_str)

class GcamDataSystem(object):

    def __init__(self, sim_id, scenario, gcamdata_dir, renv_dir=None, xml_modifier=None):
        """
        Class to manage running the GCAM data system in Monte Carlo Simulations.
        Designed to be subclassed with key methods handling application-specific
        requirements.

        :param gcamdata_dir: (str) the directory from which to load all R assets.
        :param xml_modifier: (str) The suffix to add to XML files generated by running
            "driver_drake". Default is "__drake".
        """
        self.sim_id = sim_id
        self.scenario = scenario
        self.renv_dir = renv_dir
        self.xml_modifier = xml_modifier or DEFAULT_MODIFIER
        self.gcamdata_dir = gcamdata_dir  or getParam('GCAM.RefGcamData')

        self.trial_sandbox_dict = dict()  # key = trial num; value is pathname of temp dir

    def trial_func(self, trial_num):
        # Subclass can define if needed
        return None

    def activate_renv(self):
        """
        Activate the "renv" at directory ``self.renv_dir``.

        :return: none
        """
        if self.renv_dir:
            #importr('assertthat')
            renv = importr("renv")
            renv.activate(self.renv_dir)

    def load_gcamdata(self):
        """
        Call devtools::load_all(self.ref_gcamdata_dir).

        :return: none
        """
        devtools = importr('devtools')
        _logger.debug(f"Calling load_all('{self.gcamdata_dir}')")
        devtools.load_all(self.gcamdata_dir)

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
        drake = importr('drake')
        drake.clean(list=func_names)

        driver_drake = robjects.r["driver_drake"]
        driver_drake(user_modifications=func_names, xml_suffix=self.xml_modifier)

    def trial_sandbox(self, trial_num, delete=True):
        """
        Return the path to a temporary sandbox directory in which to build dependent
        XML files. A cache of these is maintained so on subsequent calls with the same
        ``trial_num``, the cached path is returned and no other action is taken.
        """
        from pygcam.temp_file import getTempDir

        # If we've already set it up, just return the pathname
        trial_sandbox_dir = self.trial_sandbox_dict.get(trial_num)
        if trial_sandbox_dir is not None:
            return trial_sandbox_dir

        gcamdata_dir = self.gcamdata_dir

        # temp dir is automatically deleted when app exits
        trial_sandbox_dir = getTempDir(suffix=f"-trial_{trial_num}", delete=delete)
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

    def run_data_system(self, trials, user_modifications):
        """
        Run the GCAM data system using "driver_drake" to generate XML files with ``user_modifications``.

        :param trials: ("PATH" or a comma-delimited list of ints or hyphen-separated numbers
            indicating the trials to run. (Example: "1,4,7-11,2,21-50")

        :param user_modifications: (str or list of str) names of "user modification" R functions
            to insert into the GCAM data system for use with drake. If None, just run the data
            system in the reference workspace, without any modifications to create the baesline.
        :return: none
        """
        self.activate_renv()
        self.load_gcamdata()

        if user_modifications is None:
            self.run_drake(self.gcamdata_dir)
            return

        if trials == 'PATH':
            # extract the trial number from the current pathname (an "exe" dir)
            cur_dir = Path(os.curdir).absolute()
            trial_num = parseMcsDir(cur_dir, trialNum_only=True)
            trial_list = [trial_num]
        else:
            trial_list = parseTrialString(trials)

        trial_rel_xml = Path('trial-xml/input/gcamdata/xml')

        updated_config = False

        for trial in trial_list:
            _logger.info(f'Generating XML for trial {trial}')

            sim_dir = getSimDir(self.sim_id)
            trial_dir = dirFromNumber(trial, prefix=sim_dir, create=True)
            sandbox_dir = self.trial_sandbox(trial)

            self.trial_func(trial)

            # run driver_drake() in the reference workspace with user_modification established above
            with pushd(sandbox_dir):
                self.run_drake_with_mods(user_modifications)

            # Move XML files into the trial-xml directory
            sandbox_xml_dir = Path(sandbox_dir, 'xml')
            dst_dir = Path(trial_dir, trial_rel_xml)
            dst_dir.mkdir(parents=True, exist_ok=True)
            abs_paths = self.move_modified_xml_files(sandbox_xml_dir, dst_dir)

            # The scenario config file needs to be updated only once since it's shared by
            # (and uses the same relative path for) all trials in a scenario
            if not updated_config:
                rel_dir = Path('../..', trial_rel_xml)
                self.update_scenario_config(rel_dir, abs_paths)
                updated_config = True

    def update_scenario_config(self, rel_dir, abs_paths):
        """
        Update the configuration XML file for the given ``simId`` and ``scenario``,
        substituting the path to the modified XML for the file ending with the same
        basename. This, of course, assumes basenames within the config file are unique.

        :param simId: (int) simulation ID (usually 1)
        :param scenario: (str) the name of the scenario
        :param rel_dir: (Path) the directory that holds the modified XML files,
            relative to the "exe" directory for the given scenario, suitable
            for insertion into the configuration XML file.)
        :param abs_paths: (list of Path) the absolute paths of the modified XML
            files.
        :return: none
        """
        from pygcam.mcs.context import McsContext
        from pygcam.mcs.XMLConfigFile import XMLConfigFile

        ctx = McsContext(simId=self.sim_id, scenario=self.scenario)
        scen_config = XMLConfigFile(ctx)
        scen_config_path = scen_config.getFilename()
        _logger.debug(f"Updating config file '{scen_config_path}'")

        # extract tuples of (file_tag, file_path) for all XML components
        file_refs = scen_config.tree.xpath('//ScenarioComponents/Value')
        file_dict = {os.path.basename(elt.text): (elt.attrib['name'], elt.text) for elt in file_refs}

        # update the config file, which, for each scenario, is shared across trials
        for abs_path in abs_paths:
            basename = abs_path.parts[-1]
            try:
                tag, rel_path = file_dict[basename]
            except KeyError:
                _logger.warning(
                    f"Ignoring file with basename '{basename}': not found in ref config file '{scen_config_path}'")
                continue

            new_path = rel_dir / basename
            _logger.debug(f"Updating config component '{tag}' to path '{new_path}'")

            scen_config.updateComponentPathname(tag, new_path)

        scen_config.write()


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
        src_dir = Path(src_dir)
        modified = src_dir.glob(f'*{self.xml_modifier}.xml')
        if not modified:
            _logger.warn(f"No modified XML files found in '{src_dir}' (modifier='{self.xml_modifier}')")
            return

        dst_paths = self.move_without_stem_modifier(modified, dst_dir)
        return dst_paths
