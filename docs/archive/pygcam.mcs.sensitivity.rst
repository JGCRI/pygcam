``pygcam.mcs.sensitivity``
============================

Functions for performing sampling and sensitivity analysis.

The main features of this module are:

#. The ``SensitivityAnalysis`` class, which provides a uniform interface
   to the various sampling and sensitivity analysis methods implemented
   in :doc:`SALib <SALib:api>`.
#. The ``data.sa`` directory "package" (managed by the ``SensitivityAnalysis``
   class) which stores sampled data and information about the sampling method
   required by the analysis methods.

Access to these features is provided via the ``-m`` / ``--method`` argument
to the :ref:`gensim <gensim>` sub-command.

API
---

.. automodule:: pygcam.mcs.sensitivity
   :members:

