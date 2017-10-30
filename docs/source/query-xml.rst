.. _query-xml:

The ``query`` sub-command and the underlying :py:func:`pygcam.query.runBatchQuery`
function allow you to specify an XML file that describes a sequence of query
to execute. The queries can reference named sets of label rewrite statements that
allow results to be renamed, aggregated, or ignored. Here we document the format of
the two XML files.

    .. seealso::

       See :doc:`pygcam.query` for more information about run-time behavior.
       Command-line usage is described on the :ref:`gt query<query>` page.

       Some elements of the ``query.xml`` file can contain ``<CONDITIONAL>``
       elements, as described below. See :doc:`conditional-xml` for further details.


queries.xml
===============
The ``queries.xml`` file defines a set of queries to execute. It's elements
are described below, followed by a short example.

XML elements
------------

The elements that comprise the ``queries.xml`` file are described below.

<queries>
^^^^^^^^^^

The top-most element, ``<queries>``, encloses one or more ``<query>``
elements. The ``<queries>`` element may also contain ``<CONDITIONAL>``
elements. The ``<query>`` element takes the following attributes:

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| varName     | depends    | (none)    | text     |
+-------------+------------+-----------+----------+
| defaultMap  | no         | (none)    | text     |
+-------------+------------+-----------+----------+
| delete      | no         | "1"       | boolean  |
+-------------+------------+-----------+----------+

The `varName` is required for ``<queries>`` defined in the ``project.xml`` file;
it defines a variable name which is assigned the path of a temporary file
into which the ``<queries>`` element and sub-elements are copied. If an
external queries file is used, the varName is ignored.

The ``defaultMap`` defines a default :doc:`rewrite set <rewrites-xml>` to use
with all queries, which can be overridden for any single query by explicitly
specifying ``useDefault="0"``.

The ``delete`` attribute defines whether the temporary file generated from
the ``<queries>`` element in the project.xml file should be deleted. This
is primarily for debugging.

<query>
^^^^^^^^^

The ``<query>`` element specifies a query to run. The required
name attribute must match the name of a query found on the Query
Path, which is specified as an argument to the function
:py:func:`pygcam.query.runBatchQuery`, on the command-line to the ``query``
sub-command, or by the value of the config variable ``GCAM.QueryPath``.

The ``<query>`` element can contain zero or more ``<rewriter>``
elements and may contain ``<CONDITIONAL>`` elements.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+
| saveAs      | no         | name      | text     |
+-------------+------------+-----------+----------+
| useDefault  | no         | "1"       | boolean  |
+-------------+------------+-----------+----------+

By default, the results for the query are saved to a file based on
`name` and the scenario name. However, using the `saveAs` option
allows you to save results to a different name, allowing a single
query to be run multiple times with different rewrites to produce
multiple CSV files.

The `useDefault` attribute provides a way to override any
`defaultMap` specified in the surrounding ``<queries>`` element.
Set ``useDefault="0"`` to prevent the default rewrite map from
applying to this ``<query>``.

<rewriter>
^^^^^^^^^^
This element identifies a :doc:`rewrite set <rewrites-xml>` by name.
The rewrite set must be defined in a file identified as an argument
to the :py:func:`pygcam.query.runBatchQuery`, on the command-line to
the :ref:`query sub-command <query>`, or by setting a value for
the config variable ``GCAM.RewriteSetsFile``.

The query named in the ``<query>`` node is extracted into a
temporary file and the specified rewrites are inserted into the
query. If a ``level`` is specified, it identifies the variable
in the query output that should be rewritten according to the
``<rewrite>`` elements in the corresponding rewrite set.

If no ``level`` is specified, the level giving in the query
definition itself is used. In most cases, the user will not
need to specify a level in the ``<rewriter>`` statement, but
the option is available to override the default.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+
| level       | no         | (none)    | text     |
+-------------+------------+-----------+----------+

Example
^^^^^^^^
This is an example of a query specification file.

  .. code-block:: xml

     <queries varName="queryXmlFile" defaultMap="eightRegions">
        <query name="land_cover">
            <rewriter name="eightRegions"/>
            <rewriter name="landCover"/>
        </query>

        <query name="Aggregated Land Allocation"/>

        <query name="luc_emissions"/>

        <query name="ag_production" useDefault="0">
            <rewriter name="GTAP-BIO-ADV"/>
            <rewriter name="food" level="input"/>
        </query>

        <query name="nonco2"/>
        <query name="Climate_forcing"/>
        <query name="Global_mean_temperature"/>
     </queries>
