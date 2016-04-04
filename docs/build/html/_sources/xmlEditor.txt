``pygcam.xmlEditor``
=======================

This module defines common variables, functions, and classes for manipulating
XML files to setup GCAM modeling experiments. An introduction to the XML-Setup
system is available on the :doc:`setup` page; command-line features are documented
with the :ref:`setup <setup-label>` sub-command.

The basic approach is to create a directory for each defined scenario,
in which modified files and a corresponding configuration XML file
are stored.

To allow functions to be called in any order or combination, each
checks for a local copy of the file to be edited, and if not present,
copies the original file to the local directory. Local copies are
modified in place. Each function updates the local config file
so that it loads the modified file.

XML Starlet
-----------
The ``xmlEditor`` module relies on the XML Starlet
program, a command-line tool that can search and edit XML files (among other
tricks.) It is available for all three GCAM platforms.
`Download XML Starlet <http://xmlstar.sourceforge.net/download.php>`_.
It should be included on Linux systems. It is available in binary (executable)
form for Windows, but must be compiled on Mac OS X.


API
----

.. automodule:: pygcam.xmlEditor
   :members:


Sector-specific config editors
-------------------------------

These classes subclass XMLEditor to create sector-specific setup functionality.

.. automodule:: pygcam.sectorEditors
   :members:
