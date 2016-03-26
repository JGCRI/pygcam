.. pygcam documentation master file, created by
   sphinx-quickstart on Tue Feb  9 16:33:28 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The ``pygcam`` package
==================================

The ``pygcam`` package comprises a set of Python modules and a main driver script designed
to facilitate working with the `Global Change Assessment Model <http://www.globalchange.umd.edu/models/gcam>`_
(GCAM).

The main script (:doc:`gcamtool`) uses a :doc:`plug-in <subcommand>` architecture to simplify customization.

*This package is currently under development.*


Contents
--------

.. toctree::
   :maxdepth: 1

   intro
   install
   common
   config
   diff
   error
   landProtection
   log
   project
   query
   setup
   subcommand
   gcamtool
   windows

XML input file formats for sub-commands
---------------------------------------

.. toctree::
   :maxdepth: 1

   project-xml
   protect-xml
