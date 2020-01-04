'''
.. Support for 'setup' sub-command, which sets up / customizes GCAM project's XML files.

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import os

from .config import getParam, getParamAsBoolean, pathjoin, parse_version_info
from .constants import LOCAL_XML_NAME, DYN_XML_NAME
from .error import SetupException
from .log import getLogger
from .utils import copyFileOrTree, removeFileOrTree, mkdirs, symlinkOrCopyFile, removeTreeSafely, pushd

_logger = getLogger(__name__)

def _getFilesToCopyAndLink(linkParam):
    reqFiles = getParam('GCAM.RequiredFiles')
    allFiles = set(reqFiles.split())

    # Subtract from the set of all files the ones to link
    toLink = getParam(linkParam)
    filesToLink = toLink.split()
    filesToLinkSet = set(filesToLink)

    unknownFiles = filesToLinkSet - allFiles
    if unknownFiles:
        _logger.warn('Ignoring unknown files specified in %s: %s' % (linkParam, list(unknownFiles)))
        filesToLinkSet -= unknownFiles

    # Copy everything that is not in the filesToLinkSet
    filesToCopy = list(allFiles - filesToLinkSet)
    return filesToCopy, filesToLink

def _remakeSymLink(source, linkname):
    removeFileOrTree(linkname)
    symlinkOrCopyFile(source, linkname)

def _workspaceLinkOrCopy(src, srcWorkspace, dstWorkspace, copyFiles=False):
    '''
    Create a link (or copy) in the new workspace to the
    equivalent file in the given source workspace.
    '''
    # Set automatically on Windows for users without symlink permission
    copyFiles = copyFiles or getParamAsBoolean('GCAM.CopyAllFiles')
    linkFiles = not copyFiles

    if os.path.isabs(src):
        # if absolute path, append only the basename to the runWorkspace
        srcPath = src
        dstPath = pathjoin(dstWorkspace, os.path.basename(os.path.normpath(src)))
    else:
        # if relative path, append the whole thing to both workspaces
        srcPath = pathjoin(srcWorkspace, src)
        dstPath = pathjoin(dstWorkspace, src)

    # Ensure that parent directory exists
    parent = os.path.dirname(dstPath)
    mkdirs(parent)

    # If dstPath is a link, we always remove it and either recreate
    # the link or copy the files as required. If dstPath isn't a
    # link, we remove it only if we are replacing it with a link.
    if os.path.lexists(dstPath) and (linkFiles or os.path.islink(dstPath)):
        removeFileOrTree(dstPath)

    # We've removed dstPath unless we're avoiding re-copying srcPath
    if not os.path.lexists(dstPath):
        if copyFiles:
            _logger.info('Copying %s to %s' % (srcPath, dstPath))
            copyFileOrTree(srcPath, dstPath)
        else:
            symlinkOrCopyFile(srcPath, dstPath)


def createSandbox(sandbox, srcWorkspace=None, forceCreate=False, mcsMode=None):
    '''
    Set up a run-time sandbox in which to run GCAM. This involves copying
    from or linking to files and directories in `workspace`, which defaults
    to the value of config parameter GCAM.SandboxRefWorkspace.

    :param sandbox: (str) the directory to create
    :param srcWorkspace: (str) the workspace to link to or copy from
    :param forceCreate: (bool) if True, delete and recreate the sandbox
    :param mcsMode: ('gensim', 'trial', or None) perform setup appropriate
       for pygcam-mcs trials.
    :return: none
    '''
    from semver import VersionInfo

    if not srcWorkspace:
        srcWorkspace = getParam('GCAM.RefWorkspace') if mcsMode == 'gensim' \
            else getParam('GCAM.SandboxRefWorkspace')

    # MCS "new" sub-command creates its ref workspace; for non-MCS
    # we do it here, on demand, i.e., if it doesn't exist already.
    if not mcsMode:
        copyWorkspace(srcWorkspace, forceCreate=forceCreate)

    if mcsMode and getParamAsBoolean('GCAM.CopyAllFiles'):
        # Not prohibited; just a disk-hogging, suboptimal choice
        _logger.warn('GCAM.CopyAllFiles = True while running MCS')

    _logger.info("Setting up sandbox '%s'", sandbox)

    if os.path.lexists(sandbox) and os.path.samefile(sandbox, srcWorkspace):
        raise SetupException("The run sandbox is the same as the run workspace; no setup performed")

    if forceCreate:
        # avoid deleting the current directory
        with pushd('..'):
            removeTreeSafely(sandbox, ignore_errors=True)
            mkdirs(sandbox)

    # also makes sandbox and sandbox/exe
    logPath = pathjoin(sandbox, 'exe', 'logs')
    mkdirs(logPath)

    # Need to mkdir("exe/restart") for gcam-v5.1.2 (and beyond?)
    if parse_version_info() >= VersionInfo(5, 1, 2):
        restartDir = pathjoin(sandbox, 'exe', 'restart')
        mkdirs(restartDir)

    filesToCopy, filesToLink = _getFilesToCopyAndLink('GCAM.SandboxFilesToLink')

    for filename in filesToCopy:
        _workspaceLinkOrCopy(filename, srcWorkspace, sandbox, copyFiles=True)

    for filename in filesToLink:
        _workspaceLinkOrCopy(filename, srcWorkspace, sandbox, copyFiles=False)

    outputDir = pathjoin(sandbox, 'output')

    if mcsMode:
        from .mcs.util import createOutputDir
        # link {sandbox}/dyn-xml to ../dyn-xml
        dynXmlDir = pathjoin('..', DYN_XML_NAME)

        dynXmlAbsPath = pathjoin(os.path.dirname(sandbox), DYN_XML_NAME)
        mkdirs(dynXmlAbsPath)
        createOutputDir(outputDir) # deals with link and tmp dir...
    else:
        # link {sandbox}/dyn-xml to {refWorkspace}/dyn-xml
        dynXmlDir = pathjoin(srcWorkspace, DYN_XML_NAME)

        # Create a local output dir
        mkdirs(outputDir)

    dynXmlLink = pathjoin(sandbox, DYN_XML_NAME)
    _remakeSymLink(dynXmlDir, dynXmlLink)

    # static xml files are always linked to reference workspace
    localXmlDir  = pathjoin(srcWorkspace, LOCAL_XML_NAME)
    localXmlLink = pathjoin(sandbox, LOCAL_XML_NAME)
    _remakeSymLink(localXmlDir, localXmlLink)


def copyWorkspace(newWorkspace, refWorkspace=None, forceCreate=False, mcsMode=False):
    '''
    Create a copy of a reference workspace by linking to or copying files from
    `refWorkspace`, which defaults to the value of config parameter
    GCAM.RunWorkspace. The copied workspace is the basis for creating sandboxes
    for a Monte Carlo simulation or a non-MCS project.

    :param newWorkspace: (str) the directory to create
    :param refWorkspace: (str) the workspace to link to or copy from (defaults
       to the value of config parameter GCAM.RefWorkspace)
    :param forceCreate: (bool) if True, delete and recreate the sandbox
    :param mcsMode: (bool) if True, perform setup appropriate for gcammcs trials.
    :return: none
    '''
    version = getParam('GCAM.VersionNumber')
    _logger.info("Setting up GCAM workspace '%s' for GCAM %s", newWorkspace, version)

    refWorkspace = refWorkspace or getParam('GCAM.RefWorkspace')

    if os.path.lexists(newWorkspace) and os.path.samefile(newWorkspace, refWorkspace):
        raise SetupException("run workspace is the same as reference workspace; no setup performed")

    # We write a semaphore file when creating Workspace so we can tell
    # if we failed, in which case we forceCreate on the next attempt.
    # The lock just prevents two users from doing this at the same time,
    # though it's probably overkill.
    # Updated 7/10/17: filelocking failed on Cray (NERSC) so was disabled for now.
    mkdirs(newWorkspace)
    semaphoreFile = pathjoin(newWorkspace, '.creation_semaphore')

    try:
        os.remove(semaphoreFile)
        forceCreate = True          # if we can remove it, last attempt failed
    except OSError as e:
        import errno
        if e.errno != errno.ENOENT: # ENOENT => no such file exists
            raise

    if mcsMode and getParamAsBoolean('GCAM.CopyAllFiles'):
        _logger.warn('GCAM.CopyAllFiles = True while running MCS')

    if forceCreate:
        _logger.info("Removing workspace '%s'", newWorkspace)
        removeTreeSafely(newWorkspace, ignore_errors=True)

    mkdirs(newWorkspace)
    open(semaphoreFile, 'w').close()    # create empty semaphore file

    # Spell out variable names rather than computing parameter names to
    # facilitate searching source files for parameter uses.
    paramName = 'MCS.WorkspaceFilesToLink' if mcsMode else 'GCAM.WorkspaceFilesToLink'

    filesToCopy, filesToLink = _getFilesToCopyAndLink(paramName)

    for filename in filesToCopy:
        _workspaceLinkOrCopy(filename, refWorkspace, newWorkspace, copyFiles=True)

    for filename in filesToLink:
        _workspaceLinkOrCopy(filename, refWorkspace, newWorkspace, copyFiles=False)

    for filename in ['local-xml', 'dyn-xml']:
        dirname = pathjoin(newWorkspace, filename)
        mkdirs(dirname)

    # if successful, remove semaphore
    os.remove(semaphoreFile)
