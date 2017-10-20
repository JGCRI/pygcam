``pygcam.xmlEditor``
=======================

This module defines common variables, functions, and classes for manipulating
XML files to setup GCAM modeling experiments. An introduction to the XML-Setup
system is available on the :doc:`setup` page; command-line features are documented
with the :ref:`setup <setup>` sub-command.

The basic approach is to create a directory for each defined scenario,
in which modified files and a corresponding configuration XML file
are stored.

To allow functions to be called in any order or combination, each
checks for a local copy of the file to be edited, and if not present,
copies the original file to the local directory. Local copies are
modified in place. Each function updates the local config file
so that it loads the modified file.


API
----

.. automodule:: pygcam.xmlEditor
   :members:


Sector-specific config editors
-------------------------------

These classes subclass XMLEditor to create sector-specific setup functionality.

.. automodule:: pygcam.sectorEditors
   :members:
