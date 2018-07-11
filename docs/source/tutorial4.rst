Tutorial, Part 4
==================

In this part of the tutorial, we look at the queries that are defined
in ``project.xml`` and the use of "rewrites" to aggregate the
results in different ways.

4.0 Queries
-------------
The queries identified in the project file (or in an external file) determine which
results are extracted from the GCAM database for each run of the model, and thus
determine which subsequent steps (computing differences, creating charts) can be
performed.

GCAM uses an XML-based database for which queries are likewise composed in XML.
The database is managed by the java-based ModelInterface program provided in
the GCAM distribution. There is also a standard file called "Main_Queries.xml"
that is used by ModelInterface to provide interactive access to these queries.

``Pygcam`` executes queries by creating XML query files and invoking the ModelInterface
program in "batch" (non-interactive) mode to generate CSV files. You can craft query
files by hand, or you can use pre-existing ones in Main_Queries.xml or some other
file with custom queries.

The queries themselves can be extracted on-the-fly from these files by specifying
the location of the XML file in the configuration variable ``GCAM.QueryPath`` and
referencing the desired query by its defined "title". (See the
:ref:`query sub-command <query>` and the :doc:`pygcam.query` API documentation
for more information.) In general, there is little need to create individual query
files; anything you can run in ModelInterface can be run by ``pygcam`` as well.

Queries can be run several ways in GCAM:

  #. If an XML database is written to disk (the default), queries can be
     run on the database using the ModelInterface.jar file, which is used
     by the :ref:`query sub-command <query>`.

  #. If the XML database is written to disk, GCAM can run the queries before
     it exits, using the same mechanism as in the option above.

  #. Since v4.3, GCAM can write its XML database to memory only, in
     which case it *must* be queried from within GCAM since the database will
     no longer exist after GCAM exits. This is particularly useful in large
     ensemble (e.g., Monte Carlo simulation) runs where you want to extract some
     data but don't need to keep the large databases around.

Two configuration file parameters control this behavior. The variables and
their default values are shown below. Add these to your ``.pygcam.cfg`` file
with appropriate ``True`` or ``False`` values to configure GCAM as you wish.

.. code-block:: cfg

    # Setting ``GCAM.InMemoryDatabase`` to ``True`` forces ``GCAM.RunQueriesInGCAM``
    # to be ``True`` since there is no other way to run queries in this case.
    GCAM.InMemoryDatabase = False
    GCAM.RunQueriesInGCAM = False

.. note::
   Using the in-memory database substantially increases GCAM's memory footprint, particularly
   since version 5.0, so it may be impractical to use this feature in some cases.


4.1 Processing of query definitions
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

4.2 Rewrite sets
------------------
Standard GCAM XML queries can define "rewrites" which modify the values of chosen
data elements to allow them to be aggregated. For example, you can aggregate all
values of CornAEZ01, CornAEZ02, ..., CornAEZ18 to be returned simply as "Corn".

In ``pygcam`` this idea is taken a step further by allowing you to define reusable,
named "rewrite sets" that can be applied to queries named in the project file.
For example, if you are working with a particular
regional aggregation, you can define this aggregation once in a ``rewrites.xml`` file
and reference the name of the rewrite set when specifying queries in :doc:`project-xml`.
See :doc:`rewrite sets <rewrites-xml>` for more information.

Defining queries with rewrites
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following example ``rewriteSets.xml`` file is copied into new projects:

.. literalinclude:: ../../pygcam/etc/examples/rewriteSets.xml
   :language: xml
   :linenos:

We can reference any of these sets in the ``<queries>`` section of the ``project.xml``
file. We can define a list of rewrite sets to apply by default to all queries, and
we can define rewrites to apply to individual queries (as well as opt out of the
default rewrites in any individual query.)

Let's now use the pre-defined "eightRegions" set to aggregate the 32 regions to
simplify the plot of Land Use Change Emissions we've been working on. To do this,
we change the line for this query in ``project.xml`` from

.. code-block:: xml

   <query name="Land_Use_Change_Emission"/>

to:

.. code-block:: xml

   <query name="Land_Use_Change_Emission">
      <rewriter name="eightRegions"/>
   </query>

We then need to rerun the queries for both the baseline and policy scenarios, recompute
the differences, and re-generate the plots. We can do that with this command::

    $ gt run -s query,diff,plotDiff -S base,tax-10

This results in the following figure:

---------

  .. image:: images/tutorial/Land_Use_Change_Emission-tax-10-base-by-region-mod3.*

---------

or, if we restore the original aesthetic choices, we have this:

---------

  .. image:: images/tutorial/Land_Use_Change_Emission-tax-10-base-by-region-mod4.*

