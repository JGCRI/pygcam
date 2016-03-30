``pygcam.log``
============================

This module allows modules to register themselves for logging which is
turned on after the app reads configuration information. Modules call

   .. code-block:: python

      logger = pygcam.log.getLogger(__name__)

as a top-level statement, evaluated
at load time. This returns the logger, which may not yet be configured.
When the configuration file has been read, all registered loggers are
initialized, and all subsequently registered loggers are initialized
upon instantiation.

API
---

.. automodule:: pygcam.log
   :members:

