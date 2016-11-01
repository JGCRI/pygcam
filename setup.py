import platform

if platform.system() != 'Windows':
    # Unfortunately, this stalled on Windows when I tested it...
    import ez_setup
    ez_setup.use_setuptools()

from setuptools import setup

requirements = ['configparser',     # backport of python 3.5 version
                'lxml',
                'numpy',
                'pandas',
                'seaborn',
                'sphinx-argparse',
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

* The easiest way to to install directly from PyPi:

    ``pip install pygcam``

* Alternatively, clone the repository or download the tarball and run this command
  on the included setup.py file:

    ``python setup.py install``

  Or, if you clone the repository, you might want to install in "develop"
  mode, which creates links back to the repository so you don't have to
  reinstall every time there is a change. To install in develop mode use
  this command:

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
    version='1.0b1',
    description='Python 2.7 library and scripts for interfacing with GCAM',
    platforms=['Windows', 'Mac OS X', 'Linux'],

    packages=['pygcam'],
    entry_points={'console_scripts': ['gt = pygcam.tool:main']},
    install_requires=requirements,
    include_package_data = True,

    url='https://bitbucket.org/plevin/pygcam',
    # download_url='ssh://git@bitbucket.org/plevin/pygcam.git',
    download_url='https://plevin@bitbucket.org/plevin/pygcam.git',
    license='MIT License',
    author='Richard Plevin',
    author_email='rich@plevin.com',

    classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Science/Research',
          ],

    zip_safe=True,

    # TBD
    # test_suite="string identifying test module etc."

)
