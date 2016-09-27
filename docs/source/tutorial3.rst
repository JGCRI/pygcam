Tutorial, Part 3
==================

 .. note:: This section is under development.

In this part of the tutorial, we will modify the queries that are defined
in ``project.xml`` and change the "rewrites" to aggregate the
results in different ways.

3.1 Queries
-------------
The queries identified in the project file (or in an external file) determine which
results are extracted from the GCAM database for each run of the model, and thus
determine which subsequent steps (computing differences, creating charts) can be
performed. To plot results, you must first extract them from the database using
a query.

Queries can be extracted on-the-fly from files used with ModelInterface by specifying
the location of the XML file in the configuration variable ``GCAM.QueryPath`` and
referencing the desired query by its defined "title". (See the
:ref:`query sub-command <query-label>` and the :doc:`pygcam.query` API documentation
for more information.)

3.2 Rewrite sets
------------------
Standard GCAM XML queries can define "rewrites" which modify the values of chosen
data elements to allow them to be aggregated. For example, you can aggregate all
values of CornAEZ01, CornAEZ02, ..., CornAEZ18 to be returned simply as "Corn".

In ``pygcam`` this idea is taken a step further by allowing you to define reusable,
named "rewrite sets" that can be applied on-the-fly to
queries named in the project file. For example, if you are working with a particular
regional aggregation, you can define this aggregation once in a ``rewrites.xml`` file
and reference the name of the rewrite set when specifying queries in :doc:`project-xml`.
See :doc:`rewrite sets <rewrites-xml>` for more information.
