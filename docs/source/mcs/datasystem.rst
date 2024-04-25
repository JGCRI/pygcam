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
changed CSV files are not re-generated. This is particularly helpful
when running the data system for every trial in a Monte Carlo simulation
since it substantially reduces the time spent building XML files, e.g.,
from ~15-20 minutes to ~5. (Depending on how many XML files need to be
recreated, of course.)

The GCAM data system is not designed to allow multiple build processes
to run simultaneously in a single directory. For example, the ``drake``
code creates a database of file dependencies that represents the state
of the repository. To permit parallel
processing, ``pygcam`` makes a copy of the relevant input and output files
and the ``drake``
database in a temporary directory for each Monte Carlo trial, allowing
trials to generate their own set of updated XML files based on
changes to CSV files resulting from parameter values drawn for that specific
trial. Where possible, files are symbolically linked to the reference
workspace, with link modification times set to match those on the
original files. This saves considerable disk space and avoids copying
large files.

After the XML files are updated for a trial, the modified XML files are
moved to the trial’s ``trial-xml`` directory and the temporary folder that
was used to run the data system is deleted.

.. seealso::
   See :doc:`pygcam.mcs.gcamdata` for support in developing custom plugins.


Support for ``renv``
~~~~~~~~~~~~~~~~~~~~~~~~

The ``R`` language ``renv`` package allows the creation of ``R``
environments with specified versions of ``R`` modules. This is used by
``pygcam`` to establish an environment suitable for running the GCAM
data system.

A suitable ``renv.lock`` file is included in recent GCAM distributions
in the folder ``input/gcamdata``. See the
`Renv <https://rstudio.github.io/renv/articles/renv.html>`_ page for
more information on how to use that module.


The ``moirai`` plug-in
---------------------------

The ``moirai`` plug-in for ``pygcam`` uses the generic features provided
by :doc:`pygcam.mcs.gcamdata` to support Monte Carlo simulations that
included uncertainty in the soil and vegetative carbon densities represented
by the `Moirai Land Data System <https://github.com/JGCRI/moirai>`_
incorporated into GCAM.

The `Moirai Land Data System <https://github.com/JGCRI/moirai>`_ can use
different statistical values from the underlying distributions
of data to represent the carbon data used in building GCAM's XML input files.
This is determined by the ``R`` variable ``aglu.CARBON_STATE``, defined in the
GCAM data system in the file ``input/gcamdata/R/constants.R``. Possible values
for this variable are: ``median_value`` (median of all available grid cells), ``min_value``
(minimum of all available grid cells), ``max_value`` (maximum of all available grid
cells), ``weighted_average`` (weighted average of all available grid cells using
the land area as a weight), ``q1_value`` (first quartile of all available grid
cells) and ``q3_value`` (3rd quartile of all available grid cells). The default
is ``q3_value``.

The ``moirai`` plugin supports the following steps necessary to use
these data in support of Monte Carlo simulations. Specifically, it:

#. Runs the data system 6 times with different ``aglu.CARBON_STATE`` settings,
   saving the results in the file ``moirai-summary-wide.csv``,

#. Combines these 6 files into a summary CSV file with all 6 statistics in
   each row with "index" information (``region_ID``, ``land_type``,
   ``GLU``).

#. Generate arguments for a representative Beta distribution for each
   row of the CSV based on these statistics, storing the values in the file
   ``moirai-beta-args.csv``,

#. Draws values from the imputed Beta distributions and substitutes these
   into the carbon data file used to generate XML files, and

#. Runs the data system using ``driver_drake`` to generate all XML files
   that depend on the carbon data input file.


Notes on the use of Beta distributions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Beta distribution is a very flexible form that can represent a variety
of shapes, from exponential curves to bell-shaped distributions, depending on
the distribution's two shape parameters, `alpha` and `beta`. The ``moirai`` plug-in
uses the ``q1_value`` and ``q3_value`` to solve for these parameters.

