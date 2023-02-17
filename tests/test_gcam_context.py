import pytest
from pygcam.config import getConfig, setParam, getSection
from pygcam.gcam_context import GcamPath, gcam_path, GcamContext, makeDirPath

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


def test_context():
    getConfig()

    baseline = 'base'
    scenario = 'policy'
    group_name = 'group1'

    test_dir = '/tmp/test_gcam_context'
    project_name = 'gcam_mcs'
    project_root = f'{test_dir}/projects'
    sandbox_root = f'{test_dir}/sandboxes'
    ref_workspace = '/Volumes/Plevin1TB/Software/GCAM/6.0/gcam-core'

    # Set key parameters to ensure consistency when testing
    params = (
        ('GCAM.ProjectRoot', project_root),
        ('GCAM.ProjectName', project_name),
        ('GCAM.XmlSrcDir', f'{project_root}/{project_name}/xmlsrc'),
        ('GCAM.SandboxRoot', sandbox_root),
        ('GCAM.SandboxProjectDir', f'{sandbox_root}/{project_name}'),
        ('GCAM.RefWorkspace', ref_workspace),
    )

    section = getSection()
    for name, value in params:
        setParam(name, value, section=section)

    ctx = GcamContext(baseline, scenario, scenarioGroup=group_name,
                 xmlSourceDir=None, xmlGroupSubdir=None,
                 sandboxRoot=None, sandboxGroupSubdir=None, createDirs=False)

    assert ctx.sandboxRefWorkspace == f"{sandbox_root}/{project_name}/Workspace"

    assert ctx.sandboxExePath == f"{sandbox_root}/{project_name}/{group_name}/{scenario}/exe/gcam.exe"

    assert gcam_path(ctx.gcam_xml) == f"{sandbox_root}/{project_name}/{group_name}/{scenario}/input/gcamdata/xml"


def test_dir_path():
    from pygcam.error import SetupException
    from pygcam.utils import removeFileOrTree

    # makeDirPath(*elements, require=False, normpath=True, create=False, mode=0o775)
    assert makeDirPath("/foo", "bar", "baz") == "/foo/bar/baz"

    with pytest.raises(SetupException, match=f'Required path .* does not exist.'):
        makeDirPath("/foo", "bar", "baz", require=True)

    path = makeDirPath("/tmp/test_dir_path", "foo", "bar", "baz", create=True)
    assert path == '/tmp/test_dir_path/foo/bar/baz'

    assert makeDirPath("/tmp", "test_dir_path", "foo", "bar", "baz", require=True) == path
    removeFileOrTree("/tmp/test_dir_path")

