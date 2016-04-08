``pygcam.config``
=============================

This module provides access to configuration parameters. The parameters listed below
are defined with the given defaults, and then the user's ``~/.pygcam.cfg`` file is read,
overriding any defaults. User values should be defined in a section called ``[GCAM]``.

API
---

.. automodule:: pygcam.config
   :members:

.. _pygcam-cfg:


Default values
--------------
The configuration system sets default value by first reading a file called
``pygcam/etc/system.cfg`` (listed below) which is included in the pygcam
distribution. Then, if it exists, the file ``pygcam/etc/site.cfg`` is read.
This file is intended to allow administrators to set configuration parameters
for all users.

Next, four values are set dynamically based on the operating system being
used. Three are shown in the table below; ``GCAM.JarFile`` is set to
``%(GCAM.ModelInterface)s/ModelInterface.jar`` except on Mac OS X where it is set to
``%(GCAM.ModelInterface)s/ModelInterface.app/Contents/Resources/Java/ModelInterface.jar``.


+-----------------------+------------+-----------------+------------+----------+
| Variable              | Linux      | Mac OS X        | Windows    | Other    |
+=======================+============+=================+============+==========+
| Home                  | $(HOME)    | $(HOME)         | %HOMEPATH% | $(HOME)  |
+-----------------------+------------+-----------------+------------+----------+
| GCAM.Executable       | ./gcam.exe | Release/objects | gcam.exe   | gcam.exe |
+-----------------------+------------+-----------------+------------+----------+
| GCAM.UseVirtualBuffer | True       | False           | False      | False    |
+-----------------------+------------+-----------------+------------+----------+

Finally, the user's config file ``~/.pygcam.cfg`` is read if it exists; otherwise
the file is created by commenting out all settings found in the ``system.cfg`` file,
which are provided for reference.

  .. note::

    When de-referencing a variable in the config file, you must include the
    trailing 's' after the closing parenthesis, or a Python exception will be raised.


  .. literalinclude:: ../../pygcam/etc/system.cfg
     :language: cfg
