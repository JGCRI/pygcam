import pytest
from pygcam.config import setSection, getParam
from pygcam.sandbox import Sandbox, GcamPath, gcam_path, makeDirPath
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
    baseline = 'base'
    scenario = 'policy'
    group_name = 'group1'

    test_dir = '/tmp/test_gcam_context'
    project_name = 'test-project'
    project_root = f'{test_dir}/projects'
    sandbox_root = f'{test_dir}/sandboxes'
    ref_workspace = '/Volumes/Plevin1TB/Software/GCAM/6.0/gcam-core'

    # Create a config section
    cfg_text = f"""[{project_name}]
        GCAM.ProjectRoot = {project_root}
        GCAM.ProjectName = {project_name}
        GCAM.ProjectXmlsrc = {project_root}/{project_name}/xmlsrc
        GCAM.SandboxRoot = {sandbox_root}
        GCAM.SandboxProjectDir = {sandbox_root}/{project_name}
        GCAM.RefWorkspace = {ref_workspace}
    """

    # load the config text and make the new section the default
    load_config_from_string(cfg_text)
    setSection(project_name)

    # With group dir
    sbx = Sandbox(baseline, scenario, scenarioGroup=group_name, useGroupDir=True,
                  projectXmlsrc=None, xmlsrcSubdir=None,
                  sandboxRoot=None, sandboxSubdir=None, createDirs=False)

    assert sbx.sandbox_workspace == f"{sandbox_root}/{project_name}/Workspace"
    assert sbx.sandbox_exe_path == f"{sandbox_root}/{project_name}/{group_name}/{scenario}/exe/gcam.exe"
    assert gcam_path(sbx.scenario_gcam_xml_dir) == f"{sandbox_root}/{project_name}/{group_name}/{scenario}/input/gcamdata/xml"

    xmlsrc = getParam('GCAM.ProjectXmlsrc')
    assert sbx.scenario_xmlsrc_dir == f"{xmlsrc}/{group_name}/{scenario}"

    # Without group dir
    sbx = Sandbox(baseline, scenario, scenarioGroup=group_name, useGroupDir=False,
                  projectXmlsrc=None, xmlsrcSubdir=None,
                  sandboxRoot=None, sandboxSubdir=None, createDirs=False)

    assert sbx.sandbox_exe_path == f"{sandbox_root}/{project_name}/{scenario}/exe/gcam.exe"
    assert gcam_path(sbx.scenario_gcam_xml_dir) == f"{sandbox_root}/{project_name}/{scenario}/input/gcamdata/xml"

    assert sbx.scenario_xmlsrc_dir == f"{xmlsrc}/{scenario}"       # without group name

