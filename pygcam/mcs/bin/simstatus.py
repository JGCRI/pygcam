#!/usr/bin/env python
from __future__ import print_function
import os

def main():
    cfg = os.path.expanduser('~/.pygcam.cfg')
    with open(cfg, 'r') as f:
        lines = f.readlines()

    match = filter(lambda line: line.startswith('GCAM.DefaultProject'), lines)
    if match:
        line = match[0]
        defaultProject = line.split('=')[1].strip()
        print(defaultProject)
    else:
        print('-- Not set --')

main()
