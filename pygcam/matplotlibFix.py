'''
.. Created on: 2/7/2017
   Fix for non-framework version of python on Mac OS X

.. Copyright (c) 2017 Richard Plevin
   See the https://opensource.org/licenses/MIT for license details.
'''
import matplotlib as mpl

major, minor, rev = map(int, mpl.__version__.split('.'))
if major >= 2:
    import platform
    if platform.system() == 'Darwin':
        mpl.use('TkAgg')

#import matplotlib.pylab as pylab
import matplotlib.pyplot as plt
