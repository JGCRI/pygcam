Introduction
=============

.. note::

   Currently, ``pygcam.mcs`` runs only on Unix-like platforms with
   either the SLURM or PBS job management systems.
   See the :doc:`configuration` page for more information.

Sub-commands
-------------
Running an MCS with ``pygcam`` involves the following steps:

#. :doc:`Define parameters and distributions <parameters>` in the
   file ``parameters.xml``.

#. Run the :ref:`gensim <gensim-label>` sub-command to create the file
   structure and database required for the MCS and a CSV file containing
   the data for the Monte Carlo trials. Several sampling methods are
   available.

#. Run the simulation by running the :ref:`cluster <cluster-label>` sub-command.
   You can run as many "worker" processes as resources allow.

#. Run the :ref:`anaylze <analyze-label>` sub-command to generate statistical
   information and various types of plots based on input values and results
   stored in the SQL database.

There are additional "utility" sub-commands for running shell commands on
each trial sandbox, and other useful tools.

When an MCS trial runs, it:

#. Reads the row of the CSV file corresponding to its trial number.

#. Reads ``parameters.xml`` and runs the queries for each parameter to
   produce a sets of values.

#. Modifies each set of values as per the instructions by adding to, multiplying
   by, or replacing with the value drawn from the distribution for this trial.
   In the example above, the values returned by the query are multiplied
   by a value drawn from the Uniform distribution [0.5, 2].

#. Writes the modified XML input files to the trial's "sandbox" directory. This
   file is loaded in place of the file previously indicated in the GCAM XML
   configuration file when GCAM runs in this sandbox.


Sampling
----------

The default sampling mode is Latin Hypercube sampling from the distributions
defined in ``parameters.xml``. Using the ``-m`` / ``--method`` argument to the
:ref:`gensim <gensim-label>` sub-command, you can use other alternatives
provided via the SALib package, including:

* The Method of Morris (``-m morris``),
* Sobol sampling (``-m sobol``), and
* Fourier Amplitude Sensitivity Test (``-m fast``).

Other methods can be added via custom plugins.

Note that when using the Morris, Sobol, or FAST methods, the corresponding
sensitivity analysis method must be used to evaluate the results. This is
accomplished by storing the choice of sampling method, optional arguments
to the sampling method, and input data into a set of files within a directory
"package" named ``data.sa`` in the run-time directory structure for the
analysis. Invoking the :ref:`analyze <analyze-label>` sub-command calls
the appropriate sensitivity analysis method for the chosen sampling method.

