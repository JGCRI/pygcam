#!/usr/bin/env python
'''
a@author: Rich Plevin (rich@plevin.com)

Copyright (c) 2015 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.
'''

import os
import sys
import platform
from itertools import chain
import argparse
from pygcam.protectLand import AllUnmanagedLand, protectLand, XMLFile, LandProtection
from pygcam.common import mkdirs

# Read the following imports from the same dir as the script
sys.path.insert(0, os.path.dirname(sys.argv[0]))

PROGRAM = os.path.basename(__file__)
VERSION = "0.1"

PlatformName = platform.system()

DefaultTemplate = 'prot_{fraction}_{filename}'
Verbose = False

def printmsg(msg):
    if Verbose:
        print msg


def parseArgs():
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description='''Generate versions of GCAM's land_input XML files that protect a given fraction
                       of land of the given land types in the given regions. The script can be run
                       multiple times on the same file to apply different percentage protection to
                       distinct regions or land classes. The script detects if you attempt to protect
                       already-protected land class and region combinations, as this fails in GCAM.''')

    parser.add_argument('-b', '--backup', action='store_true',
                        help='''Make a copy of the output file, if it exists (with an added ~ after
                        filename) before writing new output.''')

    parser.add_argument('-f', '--fraction', type=float, default=None,
                        help='''The fraction of land in the given land classes to protect. (Required)''')

    parser.add_argument('-i', '--inFile', action='append',
                        help='''One or more input files to process. Use separate -i flags for each file.''')

    parser.add_argument('--inPlace', action='store_true',
                        help='''Edit the file in place. This must be given explicitly, to avoid overwriting
                        files by mistake.''')

    parser.add_argument('-l', '--landClasses', action='append',
                        help='''The land class or classes to protect in the given regions. Multiple,
                        comma-delimited land types can be given in a single argument, or the -l flag can
                        be repeated to indicate additional land classes. By default, all unmanaged land
                        classes are protected. Allowed land classes are %s''' % AllUnmanagedLand)

    parser.add_argument('-m', '--mkdir', action='store_true',
                        help='''Make the output dir if necessary.''')

    parser.add_argument('-o', '--outDir', type=str, default='.',
                        help='''The directory into which to write the modified files. Default is current directory.''')

    parser.add_argument('-t', '--template', type=str, default=DefaultTemplate,
                        help='''Specify a template to use for output filenames. The keywords {fraction}, {filename},
                        {regions}, and {classes} (with surrounding curly braces) are replaced by the following values
                        and used to form the name of the output files, written to the given output directory.
                        fraction: 100 times the given fraction (i.e., int(fraction * 100));
                        filename: the name of the input file being processed (e.g., land_input_2.xml or land_input_3.xml);
                        basename: the portion of the input filename prior to the extension (i.e., before '.xml');
                        regions: the given regions, separated by '-', or the word 'global' if no regions are specified;
                        classes: the given land classes, separated by '-', or the word 'unmanaged' if no land classes
                        are specified. The default pattern is "%s".''' % DefaultTemplate)

    parser.add_argument('-r', '--regions', action='append',
                        help='''The region or regions for which to protect land. Multiple, comma-delimited
                        regions can be given in a single argument, or the -r flag can be repeated to indicate
                        additional regions. By default, all regions are protected.''')

    parser.add_argument('-s', '--scenario', default=None,
                        help='''The name of a land-protection scenario defined in the file given by the --scenarioFile
                        argument or it's default value.''')

    parser.add_argument('-S', '--scenarioFile', default=None,
                        help='''An XML file defining land-protection scenarios. Default is [WHAT?]''')

    parser.add_argument('-v', '--verbose', action='store_true', help='''Show diagnostic output''')

    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + VERSION)

    parser.add_argument('-w', '--workspace', type=str, default=None,
                        help='''Specify the path to the GCAM workspace to use. If input files are not identified
                        explicitly, the files in {workspace}/input/gcam-data-system/xml/aglu-xml/land_input_{2,3}.xml
                        are used as inputs.''')

    args = parser.parse_args()
    return args


def flatten(listOfLists):
    "Flatten one level of nesting"
    return list(chain.from_iterable(listOfLists))


def main():
    args = parseArgs()
    global Verbose
    Verbose = args.verbose

    landClasses  = flatten(map(lambda s: s.split(','), args.landClasses)) if args.landClasses else AllUnmanagedLand
    scenarioFile = args.scenarioFile
    scenarioName = args.scenario
    regions   = args.regions and flatten(map(lambda s: s.split(','), args.regions))
    outDir    = args.outDir
    inFiles   = args.inFile
    workspace = args.workspace
    template  = args.template
    inPlace   = args.inPlace
    backup    = args.backup

    if not inFiles and not workspace:
        raise Exception('Must specify either inFiles or workspace')

    if workspace:
        if inFiles:
            print "Workspace is defined; ignoring inFiles"

        # compute equivalent 'inFiles' arguments for loop below
        filenames = ['land_input_2.xml', 'land_input_3.xml']
        xmlDir = os.path.join(workspace, 'input', 'gcam-data-system', 'xml', 'aglu-xml')
        inFiles = map(lambda filename: os.path.join(xmlDir, filename), filenames)

    if args.mkdir:
        mkdirs(outDir)

    if scenarioName:
        if not scenarioFile:
            raise Exception('A scenario file was not identified')

        print "Land-protection scenario '%s'" % scenarioName

        schemaFile = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'etc', 'protection-schema.xsd')
        xmlFile = XMLFile(scenarioFile, schemaFile=schemaFile, rootClass=LandProtection)
        landProtection = xmlFile.getRoot()
        for inFile in inFiles:
            basename = os.path.basename(inFile)
            outFile  = os.path.join(outDir, basename)

            # check that we're not clobbering the input file
            if not inPlace and os.path.lexists(outFile) and os.path.samefile(inFile, outFile):
                raise Exception("Attempted to overwrite '%s' but --inPlace was not specified." % inFile)

            landProtection.protectLand(inFile, outFile, scenarioName, backup=backup)

        return

    fraction = args.fraction
    if fraction is None:
        raise Exception('If not using protection scenarios, fraction must be provided')

    fraction = float(fraction)
    templateDict = {'fraction' : str(int(fraction * 100)),
                    'regions'  : '-'.join(regions) if regions else 'global',
                    'classes'  : '-'.join(landClasses) if args.landClasses else 'unmanaged'}

    for path in inFiles:
        filename = os.path.basename(path)
        templateDict['filename'] = filename
        templateDict['basename'] = os.path.splitext(filename)[0]

        outFile = template.format(**templateDict)
        outPath = os.path.join(outDir, outFile)
        printmsg( "protectLand(%s, %s, %0.2f, %s, %s)" % (path, outFile, fraction, landClasses, regions))
        protectLand(path, outPath, fraction, landClasses=landClasses, regions=regions) #, template=template)

if __name__ == '__main__':
    status = -1
    try:
        main()
        status = 0
    except Exception as e:
        print "%s: %s" % (PROGRAM, e)
        raise

    sys.exit(status)
