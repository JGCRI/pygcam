Tutorial -- Using ``pygcam``
=============================

  .. note::

        This tutorial is currently under development.

Setting up a GCAM experiment
----------------------------------

Configuration
^^^^^^^^^^^^^^^

    .. seealso::

       The configuration API and default variable settings are described in :doc:`config`


  * First run creates ~/.pygcam

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

    * Use ``-l`` and ``-L`` to list steps

    * Choose steps to run or not run

    * Choose groups and scenarios to operate on

    * Setting defaults to simplify use


