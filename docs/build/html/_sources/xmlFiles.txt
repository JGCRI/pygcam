XML File Formats
==================

Various :doc:`gcamtool` sub-commands take input from XML files that are distinct
from those read by the GCAM model itself. These include:

project.xml
^^^^^^^^^^^^
The :doc:`project-xml` file describes all the workflow steps required to run a ``pygcam`` project.

query.xml
^^^^^^^^^^^
The :doc:`query-xml` file describes XML queries to run against the XML database generated
by GCAM, including aggregation "rewrites" that are added on-the-fly.

rewriteSets.xml
^^^^^^^^^^^^^^^^^
The :ref:`rewriteSets.xml <rewriteSets-label>` file describes named sets of "rewrite" statements that can be
referenced by queries in :doc:`query-xml`.

landProtection.xml
^^^^^^^^^^^^^^^^^^^^
The :doc:`landProtection-xml` file describes which types of unmanaged land should "protected",
(i.e., removed from economic consideration in the model), and at what percentages in each region.


.. toctree::
   :maxdepth: 1

   project-xml
   query-xml
   landProtection-xml
