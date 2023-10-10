import os
import pytest
from pygcam.config import setSection, getParam, pathjoin
from pygcam.constants import LOCAL_XML_NAME
from pygcam.file_mapper import FileMapper
from pygcam.gcam_path import makeDirPath, GcamPath, gcam_path
from pygcam.mcs.context import McsContext
from pygcam.mcs.sim_file_mapper import SimFileMapper
from .utils_for_testing import load_config_from_string

exe_dir = '/tmp/foo/exe'
rel_path = "../input/xml/whatever.xml"

@pytest.fixture(scope="module")
def gp():
    return GcamPath(exe_dir, rel_path, create=True)

def test_rel_path(gp):
    assert gp.rel == rel_path
    assert gp.abs == '/tmp/foo/input/xml/whatever.xml'

def test_get_path(gp):
    assert gcam_path("/foo/bar/baz") == "/foo/bar/baz"

    assert gcam_path(gp) == gp.abs
    assert gcam_path(gp, abs=False) == gp.rel


def test_dir_path():
    from pygcam.error import SetupException
    from pygcam.file_utils import removeFileOrTree

    # makeDirPath(*elements, require=False, normpath=True, create=False, mode=0o775)
    assert makeDirPath("/foo", "bar", "baz") == "/foo/bar/baz"

    with pytest.raises(SetupException, match=f'Required path .* does not exist.'):
        makeDirPath("/foo", "bar", "baz", require=True)

    path = makeDirPath("/tmp/test_dir_path", "foo", "bar", "baz", create=True)
    assert path == '/tmp/test_dir_path/foo/bar/baz'

    assert makeDirPath("/tmp", "test_dir_path", "foo", "bar", "baz", require=True) == path
    removeFileOrTree("/tmp/test_dir_path")


def test_sandbox():
    scenario = 'tax-10'
    group_name = 'group1'   # group1 has useSubdir="1"; group2 has "0"

    tmp_dir = '/tmp/test_gcam_sandbox'
    sandbox_root = f'{tmp_dir}/sandboxes'

    project_name = 'test-project'
    project_root = pathjoin(os.path.dirname(__file__), 'data')
    project_subdir = 'analysis_22'

    ref_workspace = '/Volumes/Plevin1TB/Software/GCAM/6.0/gcam-core'

    # Create a config section
    cfg_text = f"""[{project_name}]
        GCAM.ProjectRoot = {project_root}
        GCAM.ProjectName = {project_name}
        GCAM.ProjectSubdir = {project_subdir}
        GCAM.SandboxRoot = {sandbox_root}
        GCAM.SandboxProjectDir = {sandbox_root}/{project_name}
        GCAM.RefWorkspace = {ref_workspace}
        MCS.SandboxRoot = {tmp_dir}/mcs
    """

    # load the config text and make the new section the default
    load_config_from_string(cfg_text)
    setSection(project_name)

    # With group dir
    # scenario, projectName=None, scenarioGroup=None,
    #                  scenariosFile=None, parent=None, createDirs=True)
    mapper = FileMapper(scenario, scenario_group=group_name, create_dirs=False)

    assert mapper.sandbox_workspace == pathjoin(sandbox_root, project_name, project_subdir, 'Workspace', normpath=True)
    assert mapper.sandbox_exe_path  == pathjoin(sandbox_root, project_name, project_subdir, group_name,
                                                scenario, "exe/gcam.exe", normpath=True)
    assert gcam_path(mapper.sandbox_scenario_xml) == pathjoin(sandbox_root, project_name, project_subdir, LOCAL_XML_NAME, scenario, normpath=True)

    xmlsrc = getParam('GCAM.ProjectXmlsrc')
    assert mapper.project_xml_src == xmlsrc

    #
    # MCS sandbox test
    #
    group_name = 'group2'    # group2 sets useGroupDir="0"
    sim_id = 1
    trial_num = 20
    mcs_root = f"{tmp_dir}/mcs"

    ctx = McsContext(projectName=project_name, scenario=scenario, groupName=group_name, simId=sim_id, trialNum=trial_num)
    mapper = SimFileMapper(context=ctx, scenario_group=group_name, create_dirs=True) # this one creates the directories; the one above does not

    assert mapper.sandbox_exe_path == pathjoin(mcs_root, project_name, project_subdir, # group_name,
                                               f"sims/s{sim_id:03}/000/{trial_num:03}",
                                               scenario, "exe/gcam.exe", normpath=True)

