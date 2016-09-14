pygcam
=======

The ``pygcam`` package is currently under development. It is a Python package
that provides classes, functions, and scripts for working with GCAM.

Core functionality
------------------

* Project workflow management framework that lets you define steps to run and
  run them all or run steps selectively.

* The main ``gt`` (think "gcamtool") script, which provides numerous
  sub-commands, and can be extended by writing plug-ins.

* The ``gt`` sub-commands facilitate key steps in working with GCAM, including:

  * Setting up experiments by modifying XML input files and configuration.xml
  * Running GCAM, locally or by queueing jobs on a Linux cluster
  * Querying the GCAM database to extract results to CSV files
  * Interpolating between time-steps and computing differences between baseline and policy cases
  * Plotting results

* The scripts are based on the pygcam API, which is fully documented on readthedocs.org.
  Use the scripts or API to develop your own custom applications or plug-ins for use with
  gt.

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

Contribution guidelines
------------------------

* TBD

Who do I talk to?
------------------

* Richard Plevin (rich@plevin.com)
