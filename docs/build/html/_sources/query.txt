``pygcam.query``
============================

This module contains classes that allow you to run batch queries against
GCAM's XML database and perform various common operations on the resulting
.csv files. This module relies heavily on the pandas `DataFrame`_ class.

.. _DataFrames:
.. _DataFrame: http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html

The query module looks for queries by name in any of the directories or files listed in the
configuration parameter ``GCAM.QueryPath``. Elements are separated by ';' on Windows and by
':' otherwise. The elements can be:

  1. An XML file structured like the standard GCAM queries file, ``Main_Queries.xml``,
  2. An XML file structured like a batch query file, or
  3. A directory holding XML files defining queries.

To locate the query code, the given name and variations thereof are sought in each element
of ``GCAM.QueryPath``, in order. For path elements that
are directories, a file with the query name and the ``.xml`` extension. For path elements
that are XML batch query or "Main_Query" type files, a query with a ``title`` attribute
matching the query name is sought.

For each element of the path, the query name is checked first as given. If not found,
variations of the name are checked in this order:

   1. Original name, but with all '-' changed to spaces.
   2. Original name, but with all '_' changed to spaces.
   3. Original name, but with all '-' and '_' changed to spaces.


API
---

.. automodule:: pygcam.query
   :members:

