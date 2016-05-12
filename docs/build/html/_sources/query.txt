``pygcam.query``
============================

This module contains classes and a sub-command that allow you to run batch queries
against GCAM's XML database, generate label rewrites on the fly, and perform
various common operations on the resulting .csv files.

.. _DataFrames:
.. _DataFrame: http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html

Running queries by name
^^^^^^^^^^^^^^^^^^^^^^^^^

The query module looks for queries by name in any of the directories or files listed in the
Query Path, which is specified as an argument to the function :py:func:`pygcam.query.runBatchQuery`,
on the command-line to the :ref:`query sub-command <query-label>`, or by the value of the
config variable ``GCAM.QueryPath``.

configuration parameter ``GCAM.QueryPath``. Elements are separated by ';' on Windows and by
':' otherwise. The elements can be:

  1. An XML file structured like the standard GCAM queries file, ``Main_Queries.xml``,
  2. An XML file structured like a batch query file, or
  3. A directory holding XML files defining queries.

To locate the query code, each element of ``GCAM.QueryPath`` is examined, in order, for the named
query and variations thereof (more below.)

If a path element is a directory, we look for a file with the exact query name and an ``.xml``
extension. If the file exists, it is not altered in any way; it is simply referenced from the
generated batch query file. If a path element is not a directory, it must be the name of an XML
file in the format of Main_Queries.xml or a query file for use as a batch query. To find the
query, the ``title`` attribute is compared directly and with the variants below, in this order:

   1. Original name, but with all '-' changed to spaces.
   2. Original name, but with all '_' changed to spaces.
   3. Original name, but with all '-' and '_' changed to spaces.

Running sets of queries
^^^^^^^^^^^^^^^^^^^^^^^^^
The :ref:`query sub-command <query-label>` allows a set of queries to be identified
in a text file, with one query name per line, or in an XML file that offers additional
features. See :doc:`query-xml` for information on the XML file format.

Extracting queries
^^^^^^^^^^^^^^^^^^^


Generating label rewrites to aggregate and filter results
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  .. note::

        This section describes a new feature that is subject to change

The user can define a set of queries in an XML file. The query elements are processed
in order, adding any designated label rewrites to the query.

The :ref:`query sub-command <query-label>` runs the batch query in ModelInterfaces and saves
the results in the designated .CSV file. The :doc:`gcamtool` page for command-line options.

Label rewrites are currently defined in a separate XML file, for which the default path is
given in pygcam's system configuration file by the variable ``GCAM.RewriteSetsFile``; it
defaults to ``%(ProjectRoot)s/queries/rewriteSets.xml``. The format of this XML file is
described in :doc:`query-xml`.



API
---

.. automodule:: pygcam.query
   :members:

