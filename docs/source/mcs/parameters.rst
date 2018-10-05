Defining parameters and distributions
=======================================

.. _parameters-xml:

The file ``parameters.xml`` defines the parameters modified in a Monte Carlo
Simulation (MCS) with GCAM.

Note that there is no native concept of a “parameter” in GCAM. The XML files
read by GCAM define thousands of numerical values describing emissions,
conversion efficiencies, elasticities, share-weights, logit exponents, and more,
with values that can differ by region, sector, subsector, year, and AEZ.

In ``pygcam.mcs``, a parameter is defined as a query on an XML file (using the
"XPath" query language) that produces a set of numerical values. This is
general enough to allow the analyst to be as specific or broad as desired in
deciding which values to perturb as a set.

For example, the following XML fragment defines the parameter ``n2o-emissions``
as all ``input-emissions`` elements below ``Non-CO2`` elements named ``N2O_AGR``
(i.e., agricultural N2O emission) and ``AgProductionTechnology`` elements,
for the year "2005" only. The query is applied to the XML file identified in the
configuration file with "name" ``nonco2_aglu``.

.. code-block:: XML

  <!-- N2O emissions intensity -->
  <InputFile name="nonco2_aglu">
    <Parameter name="n2o-emissions">
      <Query>//AgProductionTechnology/period[@year="2005"]/Non-CO2[@name="N2O_AGR"]/input-emissions</Query>
      <Distribution apply="multiply">
        <LogUniform factor="2"/>  <!-- i.e., from half to double -->
      </Distribution>
    </Parameter>
  </InputFile>

