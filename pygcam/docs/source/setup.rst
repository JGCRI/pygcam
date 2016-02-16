The ``pygcam.setup`` module
============================

This module defines common variables, functions, and classes for manipulating
XML files to setup GCAM modeling experiments.

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

.. automodule:: pygcam.setup
   :members:


Mixins
------

These classes can be "mixed in" to a subclass of ConfigEditor to
create custom setup functionality.

.. automodule:: pygcam.mixins
   :members:
