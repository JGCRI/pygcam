scenarios.xml
===============

The ``scenarios.xml`` provides instructions for modifying a GCAM
configuration XML file. The file, which is processed by the
:ref:`setup <setup-label>` sub-command, cad define one or more
groups of related scenarios, and provides an iteration feature
that allows automated generation of a set of related scenarios.

    .. seealso::

       The :doc:`setup` page provides an overview of setup system. See
       :doc:`pygcam.xmlEditor` for more information about the Python API.
       Command-line usage is described on the :ref:`gt setup <setup-label>` page.

    .. note::

       When developing scenario definitions using iterators, it can be helpful
       to see the generated XML. You can set the configuration variable
       ``GCAM.ScenarioSetupOutputFile`` to a pathname to which the expanded
       XML should be written after the ``setup`` sub-command has been run.

The XML element of the ``scenarios.xml`` file are described below, followed by an
example.

XML elements
------------

The elements that comprise the ``scenarios.xml`` file are described below.

    .. note::

       All elements can be wrapped in a ``<comment> ... </comment>`` element
       to effectively remove them from the input stream. This is provided to
       allow commenting sections that themselves contain comments.

<setup>
^^^^^^^^^^

The top-most element, ``<setup>``, encloses one or more ``<scenarioGroup>``
elements, zero or more ``<iterator>`` elements, and zero or more ``<comment>``
elements. The ``<setup>`` element takes the following attributes:

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| defaultGroup| no         | (none)    | text     |
+-------------+------------+-----------+----------+

The ``defaultGroup`` attribute of ``<setup>`` identifies the default
scenarioGroup to use when no group is explicitly identified in
the :ref:`gt setup <setup-label>` command.


<scenarioGroup>
^^^^^^^^^^^^^^^^

The ``<scenarioGroup>`` element defines a set of two or moreo related
``<scenario>`` elements, including one baseline scenario and one or more
policy scenarios. It may also include zero or more ``<comment>`` elements.

+----------------+------------+-----------+----------+
| Attribute      | Required   | Default   | Values   |
+================+============+===========+==========+
| name           | yes        | (none)    | text     |
+----------------+------------+-----------+----------+
| useGroupDir    | no         | "0"       | boolean  |
+----------------+------------+-----------+----------+
| iterator       | no         | (none)    | text     |
+----------------+------------+-----------+----------+
| baselineSource | no         | (none)    | text     |
+----------------+------------+-----------+----------+

The required `name` attribute must match the name of a
scenario defined in the :doc:`project-xml` file.

When a project contains multiple scenario groups, it can keep the groups
separated by using the group dir in the path. The `useGroupDir` attribute
indicates whether the name of the scenario group should be used when
composing pathnames of the scenario group's XML files.

The `iterator` attribute identifies an iterator (defined withing
the ``<scenarioGroup>`` to use to generate a series of scenario
groups and/or scenarios. (See the next section and the
:ref:`example <setup-example>` below.)

The `baselineSource` attribute allows the baseline for one scenario
group to be based on the baseline for another scenario group in the
same setup file. The argument to the `baselineSource` attribute must
be of the form "groupName/baselineName". For example, if the baseline
(named 'base-1a') for scenario group "Bar" is sourced from scenario
group "Foo", whose baseline is named "foobase", you would use the
following definition:

  .. code-block:: xml

     <scenarioGroup name="Bar" useGroupDir="1" baselineSource="Foo/foobase">
        <scenario name="base-1a" baseline="1">

Note that this use pattern requires that you use group directory names
for each scenario group in a project, which is a good organizing approach
in any case.

The configuration file generated for the source
group's baseline is copied as the starting point for the current
group's baseline configuration, rather than using the GCAM reference
configuration file. This avoids duplication of sequences of actions
that are shared among scenario groups.

<iterator>
^^^^^^^^^^
This element identifies an iterator that can be used to automatically
generate a set of ``<scenarioGroup>`` and/or ``<scenario>`` elements
whose names are a function of the iterator value.

There are three types of iterators: integer, floating point, and a
comma-delimited list of text values. In each case, the setup command
iterators over the given (or implied) set of values and substitutes
the value where the name of the iterator is specified within curly
braces, e.g., ``{myIterator}``.

For example, to create 3 scenarios called ``scen-1``, ``scen-2``,
and ``scen-3``, you can define an integer iterator (here, named
"ssp") with a minimum value of 1, a maximum of 2 and a step of
1 (the default):

  .. code-block:: xml

     <iterator name="ssp" min="1" max="3">

You would then define the scenario name as

  .. code-block:: xml

     <scenario name="scen-{ssp}">

which would result in the desired scenarios. Of course, for these
to be useful, they need to create different configuration files.
This is accomplished by using iterator names in the names of the
relevant XML files. For example, you might have a set of files that
define alternatives that you number 1 through three. You would then
select the correct one by using the line:

  .. code-block:: xml

     <replace name="cement_2">{scenarioDir}/cement_incelas_ssp{ssp}.xml</replace>

Note that in addition to iterators defined in the scenario group, two variables
are added automatically: ``scenarioDir`` and ``baselineDir``, which refer to paths
relative to the GCAM "exe" directory to the directories for the current scenario
and, for non-baseline scenarios, for the baseline.

The ``<iterator>`` element recognizes the following attributes:

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+
| type        | yes        | (none)    | see below|
+-------------+------------+-----------+----------+
| min         | no         | (none)    | numeric  |
+-------------+------------+-----------+----------+
| max         | no         | (none)    | numeric  |
+-------------+------------+-----------+----------+
| step        | no         | (none)    | numeric  |
+-------------+------------+-----------+----------+
| format      | no         | (none)    | text     |
+-------------+------------+-----------+----------+
| values      | no         | (none)    | text     |
+-------------+------------+-----------+----------+

The `type` must be one of {int, float, list}. For the numeric types,
int and float, a `min` and a `max` must be specified. These are
coerced (if necessary) to the indicated type. Step is optional and
defaults to 1. The values generated are inclusive of the min and max
values. The `values` attribute is used only with ``type="list"``; its
value should be a comma-delimited series of text or numeric values. A
comma before or after no other content (or blank) results in a value
of the empty string, which can be useful in some cases.

The `format` allows you to specify how to represent values when converted
to a string, using the formatting convention common to many programming
languages. This is most useful for "float" iterators, as it lets you specify
the number of decimal places to include. For example, a format of ``%.2f``
indicates a floating point value with 2 digits to the right of the decimal point.
The default float format is ``%.1f``, allowing one digit after the decimal point.

For example, to generate the set of values {0.00, 0.25, 0.50, 0.75, 1.00}, you could
create either of the following iterators:

  .. code-block:: xml

     <iterator name="fraction" type="float" min="0" max="1" step="0.25" format="%.2f"/>

or

  .. code-block:: xml

     <iterator name="fraction" type="list" values="0.00,0.25,0.50,0.75,1.00"/>

The two approaches produce identical results. Use whichever you find more convenient.
The "list" case is more flexible in that the values need not all have the same format,
while the "int" and "float" versions would be more convenient for a large number of
scenarios. The list form allows iteration over distinctly formatted values, e.g.,

  .. code-block:: xml

     <iterator name="fraction" type="list" values="0,0.25,0.5,0.75,1"/>

In this case, '0.00' and '1.00' are shortened to '0' and '1', respectively.


<scenario>
^^^^^^^^^^^^^^^^

The ``<scenario>`` element defines a single scenario. It contains a
sequence of one or more "actions" that manipulate the scenario's
configuration file and (optionally) modify and create local copies
of GCAM reference files or files defined in the baseline scenario.
It may also contain zero or more ``<comment>`` elements.

The ``<scenario>`` element accepts the following attributes:

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+
| baseline    | no         | "0"       | boolean  |
+-------------+------------+-----------+----------+
| iterator    | no         | (none)    | text     |
+-------------+------------+-----------+----------+

The `baseline` attribute is used to identify the baseline scenario. Only
one scenario in a ``<scenarioGroup>`` can be identified as the baseline.

The value of the `iterator` attribute must be the name of an iterator
defined in the current ``<scenarioGroup>``. When an `iterator` is used,
a single ``<scenario>`` generates a sequence of
scenarios based on the values of the iterator, as described above.

Actions: <add>, <insert>, <replace>, <delete>, <function>, and <if>
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are five action elements that operate on the configuration file. The
elements ``<add>``, ``<insert>``, ``<replace>``, and ``<delete>`` operate
directly on XML configuration elements. The ``<function>`` element call
certain internal methods of the :doc:`pygcam.xmlEditor` class (and its
designated subclasses) that can modify the configuration and/or
modify and create local copies of GCAM reference files or files defined
in the baseline scenario. Finally, the ``<if>`` element allows some content
to be included conditionally. Examples of each are provided
:ref:`below <setup-example>`.

To maintain the ability to edit files programmatically using the the setup
system, the name assigned to any new component should be unique among the
scenario components.

<add>
~~~~~~~~~~~~
Adds a new "scenario component" element to the configuration file,
at the end of the list of components. The text content of the element
should be the name of the new XML file to include.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

.. | dir         | no         | (none)    | text     |
.. +-------------+------------+-----------+----------+

<insert>
~~~~~~~~~~~~
Adds a new scenario components after the component with the name
specified by the `after` attribute. The text content of the element
should be the name of the new XML file to include.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+
| after       | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

.. | dir         | no         | (none)    | text     |
.. +-------------+------------+-----------+----------+

<replace>
~~~~~~~~~~~~
Replace the XML file in the scenario component with the given name
with that given in the text content of the ``<replace>`` element.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

.. | dir         | no         | (none)    | text     |
.. +-------------+------------+-----------+----------+

<delete>
~~~~~~~~~~~~
Delete the scenario component with the given name.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

.. | dir         | no         | (none)    | text     |
.. +-------------+------------+-----------+----------+

<function>
~~~~~~~~~~~~
Call the internal function (i.e., "method") of the class
:doc:`pygcam.xmlEditor` (or, a subclass thereof) with the given
name, passing
to it the arguments provided in the text of the ``<function>``
element. The arguments should be a comma-delimited set of
values that are valid Python constants. Note that some
function calls use keyword arguments, which must be specified
with the keyword. Note that function arguments can refer to
iterator variables. (See example :ref:`below <setup-example>`.)

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

**Subclassing XMLEditor to provide functions callable from XML**

By default, the ``<function>`` element allows you to invoke
functions defined in the :doc:`pygcam.xmlEditor` class. If set,
the class identified by the configuration variable
``GCAM.ScenarioSetupClass`` must indicate a subclass of ``XMLEditor``
to use instead. The format of the value for this variable is:

``/path/to/module/dir;module.SubclassName``

That is, there are two parts separated by a semi-colon. The first
part is a path to a directory holding a module in which the subclass
is defined. The second part is a standard Python specification of
one or more modules separated by periods, with the final element being
the name of the subclass.

Note: Only functions (class methods) defined with the
``@callableMethod`` decorator are recognized as callable from XML.
See ``pygcam.xmlEditor.py`` for examples.

<if>
~~~~~~
The ``<if>`` node allows one or more of the five action elements
to be included if the two values provided match (are the same;
the default) or do not match, indicated by specifying ``matches="0"``
or ``matches="false"``. This element may contain zero or more
``<comment>`` elements.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| value1      | yes        | (none)    | text     |
+-------------+------------+-----------+----------+
| value2      | yes        | (none)    | text     |
+-------------+------------+-----------+----------+
| matches     | no         | "true"    | boolean  |
+-------------+------------+-----------+----------+

When `matches` is "1" or "true" (the default) the enclosed actions
are taken if and only if the values of attributes `value1` and
`value2` are the same. When `matches` is "0" or "false", the actions
are taken if and only if the two values differ.

.. _setup-example:

Example
^^^^^^^^
This is an example of a scenarios.xml file.

.. literalinclude:: ../../pygcam/etc/scenarios-example.xml
   :language: xml
