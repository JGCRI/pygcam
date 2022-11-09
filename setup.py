from pygcam.version import VERSION

# Build the full version with MCS on when running on ReadTheDocs.
# In normal mode, MCS is an optional install.
# import os
# import platform
#
# if platform.system() != 'Windows':
#     # Unfortunately, this stalled on Windows when I tested it...
#     import ez_setup
#     ez_setup.use_setuptools(version='36.7.2')


from setuptools import setup

requirements = [
    'dash',
    'flask',
    'ipython',
    'ipyparallel',
    'lxml',
    'matplotlib',
    'numpy',
    'pandas',
    'plotly',
    'requests',
    'rpy2',
    'scipy',
    'seaborn',
    'semver',
    'sphinx-argparse',
    'sphinx-rtd-theme',
    # 'salib>=1.1.3',
    'sqlalchemy',
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
  * Setting up, running, and analyzing Monte Carlo simulations on Linux clusters

* The scripts are based on the pygcam API, documented at https://pygcam.readthedocs.io

* Scripts that provide flexible command-line interfaces to the functionality provided by
  the library.

* Customization through an extensive configuration system

Who do I talk to?
------------------

* Rich Plevin (rich@plevin.com)
'''

setup(
    name='pygcam',
    version=VERSION,
    description='Python 3 library and scripts for interfacing with GCAM',
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

