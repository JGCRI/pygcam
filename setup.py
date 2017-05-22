import platform
from pygcam.version import VERSION

if platform.system() != 'Windows':
    # Unfortunately, this stalled on Windows when I tested it...
    import ez_setup
    ez_setup.use_setuptools() # version='32.0.0') ... this version not avail on RTD

from setuptools import setup

requirements = [
    'configparser',     # backport of python 3.5 version
    'future',
    'lxml',
    'numpy',
    'pandas',
    'seaborn',
    'six',
    'sphinx-argparse==0.1.17',
    'filelock',
]

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
    platforms=['Windows', 'Mac OS X', 'Linux'],

    packages=['pygcam'],
    entry_points={'console_scripts': ['gt = pygcam.tool:main']},
    install_requires=requirements,
    include_package_data = True,

    url='https://bitbucket.org/plevin/pygcam',
    download_url='https://plevin@bitbucket.org/plevin/pygcam.git',
    license='MIT License',
    author='Richard Plevin',
    author_email='rich@plevin.com',

    classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Science/Research',
          ],

    zip_safe=True,

    # TBD
    # test_suite="string identifying test module etc."

)
