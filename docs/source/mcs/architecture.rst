Software Architecture
=======================

The ``pygcam.mcs`` framework is implemented using `ipyparallel` ("ipython parallel"), which
provides the infrastructure to allow communication among a distributed set of python interpreters.

As implemented in ``pygcam.mcs``, a cluster is started for a desired number of worker processes
("engines" in ipyparallel parlance) and a master process that is typically run on a login node
so you can track runtime activity easily.

The ``pygcam.mcs`` package provides several additional sub-commands to the ``gcamtool`` (gt)
script, described in detail on the :doc:`commands` page. Here, we describe the commands
related to setting up, running, and monitoring a Monte Carlo simulation.