Note that the values produced by a Beta distribution are in the range ``[0, 1]``,
so the values drawn from this distribution must be scaled by subtracting the minimum
from ``q1_value`` and ``q3_value`` and then dividing each by the maximum. After
drawing values from the distribution, this scaling must be reversed, e.g.,
``actual_value = draw * max_value + min_value.``

The shape parameters are saved in a CSV along with the statistical
values to facilitate later rescaling. This files is used as an input to the MCS process.

Generating a simulation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To generate a simulation, the following steps are required:

#. Run ``drake`` to create the baseline against which changes are detected:

   ``gt moirai --create-baseline``

#. Run the data system for each of 6 carbon statistics and collect the data into one CSV:

   ``gt moirai --save-moirai-summary``

   This produces the file ``moirai-summary-wide.csv``

#. Generate the implied Beta distributions for each GLU, using min, q1, q3, and max:

   ``gt moirai --save-beta-args``

   This produces the file ``moirai-beta-args.csv``.

#. Modify ``parameters.xml`` to draw percentile values from some distribution,
   e.g., Uniform(0.5, 0.99) to indicate the percentile value to read from
   the implied Beta distributions.

#. Draw C density values from each implied Beta distribution based on
   a given percentile and save these draws in a CSV.

#. Run the gcam data system with a "user modification" function that
   swaps in stochastic C values (re-scaled) for the default values to generate
   the dependent XML files. (In GCAM v7, there are 6 affected files.)

   The best way to do this is to add a ``step`` to the ``project.xml`` file, e.g.,

.. code-block:: xml

    <step name="moirai" runFor="baseline" optional="true">
        @moirai --gen-xml -S {baseline} -t PATH
    </step>

and to modify the ``pygcam`` configuration variable declaring the setup steps to use
to run the new ``moirai`` step after setting up the sandbox and config file but before
running configuration steps that reference XML files:

.. code-block:: cfg

   MCS.SetupSteps = create-sandbox,config-setup,moirai,non-config-setup


Caveats
~~~~~~~~~~

* The Beta distribution isn't a good fit for the bimodal distributions found in the some
  of the carbon data.

* In cases in which the minimum and Q1 values are the same in moirai, we substitute 20% of Q1
  for the minimum value.


Example distributions for moirai carbon densities
----------------------------------------------------

The following snippet from a ``parameters.xml`` file defines distributions for the
percentile values to draw from the Beta distribution implied by the statistics
gleaned from the moirai data.

.. code-block:: xml

  <InputFile name="moirai-data" type="csv">
    <!-- 'type=xml' is the default; use csv to affect a data system CSV file -->

    <Parameter name="cropland-veg-c">
      <Distribution>
        <Uniform min="0.5" max="0.99"/>
      </Distribution>
    </Parameter>

    <Parameter name="pasture-veg-c">
      <Distribution>
        <Uniform min="0.5" max="0.99"/>
      </Distribution>
    </Parameter>

    <Parameter name="forest-veg-c">
      <Distribution>
        <Uniform min="0.5" max="0.99"/>
      </Distribution>
    </Parameter>

    <Parameter name="grass-shrub-veg-c">
      <Distribution>
        <Uniform min="0.5" max="0.99"/>
      </Distribution>
    </Parameter>

    <Parameter name="cropland-soil-c">
      <Distribution>
        <Uniform min="0.5" max="0.99"/>
      </Distribution>
    </Parameter>

    <Parameter name="pasture-soil-c">
      <Distribution>
        <Uniform min="0.5" max="0.99"/>
      </Distribution>
    </Parameter>

    <Parameter name="forest-soil-c">
      <Distribution>
        <Uniform min="0.5" max="0.99"/>
      </Distribution>
    </Parameter>

    <Parameter name="grass-shrub-soil-c">
      <Distribution>
        <Uniform min="0.5" max="0.99"/>
      </Distribution>
    </Parameter>
  </InputFile>
