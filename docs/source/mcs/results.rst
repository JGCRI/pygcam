Saving trial results
===================================

The file ``results.xml`` describes model results that should be saved in
the SQL database. The values must be available in CSV files, which are
generally the results of queries against the GCAM XML database, or they
can be the results of arbitrary calculations.

The general idea is that the results are named, a file is identified,
and the location in the file of the relevant values is identified using
a combination of ``<Column>`` and ``<Constraint>`` elements.

Below is a detailed description of the XML elements used in ``results.xml``,
and finally, an example file.

XML elements
------------

<ResultList>
^^^^^^^^^^^^^^^^^
This is the top-level element in the ``results.xml`` file. It must contain
one or more ``<Result>`` elements and can contain any number of ``<comment>``
elements. The ``<ResultList>`` element takes no attributes.

<Result>
^^^^^^^^^^^
The ``<Result>`` element describes a single result to store in the SQL
database. It may contains zero or one  ``<File>`` elements, zero or one
``<Column>`` elements, and any number of ``<Constraint>`` or ``<comment>``
elements.

Results can be scalar values or time-series data. If no ``<Column>`` element
is given, the result is assumed to be a time-series, and values for all year
columns are stored in the "timeseries" table in the SQL database. Scalar results
are stored in the "outvalue" table.

The ``<Result>`` element accepts the following attributes:

+-------------+------------+-----------+-------------+
| Attribute   | Required   | Default   | Values      |
+=============+============+===========+=============+
| name        | yes        | (none)    | text        |
+-------------+------------+-----------+-------------+
| type        | yes        | (none)    | *see below* |
+-------------+------------+-----------+-------------+
| desc        | no         | (none)    | text        |
+-------------+------------+-----------+-------------+

The result ``type`` must be either "diff" or "scenario". The prior
indicates a result that is the difference between a policy scenario
and a baseline, whereas the latter is a result for a single baseline
or scenario.

The optional ``desc`` attribute allows you to provide a description,
which is stored in the database and can be displayed in graphical
figures.


<File>
^^^^^^^^^^^
Indicates a CSV file from which to read numerical results.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+


<Column>
^^^^^^^^^^^
The ``<Column>`` element indicates the column of the CSV
file holding the data. If the column holds multiple rows
of data, use a ``<Constraint>`` element to isolate the
desired rows within that column.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

The ``name`` attribute identifies the column in the CSV file.


<Constraint>
^^^^^^^^^^^^^
Describes how to isolate data within a CSV file to save as
a named result. This is roughly equivalent to a SQL "where"
clause which specifies that a column must have a given
relationship to a given value. The ``column`` attribute
indicates which column to apply the constraint to; the ``value``
attribute provides a value to compare against; and the ``op``
attribute indicates how to perform the comparison.

+-------------+------------+-----------+-------------+
| Attribute   | Required   | Default   | Values      |
+=============+============+===========+=============+
| column      | yes        | (none)    | text        |
+-------------+------------+-----------+-------------+
| op          | yes        | (none)    | *see below* |
+-------------+------------+-----------+-------------+
| value       | yes        | (none)    | text        |
+-------------+------------+-----------+-------------+

The following values for ``op`` are recognized:

 * ``==``, ``=``, ``eq``, ``equal`` : synonyms for equality, i.e.,
   the value in the named column must be the same as ``value``.

 * ``<>``, ``!=``, ``neq``, ``notEqual``, ``not equal`` : synonyms for
   inequaltiy, i.e., the value in the named column must be different
   than ``value``.

 * ``startswith`` : the value in the named column must start with
   the given ``value``.

 * ``endswith`` : the value in the named column must end with
   the given ``value``.

 * ``contains`` : the value in the named column contain the string
   given in ``value``. Note that ``contains`` accepts Python
   `regular expressions <https://docs.python.org/2/library/re.html>`_,
   which means special regex characters must be "escaped" by preceding
   them with a "\" character. See the documentation link above for
   further details.


Example
--------
Following is an example of a ``results.xml`` file.

.. literalinclude:: ../../../pygcam/mcs/etc/results-example.xml
   :language: xml
