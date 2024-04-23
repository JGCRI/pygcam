Running the GCAM data system
=====================================

Overview
----------

The GCAM data system takes input files in CSV format and, through a
series of R scripts, transforms these data into the XML files that are
read as inputs by GCAM. The data system can be run using
``driver_drake``, based on the ``drake`` package, which tracks file
dependencies across data system components, thereby minimizing the
work required to generate those XML files dependent on changed CSV
files. XML files that don’t depend, directly or indirectly, on the
changed CSV files are not re-generated.

The GCAM data system is not designed to allow multiple build processes
to run simultaneously in a single directory. To permit parallel
processing, ``pygcam`` makes a copy of the relevant files and drake
database in a temporary directory for each Monte Carlo trial, allowing
each trial to generate its own set of updated XML files based on
changes to CSV files and parameter draws for that specific
trial. Where possible, files are symbolically linked to the reference
workspace, with link modification times set to match those on the
original files.

After the XML files are updated, the modified XML files are moved to
the trial’s ``trial-xml`` directory and the temporary folder used to
run the data system is deleted.

.. seealso::
   See :doc:`pygcam.mcs.gcamdata` for support in developing custom plugins.


Support for ``renv``
~~~~~~~~~~~~~~~~~~~~~~~~

The ``R`` language ``renv`` package allows the creation of ``R``
environments with specified versions of ``R`` modules. This is used by
``pygcam`` to establish and environment suitable for running the GCAM
data system.

The ``moirai`` plug-in
---------------------------

**Add a description**

Does several things, noted in comments at the very top, including
running the data system with different ``CARBON_STATE`` settings, saving
all results in ``moirai-summary-wide.csv``, generating
``moirai-beta-args.csv``, and drawing values from the implied Beta
distributions.

Pre-processing
~~~~~~~~~~~~~~~

#. Run the datasystem 6 times to generate 6 CSV files with intermediate
   results for soil carbon based on choosing each of six available
   statistics (min, max, Q1, median, Q3, mean) from the moirai system,
   one at a time. The same is performed for vegetative carbon.

#. Combine these 6 files into a summary CSV file with all 6 stats in
   each row with "index" information (region_ID, land type,
   GLU).

#. Generate arguments for a representative Beta distribution for each
   row of the CSV based on these statistics.

Use the Q1 and Q3 values to solve for the Beta distribution's two shape
parameters, `alpha` and `beta`.

Note that the values produced by a Beta distribution are in the range [0, 1],
so the values drawn from this distribution must be scaled by subtracting the minimum
from Q1 and Q3 and then dividing each by the maximum. (Later, after drawing
from the distribution, this scaling is reversed:
``soil_c = draw * max + min.)``

The implied Beta shape parameters are saved in a CSV along with the statistical
values to facilitate rescaling. This files is used as an input to the MCS process.


Generating a simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Modify ``parameters.xml`` to draw percentile values from some distribution,
   e.g., Uniform(0.5, 0.99) to indicate the percentile value to read from
   the implied Beta distributions.

#. Draw C density values from each implied Beta distribution based on
   a given percentile and save these draws in a CSV.

#. Run the gcam data system with a "user modification" function that
   swaps in stochastic C values (re-scaled) for the default values to generate
   the dependent XML files. In GCAMv7, there are 6 of these.

#. Modify the GCAM config file via ``scenarios.xml`` to use the newly generated
   XMLs rather than the standard ones.


moirai-summary-wide.csv
~~~~~~~~~~~~~~~~~~~~~~~~~~~

All soil and veg C values for all values of ``R`` variable ``CARBON_STATE``.


moirai-beta-args.csv
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Values for the two parameters for the Beta distribution for each
location and land type. These are the parameters to produce the
standard form Beta, which has bounds of [0, 1]. The draws must by
scaled, i.e., ``draw * (max - min) + min`` to produce C density
values.

Caveats
~~~~~~~~~~

* The Beta distribution doesn’t fit well bimodal distributions found in the some cases in the data.
* In cases in which the minimum and Q1 values are the same in moirai, we substitute 20% of Q1 is
  for the minimum value .
