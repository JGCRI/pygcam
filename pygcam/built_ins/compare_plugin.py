#!/usr/bin/env python
"""
.. "compare" sub-command (compares two config files and the files they load)

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016  Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
"""
from ..subcommand import SubcommandABC, clean_help

def driver(args, tool):
    import os
    import subprocess
    from ..config import getParam, pathjoin
    from ..error import FileFormatError
    from ..utils import mkdirs
    from ..XMLFile import XMLFile

    xmlStarlet = getParam('GCAM.XmlStarlet')

    def getFiles(config):
        xmlFile  = XMLFile(config)
        fileElts = xmlFile.tree.findall('//ScenarioComponents/Value')

        files = {}
        for elt in fileElts:
            fileTag = elt.get('name')
            if fileTag in files:
                raise FileFormatError('Config file "%s" has multiple scenario components with tag "%s"' % (config, fileTag))

            files[fileTag] = elt.text

        return files

    def normalizeFiles(name, files, exedir):
        subdir = pathjoin(args.outputDir, name)
        mkdirs(subdir)

        for fileTag, relPath in files.items():
            fileDir = pathjoin(subdir, fileTag)
            mkdirs(fileDir)

            outfile = pathjoin(fileDir, os.path.basename(relPath))
            infile  = pathjoin(exedir, relPath)

            files[fileTag] = outfile

            cmd = "{xmlStarlet} c14n --without-comments '{infile}' | xml fo -s 2 > '{outfile}'"
            cmd = cmd.format(xmlStarlet=xmlStarlet, infile=infile, outfile=outfile)
            print(cmd)
            subprocess.call(cmd, shell=True)

        return files

    files1 = getFiles(args.config1)
    files2 = getFiles(args.config2)

    set1 = set(files1.keys())
    set2 = set(files2.keys())

    if set1 != set2:
        if len(set1 - set2):
            print("Config2 is missing: %s" % list(set1 - set2))
        if len(set2 - set1):
            print("Config1 is missing: %s" % list(set2 - set1))

        return

    print("Config files are the same structurally.")
    files1 = normalizeFiles('config1', files1, args.exedir1)
    files2 = normalizeFiles('config2', files2, args.exedir2)

    diffs = {}
    for fileTag, path1 in files1.items():
        path2 = files2[fileTag]

        cmd = ['diff', path1, path2]
        print(' '.join(cmd))
        if subprocess.call(cmd, shell=False) != 0:
            diffs[fileTag] = (path1, path2)

    if diffs:
        print('The following files files differ:')
        for fileTag, filenames in diffs.items():
            print("%s: %s" % (fileTag, filenames))



class CompareCommand(SubcommandABC):
    def __init__(self, subparsers):
        kwargs = {'help' : clean_help('''Compare two GCAM configuration files and the files they load to
        find differences. Files are compared using "diff" based on matching "name" tags.''')}
        super(CompareCommand, self).__init__('compare', subparsers, kwargs, group='utils')

    def addArgs(self, parser):
        defaultOutputDir = '/tmp/xmlCompare'

        # Positional args
        parser.add_argument('config1',
                            help='''The first of two config files to compare.''')

        parser.add_argument('exedir1',
                            help='''The "exe" from which config1 pathnames should be computed.''')

        parser.add_argument('config2',
                            help='''The second of two config files to compare.''')

        parser.add_argument('exedir2',
                            help='''The "exe" from which config2 pathnames should be computed.''')

        parser.add_argument('-o', '--outputDir', default=defaultOutputDir,
                            help=clean_help('''The directory in which to create the normalized versions of XML
                            input files for comparison. Default is %s''' % defaultOutputDir))

        return parser   # for auto-doc generation


    def run(self, args, tool):
        driver(args, tool)
