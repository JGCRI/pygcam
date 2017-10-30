Tutorial, Part 4
==================

.. note:: This section is under development.

In this part of the tutorial, we look at the queries that are defined
in ``project.xml`` and the use of "rewrites" to aggregate the
results in different ways.

4.1 Queries
-------------
The queries identified in the project file (or in an external file) determine which
results are extracted from the GCAM database for each run of the model, and thus
determine which subsequent steps (computing differences, creating charts) can be
performed. To plot results, you must first extract them from the database using
a query.

Queries can be extracted on-the-fly from files used with ModelInterface by specifying
the location of the XML file in the configuration variable ``GCAM.QueryPath`` and
referencing the desired query by its defined "title". (See the
:ref:`query sub-command <query>` and the :doc:`pygcam.query` API documentation
for more information.)

Queries can be run several ways in the latest version of GCAM:

  #. If an XML database is written to disk (the default), queries can be
     run on the database using the ModelInterface.jar file, which is used
     by the :ref:`query sub-command <query>`.
  #. If the XML database is written to disk, GCAM can run the queries before
     it exits, using the same mechanism as in the option above.
  #. A new feature of GCAM allows it to store the XML database in memory, in
     which case it *must* be queried from within GCAM since the database will
     no longer exist after GCAM exits.

Two configuration file parameters control this behavior. The variables and
their default values are shown below. Add these to your ``~/.pygcam.cfg`` file
with appropriate ``True`` or ``False`` values to configure GCAM as you wish.

.. code-block:: cfg

    GCAM.InMemoryDatabase = False
    GCAM.RunQueriesInGCAM = False

Note that setting ``GCAM.InMemoryDatabase`` to ``True`` forces
``GCAM.RunQueriesInGCAM`` to be ``True`` as well, since no other option is
feasible.


4.2 Rewrite sets
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

4.3 Defining queries with rewrites
------------------------------------

The following is an example of defining a set of queries for a project:

.. code-block:: xml
   :linenos:

   <queries varName="queryXmlFile" defaultMap="eightRegions">
       <query name="Land_Allocation">
            <rewriter name="eightRegions"/>
            <rewriter name="landAllocation"/>
        </query>
        <query name="Ag_Production_by_Crop_Type">
            <rewriter name="eightRegions"/>
            <rewriter name="crops"/>
        </query>
        <query name="land_cover"/>
        <query name="luc_emissions"/>
        <query name="nonco2"/>
        <query name="Refined_liquids_for_vehicles_production_by_technology"/>
        <query name="Climate_forcing"/>
        <query name="Global_mean_temperature"/>
   </queries>


This ``<queries>`` element at line 1 defines a variable named ``queryXmlFile`` and
establishes a default rewrite by setting ``defaultMap="eightRegions"``. This will
be applied to all queries that do not override this by specifying ``useDefault="False"``,
or specify other ``<rewriter>`` elements.

Query definitions, using the ``<query>`` element, begin at line 2. The first query,
``Land_Allocation`` applies the rewriter named ``landAllocation``. Since it specifies
an explicit rewriter, the default ("eightRegions") would not be applied, so it is
also specified explicitly. Similarly, for the second query, ``Ag_Production_by_Crop_Type``,
at line 6. The remaining queries are run using the default rewriter.

4.4 Processing of query definitions
------------------------------------
When the ``project.xml`` file is read, the ``<queries>`` element is saved to
a temporary file, the pathname of which is stored in the variable given by the
``varName`` attribute. In the case above, the pathname is stored in ``queryXmlFile``.

The stored filename can be accessed in command steps using curly braces, i.e.,
``{queryXmlFile}``. The ``query`` and and ``diff`` sub-commands both understand
the format of this file. The ``query`` sub-command obviously runs the queries as
indicated, whereas the ``diff`` command uses the query names to identify the
resulting CSV files that should be compared. Examples of the ``<step>`` elements
using the temporary query file are as follows:

.. code-block:: xml

    <step name="query" runFor="policy">@query -o {batchDir} -w {scenarioDir} -s {scenario} -Q "{queryPath}"  -q "{queryXmlFile}"</step>
    <step name="diff"  runFor="policy">@diff -D {sandboxDir} -y {years} -Y {shockYear} -q "{queryXmlFile}" -i {baseline} {scenario}</step>

Note that the double-quotes around ``{queryXmlFile}`` are necessary only if the pathname
contains blanks; using them is good "defensive programming" practice.

