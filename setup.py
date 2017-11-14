import platform
from pygcam.version import VERSION

# Build the full version with MCS on when running on ReadTheDocs.
# In normal mode, MCS is an optional install.
import os

if platform.system() != 'Windows':
    # Unfortunately, this stalled on Windows when I tested it...
    import ez_setup
    ez_setup.use_setuptools(version='36.7.2') # ... is this version avail on RTD?

from setuptools import setup

requirements = [
    'configparser>=3.5.0',     # backport of python 3.5 version
    'filelock>=2.0.12',
    'futures>=3.1.1',
    'future>=0.16.0',
    'lxml>=3.8.0',
    'numpy>=1.13.1',
    'pandas>=0.20.3',
    'seaborn>=0.8.0',
    'semver>=2.7.7',
    'six>=1.10.0',
    'sphinx-argparse==0.1.17', # later versions lose markup in commands

    # GUI requirements
    'flask>=0.12.2',
    'dash>=0.19.0',
    'dash-core-components>=0.12.7',
    'dash-html-components>=0.8.0',
    'dash-renderer>=0.7.4',

    # MCS requirements
    'ipyparallel>=6.0.2',
    'numexpr>=2.6.2',
    'salib==1.1.2',
    'scipy>=0.19.1',
    'sqlalchemy>=1.1.13',
]


#if os.environ.get('READTHEDOCS') == 'True':
#    requirements.extend(mcs_requirements)
#    extras_requirements = {}
#else:
#    extras_requirements = {
#        'mcs': mcs_requirements,
#    }

long_description = '''
pygcam
=======

The ``pygcam`` package provides a workflow management framework for GCAM
consisting of scripts and a Python API for customizing the framework by
writing plug-ins, or by writing new applications.

Full documentation and a tutorial are available at
https://pygcam.readthedocs.io.

Core functionality
------------------

* Project workflow management framework that lets you define steps to run and
  run them all or run steps selectively.

* The main ``gt`` ("GCAM tool") script, which provides numerous
  sub-commands, and can be extended by writing plug-ins.

* The ``gt`` sub-commands facilitate key steps in working with GCAM, including:

  * Setting up experiments by modifying XML input files and configuration.xml
  * Running GCAM, locally or by queueing jobs on a Linux cluster
  * Querying the GCAM database to extract results to CSV files
  * Interpolating between time-steps and computing differences between baseline and policy cases
  * Plotting results
  * Setting up, running, and analyzing Monte Carlo simulations on Linux clusters

* The scripts are based on the pygcam API, documented at https://pygcam.readthedocs.io

* Scripts that provide flexible command-line interfaces to the functionality provided by
  the library.

* Customization through an extensive configuration system

How do I get set up?
----------------------

* Users on OS X and Windows platforms can download a zip file with an all-in-one
  directory that has everything you need to run the "gt" (gcamtool) command.

* Linux users and anyone wishing to use ``pygcam`` for Python development should
  install it as a normal Python package. The easiest way to to install directly from
  PyPi:

    ``pip install pygcam``

  Alternatively, clone the repository or download the tarball and run this command
  on the included setup.py file:

    ``python setup.py install``

  or, if you want to edit the code or stay abreast of code changes, you might install
  it in "developer" mode:

    ``python setup.py develop``

Contribution guidelines
------------------------

* TBD

Who do I talk to?
------------------

* Rich Plevin (rich@plevin.com)
'''

setup(
    name='pygcam',
    version=VERSION,
    description='Python 2.7 library and scripts for interfacing with GCAM',
    platforms=['Windows', 'MacOS', 'Linux'],

    packages=['pygcam'],
    entry_points={'console_scripts': ['gt = pygcam.tool:main']},
    install_requires=requirements,
    include_package_data = True,

    # extras_require=extras_requirements,

    url='https://github.com/JGCRI/pygcam',
    download_url='https://github.com/JGCRI/pygcam.git',
    license='MIT License',
    author='Richard Plevin',
    author_email='rich@plevin.com',

    classifiers=[
          'Development Status :: 5 - Production/Stable',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Science/Research',
          ],

    zip_safe=True,

    # TBD
    # test_suite="string identifying test module etc."

)

