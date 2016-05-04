Tutorial -- Using ``pygcam``
=============================

  .. note::

        This tutorial is currently under development!

Setting up a GCAM experiment
----------------------------------

Configuration
^^^^^^^^^^^^^^^

    .. seealso::

       The configuration API and default variable settings are described in :doc:`config`


  * First run creates ~/.pygcam.cfg

  * Required parameters


GCAM: main user workspace and ModelInterface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  * Location of GCAM package

  * xmlsrc, local-xml, dyn-xml




Project structure
^^^^^^^^^^^^^^^^^^^

  * XML files
  * scenarios.py



Running a GCAM experiment
----------------------------

Run-time structure:

  * SandboxRoot
      * *figure showing sandbox structure*

  * Create a file :doc:`project-xml` (template ...)

  * Use the ``run`` sub-command of :doc:`gcamtool`

    * Hint: use ``-l``, ``-L``, and ``-g`` to list steps, scenarios, and groups

    * Choose steps, scenarios, groups to run using ``-s``, ``-S``, and ``-g`` flags,
      and choose steps or scenarios *not* to run using ``-k`` and ``-K`` flags.

    * Setting defaults to simplify use


