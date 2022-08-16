#!/usr/bin/env python
import os

def main():
    cfg = os.path.expanduser('~/.pygcam.cfg')
    with open(cfg, 'r') as f:
        lines = f.readlines()

    match = [line for line in lines if line.startswith('GCAM.DefaultProject')]

    if match:
        line = match[0]
        defaultProject = line.split('=')[1].strip()
        print(defaultProject)
    else:
        print('-- Not set --')

main()
