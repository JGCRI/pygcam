#!/usr/bin/env python

'''
.. Main driver for pygcam tools, which are accessed as sub-commands.

.. codeauthor:: Rich Plevin <rich@plevin.com>

.. Copyright (c) 2016 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''

import sys
from pygcam.tool import main

if __name__ == '__main__':
    sys.exit(main())
    main()