The sub-command :ref:`gensim <gensim>` ignores the query, and simply draws
values from the designated distributions for all defined parameters, and saves these
to a CSV file. Using a CSV file as an intermediate representation allows any plugin
(or manual process) to generate the data used to generate the actual input XML files.
(The default method is Latin Hypercube Sampling from the indicated distributions, but
other sample methods are provided via the gensim's ``-m`` / ``--method`` argument.)

XML elements
------------

The elements that comprise the ``parameters.xml`` file are described below.

<ParameterList>
^^^^^^^^^^^^^^^^^^^^

The top-most element, ``<ParameterList>``, encloses one or more ``<InputFile>``
(or ``<comment>``) elements. The ``<ParameterList>`` element accepts no
attributes.

<InputFile>
^^^^^^^^^^^^^

The ``<InputFile>`` element describes a file on which XPath queries
will be run for each ``<Parameter>``, to produce sets of values that
are perturbed for each trial. The ``<InputFile>`` element accepts the
following attribute:

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+


The `name` is must identify an input file in the GCAM configuration XML
file, given in a ``<Value>`` element within the ``<ScenarioComponents>``
element. For example, in this fragment of ``configuration_ref.xml``:

  .. code-block:: xml

     <ScenarioComponents>
        ...
        <Value name="solver">../input/solution/cal_broyden_config.xml</Value>
        ...
     </ScenarioComponents>

the input file would be indicated using the name ``"solver"``. Note that
this requires each file in ``<ScenarioCompenents>`` to have a unique name,
as is the case starting in GCAM v4.3.

An ``<InputFile>`` element must contain at least one ``<Parameter>`` element,
and can contain any number of ``<comment>`` or ``<WriteFunc>`` elements.


<Parameter>
^^^^^^^^^^^^^

The ``<Parameter>`` element specifies the XPath query to run and
the distribution to apply to the results of the query. It must contain
exactly one ``<Distribution>`` element, zero or one ``<Query>`` elements,
and any number of  ``<Correlation>`` elements.

The ``<Parameter>`` element accepts the following attributes:

+-------------+------------+-----------+-------------+
| Attribute   | Required   | Default   | Values      |
+=============+============+===========+=============+
| name        | yes        | (none)    | text        |
+-------------+------------+-----------+-------------+
| mode        | no         | shared    | *see below* |
+-------------+------------+-----------+-------------+
| active      | no         | "1"       | boolean     |
+-------------+------------+-----------+-------------+

Accepted values for ``mode`` are "shared", "independent", and "ind".
The final two values are synonymous. The default, "shared",
indicates that a single random variable (RV) should be created and
used for all the elements retrieved by the XPath query. The value
"ind" or "independent" indicates that an RV should be created for
each value returned. Note that it is common for queries to return
hundreds or even tens of thousands of values, so specifying these
as independent can create a lot of overhead. In most cases, "shared"
is more appropriate.


The `active` attribute can be set to "0" or "false" to disable
a ``<Parameter>``, causing it to be ignored in the MCS.

<WriteFunc>
^^^^^^^^^^^^^

The ``<WriteFunc>`` element defines a Python function to be called
before an XML file is written. This provides a hook to make arbitrary
modifications to the XML that cannot be handled in a more straighforward
manner. The element takes no attributes and must contain a period-delimited
value that interpreted to be a sequence of Python package/module names and
a final function name.

For example, to call the function ``my_func`` in the ``MyModule`` module
of package ``MyPkg``, you would write:

.. code-block:: xml

    <WriteFunc>MyPkg.MyModule.my_func</WriteFunc>


<Distribution>
^^^^^^^^^^^^^^^^^
The ``<Distribution>`` element defines the shape of the distribution
from which values should be randomly drawn. This element accepts an
``apply`` attribute that defines how the randomly drawn value will
be applied to the values returned by the XPath query.

+-------------+------------+-----------+-------------+
| Attribute   | Required   | Default   | Values      |
+=============+============+===========+=============+
| apply       | no         | direct    | *see below* |
+-------------+------------+-----------+-------------+

The following values are recognized:

* ``dir``, ``direct``, or ``replace`` : the random value
  replaces the values returned by the XPath query.

* ``add`` : the randomly drawn value is added to the values
  returned by the XPath query.

* ``mult`` or ``multiply`` : the randomly drawn value is multiplied
  by the values returned by the XPath query.

* a period-delimited string indicating a package/module and function
  which is called to generate the result. # TBD: review this.


<Correlation>
^^^^^^^^^^^^^^^^^
This element allows the user to require that values of drawn from
the current parameter's distribution have a given rank correlation
(with values in [-1, 1]) with values drawn for one or more other
parameters. The rank correlation is produced by drawing all the
random values and then reordering them so that the requested rank
correlation obtains.

<With>
^^^^^^^^^^^^^^^^^
Names one parameter with which the enclosing parameter is correlated,
and provides the correlation level. The "text" value of the ``<With>``
element must be a floating point number in the range [-1, 1].

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+


<Linked>
^^^^^^^^^^^^^^^^^
The ``<Linked>`` element allows the vector of random values drawn
for one parameter to be shared with another parameter.
This can be useful, for example, when you have two in two XML
files that are conceptually a single "parameter". This differs from
the ``<Correlation>`` element, which ensures only a given level of
rank correlation between parameters.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| parameter   | yes        | (none)    | text     |
+-------------+------------+-----------+----------+


<Constant>
^^^^^^^^^^^^^^^^^
This pseudo-distribution produces the designated value on every draw.
It can be used to force a set of XML elements to a given value.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| value       | yes        | (none)    | float    |
+-------------+------------+-----------+----------+


<Sequence>
^^^^^^^^^^^^^^^^^
This pseudo-distribution produces each value from a discrete
set of comma-separated values, in order. If the number of trials
exceeds the number of values, the list is recycled as many times
as needed. This distribution can be used to generate trials with
a series of specific values.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| values      | yes        | (none)    | text*    |
+-------------+------------+-----------+----------+

The ``values`` attribute takes a text argument that must contain
comma-delimited integer or floating point values. (Integers are
converted to float, however.) Spaces around commas are removed,
so they can be added for readability.

<Binary>
^^^^^^^^^^^^^^^^^

Produces a discrete distribution with a 50% chance of
returning 0 or 1. This element accepts no attributes.


<Integers>
^^^^^^^^^^^^^^^^^
This produces a discrete distribution with all integer
values in the range [min, max] having equal probability
of being drawn.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| min         | no         | (none)    | float    |
+-------------+------------+-----------+----------+
| max         | no         | (none)    | float    |
+-------------+------------+-----------+----------+


<Grid>
^^^^^^^^^^^^^^^^^
Produces a distribution of `count` values equally spaced
across the range [min, max] (inclusive).

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| min         | no         | (none)    | float    |
+-------------+------------+-----------+----------+
| max         | no         | (none)    | float    |
+-------------+------------+-----------+----------+
| count       | no         | (none)    | float    |
+-------------+------------+-----------+----------+


<Uniform>
^^^^^^^^^^^^^^^^^
Produces a uniform distribution of values from a given range. The
range can be specified one of three ways:

#. Explicit minimum and maximum values, e.g.

  .. code-block:: xml

     <Uniform min=0.25 max=0.5>

#. A symmetrical spread around zero, equivalent to Uniform(-`range`, +`range`),
   which is used mainly when adding a random value to the original data:

   .. code-block:: xml

      <Uniform range=0.25>

   which is equivalent to

   .. code-block:: xml

     <Uniform min=-0.25 max=0.25>

#. A symmetrical range around 1, defined as Uniform(1 - `factor`, 1 + `factor`),
   which is used mainly when multiplying a random value by the original data:

   .. code-block:: xml

      <Uniform factor=0.25>

   which is equivalent to

   .. code-block:: xml

      <Uniform min=0.75 max=1.25>


The valid attributes are any of the following sets:

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| min         | yes        | (none)    | float    |
+-------------+------------+-----------+----------+
| max         | yes        | (none)    | float    |
+-------------+------------+-----------+----------+

or

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| factor      | yes        | (none)    | float    |
+-------------+------------+-----------+----------+

or

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| range       | yes        | (none)    | float    |
+-------------+------------+-----------+----------+



<LogUniform>
^^^^^^^^^^^^^^^^^
The ``<LogUniform>`` element defines a uniform distribution
from 1/`factor` to `factor`. For example, the following two
distribution specifications are equivalent:

.. code-block:: XML

   <LogUniform factor=3>

   <Uniform min=0.333 max=3>


+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| factor      | yes        | (none)    | float    |
+-------------+------------+-----------+----------+


<Triangle>
^^^^^^^^^^^^^^^^^
Defines a triangular distribution. There are three alternatives
for declaring the distribution:

#. Explicit minimum, mode, and maximum values, e.g.

  .. code-block:: xml

     <Triangle min=0.25 mode=0.40 max=0.75>

#. A symmetrical spread around zero, equivalent to
   Triangle(-`range`, 0, +`range`), which is used mainly when
   adding a random value to the original data:

   .. code-block:: xml

      <Triangle range=0.25>

   which is equivalent to

   .. code-block:: xml

     <Triangle min=-0.25 mode=0 max=0.25>

#. A symmetrical range around 1, defined as
   Triangle(1 - `factor`, 1, 1 + `factor`), which is used mainly when
   multiplying a random value by the original data:

   .. code-block:: xml

      <Triangle factor=0.25>

   which is equivalent to

   .. code-block:: xml

      <Triangle min=0.75 mode=1.0 max=1.25>

The valid attributes are any of the following sets:

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| min         | yes        | (none)    | float    |
+-------------+------------+-----------+----------+
| max         | yes        | (none)    | float    |
+-------------+------------+-----------+----------+
| mode        | yes        | (none)    | float    |
+-------------+------------+-----------+----------+

or

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| range       | yes        | (none)    | float    |
+-------------+------------+-----------+----------+

or

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| factor      | yes        | (none)    | float    |
+-------------+------------+-----------+----------+



<Normal>
^^^^^^^^^^^^^^^^^

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| mean        | yes        | (none)    | float    |
+-------------+------------+-----------+----------+
| stdev       | yes        | (none)    | float    |
+-------------+------------+-----------+----------+


<Lognormal>
^^^^^^^^^^^^^^^^^
This element defines a lognormal distribution one of two ways:

#. By providing the mean and standard deviation of the lognormal
   distributio, e.g.

  .. code-block:: xml

     <Lognormal mean=0.5 stdev=0.2>

#. By providing the 2.75% and 97.5% values (bounds of the central
   95% of the distribution), e.g.,

   .. code-block:: xml

     <Lognormal low95=0.1 high95=0.6>

The valid attributes are either of the following sets:

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| mean        | yes        | (none)    | float    |
+-------------+------------+-----------+----------+
| stdev       | yes        | (none)    | float    |
+-------------+------------+-----------+----------+

or

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| low95       | yes        | (none)    | float    |
+-------------+------------+-----------+----------+
| high95      | yes        | (none)    | float    |
+-------------+------------+-----------+----------+

<DataFile>
^^^^^^^^^^^^^
Describes a file containing data to be used in place of
a distribution.

<PythonFunc>
^^^^^^^^^^^^^
The ``<PythonFunc>`` element defines a Python function to be called
to produce an array of values used in place of a distribution. The
element takes no attributes and must contain a period-delimited
value that interpreted to be a sequence of Python package/module names
and a final function name.

For example, to call the function ``my_func`` in the ``MyModule`` module
of package ``MyPkg``, you would write:

.. code-block:: xml

    <WriteFunc>MyPkg.MyModule.my_func</WriteFunc>


Example
^^^^^^^^
Following is an example of a ``parameters.xml`` file.

.. literalinclude:: ../../../pygcam/mcs/etc/parameters-example.xml
   :language: xml
