#!/usr/bin/env python
'''
Created on 12/12/15

@author: Rich Plevin (rich@plevin.com)
'''

# Copyright (c) 2015, Richard Plevin.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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


def parseArgs():
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description='''Generate versions of GCAM's land_input XML files that protect a given fraction
                       of land of the given land types in the given regions.''')

    parser.add_argument('-f', '--fraction', type=float, required=True,
                        help='''The fraction of land in the given land classes to protect. (Required)''')

    parser.add_argument('-i', '--inFile', action='append',
                        help='''One or more input files to process. Use separate -i flags for each file.''')

    parser.add_argument('-l', '--landClasses', action='append',
                        help='''The land class or classes to protect in the given regions. Multiple,
                        comma-delimited land types can be given in a single argument, or the -l flag can
                        be repeated to indicate additional land classes. Allowed land classes are %s''' % AllUnmanagedLand)

    parser.add_argument('-o', '--outDir', type=str, default='.',
                        help='''The directory into which to write the modified files. Default is current directory.''')

    parser.add_argument('-r', '--regions', action='append',
                        help='''The region or regions for which to protect land. Multiple, comma-delimited
                        regions can be given in a single argument, or the -r flag can be repeated to indicate
                        additional regions.''')

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

    landClasses = flatten(map(lambda s: s.split(','), args.landClasses)) if args.landClasses else AllUnmanagedLand
    regions     = args.regions and flatten(map(lambda s: s.split(','), args.regions))
    fraction  = float(args.fraction)
    outDir    = args.outDir
    inFiles   = args.inFile
    workspace = args.workspace

    if not inFiles and not workspace:
        raise Exception('Must specify either inFiles or workspace')

    if workspace:
        if inFiles:
            print "Workspace is defined; ignoring inFiles"

        filenames = ['land_input_2.xml', 'land_input_3.xml']
        xmlDir = os.path.join(workspace, 'input', 'gcam-data-system', 'xml', 'aglu-xml')

        for filename in filenames:
            inFile = os.path.join(xmlDir, filename)
            outFile = 'prot_%d_percent_%s' % (int(fraction * 100), filename)
            outPath = os.path.join(outDir, outFile)
            print "protectLand(%s, %s, %0.2f, %s, %s)" % (inFile, outFile, fraction, landClasses, regions)
            protectLand(inFile, outPath, fraction, landClasses=landClasses, regions=regions)

if __name__ == '__main__':
    status = -1
    try:
        main()
        status = 0
    except Exception as e:
        print "%s: %s" % (PROGRAM, e)

    sys.exit(status)
