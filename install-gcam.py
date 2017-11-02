#!/usr/bin/env python
#
# Installs gcam v4.3 on Windows, Mac OS X, and Linux
#
# Author: Rich Plevin (rich@plevin.com)
# Created: 10 Nov 2016
#
from __future__ import print_function
import os
import sys
import argparse
import subprocess
import platform
import urllib
from urlparse import urlparse
import tarfile

PlatformName = platform.system()
isWindows = (PlatformName == 'Windows')
isMacOS   = (PlatformName == 'Darwin')
isLinux   = (PlatformName == 'Linux')


Home = os.environ['HOME'] = os.environ['HOME']
DefaultInstallDir  = os.path.join(Home, 'gcam-v4.3-install-dir')
DefaultDownloadDir = os.path.join(Home, '.gcam-installation-tmp')

def parseArgs():
    parser = argparse.ArgumentParser(description='''Install GCAM v4.3 on Windows, macOS, or Linux''')

    parser.add_argument('-d', '--downloadDir', default=DefaultDownloadDir,
                        help='''The directory into which to download the required tar files. Default is %s''' % DefaultDownloadDir)

    parser.add_argument('-i', '--installDir', default=DefaultInstallDir,
                        help='''The directory into which to install GCAM 4.3. Default is %s''' % DefaultInstallDir)

    parser.add_argument('-k', '--keepTarFiles', action='store_true',
                        help='''Keep the downloaded tar files rather than deleting them.''')

    parser.add_argument('-n', '--noRun', action='store_true',
                        help='''Print commands that would be executed, but don't run them.''')

    parser.add_argument('-r', '--reuseTarFiles', action='store_true',
                        help='''Use the already-downloaded tar files rather then retrieving them again.
                        Implies -k/--keepTarFiles.''')

    args = parser.parse_args()
    return args


def run(cmd, ignoreError=False, printOnly=False):
    print(cmd)
    if printOnly:
        return

    status = subprocess.call(cmd, shell=True)

    if not ignoreError and status != 0:
        sys.exit(status)

def download(url, filename, printOnly=False):
    def _report(blocks, blockSize, fileSize):
        print('\r%2.0f%% ...' % (100. * blocks * blockSize / fileSize), end='')

    if not filename:
        obj = urlparse(url)
        filename = os.path.basename(obj.path)

    print('Download "%s" -> "%s"\n' % (url, filename))
    if printOnly:
        return

    filename, headers = urllib.urlretrieve(url, filename=filename, reporthook=_report)
    print('') # for the newline
    return filename

def untar(filename, directory='.', printOnly=False):
    print("untar '%s' in '%s'" % (filename, directory))
    if printOnly:
        return

    with tarfile.open(filename, mode='r:gz') as tar:
        tar.extractall(path=directory)

#
# Comment taken from exe/run-gcam.command:
#
# We need to find where the Java development kit is installed.
# This could be the Apple supplied version which was provided up
# to 1.6 however was dropped subsequently and instead users may
# have an Oracle provided JDK.  The each take slightly different
# approaches to where libraries live and how to reference them so
# we will have to try to detect the appropriate location.
#
def fixMacJava(coreDir, printOnly=False):
    cmd = '/usr/libexec/java_home'
    javaHome = ''
    try:
        javaHome = subprocess.check_output(cmd).strip()
    except Exception:
        pass

    if not javaHome:
        print('ERROR: Could not find Java install location')
        sys.exit(-1)

    # If javaHome contains "1.6", use the Apple supplied version of java 1.6
    libPath = 'lib-stub' if '1.6' in javaHome else javaHome + '/jre/lib/server'

    owd = os.getcwd()
    if not printOnly:
        os.chdir(coreDir)

    # Create a symlink to satisfy @rpath searches
    linkName = 'libs/java/lib'
    if not os.path.islink(linkName):
        run("ln -s %s %s" % (libPath, linkName), printOnly=printOnly)

    os.chdir(owd)


def main():
    args = parseArgs()

    coreTarFile = 'gcam-v4.3.tar.gz'
    dataTarFile = 'data-system.tar.gz'

    downloadPrefix = 'https://github.com/JGCRI/gcam-core/releases/download/gcam-v4.3/'

    coreURL = 'https://github.com/JGCRI/gcam-core/archive/' + coreTarFile
    dataURL = downloadPrefix + dataTarFile

    tarFiles = [coreTarFile, dataTarFile]

    madeDownloadDir = False

    downloadDir = os.path.abspath(args.downloadDir)
    installDir  = os.path.abspath(args.installDir)
    printOnly   = args.noRun

    if not os.path.lexists(downloadDir):
        run('mkdir ' + downloadDir, printOnly=printOnly)
        madeDownloadDir = True

    elif not os.path.isdir(downloadDir):
        print('Specified download dir is not a directory: %s' % downloadDir)
        return -1

    startDir = os.getcwd()

    if not printOnly:
        os.chdir(downloadDir)

    if not args.reuseTarFiles:
        download(coreURL, coreTarFile, printOnly=printOnly)
        download(dataURL, dataTarFile, printOnly=printOnly)

    if not os.path.isdir(installDir):
        run('mkdir ' + installDir, printOnly=printOnly)

    coreDir = os.path.join(installDir, 'gcam-core-gcam-v4.3')

    untar(os.path.join(downloadDir, coreTarFile), installDir, printOnly=printOnly)
    untar(os.path.join(downloadDir, dataTarFile), coreDir,    printOnly=printOnly)

    if isMacOS or isWindows:
        binTarFile = '%s_binaries.tar.gz' % ('mac' if isMacOS else 'windows')
        binURL = downloadPrefix + binTarFile

        if not args.reuseTarFiles:
            download(binURL, binTarFile, printOnly=printOnly)

        untar(os.path.join(downloadDir, binTarFile), coreDir, printOnly=printOnly)
        tarFiles.append(binTarFile)

        if isMacOS:
            fixMacJava(coreDir, printOnly=printOnly)

    if printOnly:
        return 0

    print("Installed GCAM into %s" % installDir)

    if args.reuseTarFiles or args.keepTarFiles:
        print("Keeping tar files in %s" % downloadDir)
    else:
        for tarFile in tarFiles:
            os.remove(tarFile)

        if madeDownloadDir:
            # only remove this dir if we created it
            os.chdir(startDir)
            os.rmdir(downloadDir)

    return 0

sys.exit(main())
