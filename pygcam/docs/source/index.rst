.. pygcam documentation master file, created by
   sphinx-quickstart on Tue Feb  9 16:33:28 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

The ``pygcam`` package
==================================

The ``pygcam`` package comprises a set of Python modules and a main driver script designed
to facilitate working with the `Global Change Assessment Model <http://www.globalchange.umd.edu/models/gcam>`_
(GCAM).

The main driver (`gcamtool`) uses a plug-ins architecture to simplify customization.

*This package is currently under development.*


Contents
--------

.. toctree::
   :maxdepth: 1

   intro
   common
   config
   error
   landProtection
   project
   query
   setup
   gcamtool

XML input file formats for sub-commands
---------------------------------------

.. toctree::
   :maxdepth: 1

   project-xml
   protect-xml
