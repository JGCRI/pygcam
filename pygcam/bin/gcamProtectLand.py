#!/usr/bin/env python
'''
Created on 12/12/15
@author: Rich Plevin (rich@plevin.com)

Copyright (c) 2015 Richard Plevin
See the https://opensource.org/licenses/MIT for license details.
'''

import os
import sys
import platform
from itertools import chain
import argparse
from pygcam.protectLand import AllUnmanagedLand, protectLand

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

    parser.add_argument('-f', '--fraction', type=float, required=True,
                        help='''The fraction of land in the given land classes to protect. (Required)''')

    parser.add_argument('-i', '--inFile', action='append',
                        help='''One or more input files to process. Use separate -i flags for each file.''')

    parser.add_argument('-l', '--landClasses', action='append',
                        help='''The land class or classes to protect in the given regions. Multiple,
                        comma-delimited land types can be given in a single argument, or the -l flag can
                        be repeated to indicate additional land classes. By default, all unmanaged land
                        classes are protected. Allowed land classes are %s''' % AllUnmanagedLand)

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

    landClasses = flatten(map(lambda s: s.split(','), args.landClasses)) if args.landClasses else AllUnmanagedLand
    regions     = args.regions and flatten(map(lambda s: s.split(','), args.regions))
    fraction  = float(args.fraction)
    outDir    = args.outDir
    inFiles   = args.inFile
    workspace = args.workspace
    template  = args.template

    if not inFiles and not workspace:
        raise Exception('Must specify either inFiles or workspace')

    if workspace:
        if inFiles:
            print "Workspace is defined; ignoring inFiles"

        # compute equivalent 'inFiles' arguments for loop below
        filenames = ['land_input_2.xml', 'land_input_3.xml']
        xmlDir = os.path.join(workspace, 'input', 'gcam-data-system', 'xml', 'aglu-xml')
        inFiles = map(lambda filename: os.path.join(xmlDir, filename), filenames)

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
        protectLand(path, outPath, fraction, landClasses=landClasses, regions=regions, template=args.template)

if __name__ == '__main__':
    status = -1
    try:
        main()
        status = 0
    except Exception as e:
        print "%s: %s" % (PROGRAM, e)

    sys.exit(status)
