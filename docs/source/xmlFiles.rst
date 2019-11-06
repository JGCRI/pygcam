XML File Formats
==================

.. toctree::
   :hidden:

   project-xml
   scenarios-xml
   query-xml
   rewrites-xml
   landProtection-xml
   parameters.xml <mcs/parameters>
   results.xml <mcs/results>
   resPolicy-xml

Various :doc:`gcamtool` sub-commands take input from XML files that are distinct
from those read by the GCAM model itself. These include:

  - :doc:`project-xml` describes all the workflow steps required to run a ``pygcam`` project.

  - :doc:`scenarios-xml` file provides instructions for modifying GCAM configuration
    files to generate desired scenarios. It can be used as an alternative to defining a
    custom Python module, though the latter provides greater customizability.

  - :doc:`query-xml` file describes XML queries to run against the XML database generated
    by GCAM, including aggregation "rewrites" that are added on-the-fly.

  - :doc:`rewriteSets.xml <rewrites-xml>` file describes named sets of "rewrite" statements
    that can be referenced by queries in :doc:`query-xml`.

  - :doc:`landProtection-xml` file describes which types of unmanaged land should "protected",
    (i.e., removed from economic consideration in the model), and at what percentages in each
    region.

  - :doc:`parameters.xml <mcs/parameters>` defines Monte Carlo parameters and distributions.

  - :doc:`results.xml <mcs/results>` defines Monte Carlo results to be saved in the SQL database.

  - :doc:`resPolicy-xml` supports the definition of Renewable Energy Standard
    (RES) policies.

Most of these files allow a custom meta-language I call :doc:`conditional-xml`, which allows
portions of the XML file to be selected based on the values of configuration variables.
