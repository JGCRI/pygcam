Configuration
==============

The ``pygcam`` configuration system allows the user to control a
range of parameters defining file locations, parameters related to
the parallel execution of Monte Carlo trials, and other project-related
parameters.

.. seealso::

   The ``pygcam.mcs`` configuration parameters extend those defined for
   ``pygcam``. See pygcam's :doc:`../config` page for more info.


Default values for all configuration parameters defined in ``pygcam.mcs``
are provided in ``pygcam/mcs/etc/mcs.cfg``. Values can be overridden in the
user's configuration file (``~/.pygcam.cfg``) or a site-wide configuration
file (at the location indicated by environment variable ``PYGCAM_SITE_CONFIG``).
New values in either of these files can establish a different default value
that applies to all projects, or define a value on a per-project basis.


The system defaults file
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../../pygcam/mcs/etc/mcs.cfg
   :language: cfg
