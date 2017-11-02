Conditional XML
=================
Several of the ``pygcam`` XML files allow sections of the XML to be conditional
on the values of configuration variables. I call this "Conditional XML". It is
implemented by reading an XML file, processing it to find ``<CONDITIONAL>``
elements, and processing these to determine what portion of the conditional XML
to include in the output stream read by ``pygcam``.

This feature allows you to choose among different modes of running your
project based on the value of a configuration variable.  For example,
you might use different options in your project or scenario XML files depending
on whether you are running individual GCAM scenarios or a Monte Carlo Simulation.

The individual file types supporting Conditional XML describe the elements that
can be made conditional. This file serves to consolidate the documentation of
the Conditional XML syntax.

XML elements
------------

The outermost element of a conditional section is ``<CONDITIONAL>``, which
takes no attributes. It must contain:

* Exactly one of ``<TEST>``, ``<AND>``, or ``<OR>``.

* Exactly one ``<THEN>`` element, which contains XML to insert if the test
  evaluates to True

* An optional ``<ELSE>`` element, which can contain XML to insert if the
  test evaluates to False.

Example
^^^^^^^^
In this brief example, the project file variable ``mcsFlag`` is set
to either ``--mcs`` or the empty string, depending on the value of
the configuration variable ``RunMCS``.

.. code-block:: xml

   <project name="paper1">
      <vars>
         <CONDITIONAL>
            <TEST var="RunMCS" value="1" type="bool"/>
            <THEN>
               <var name="mcsFlag">--mcs</var>
            </THEN>
            <ELSE>
               <var name="mcsFlag"></var>
            </ELSE>
         </CONDITIONAL>
       </vars>
   ...
   </project>

<TEST>
^^^^^^^^^^^^^
This element provides the basic comparison functionality.
Each ``<TEST>`` must specify a variable and a value. If not given, the
comparison operator (``op``) is assumed to be equality. Available operators
are listed below.

If not ``type`` is specified, variables are coerced to strings before
comparison. If a ``type`` of ``str``, ``int``, ``float``, or ``bool`` is
indicated, values are coerced to that type before comparison.

+-------------+------------+-----------+-------------------------------+
| Attribute   | Required   | Default   | Values                        |
+=============+============+===========+===============================+
| var         | yes        | (none)    | text                          |
+-------------+------------+-----------+-------------------------------+
| value       | yes        | (none)    | text                          |
+-------------+------------+-----------+-------------------------------+
| op          | no         | '=='      | (see below)                   |
+-------------+------------+-----------+-------------------------------+
| type        | no         | 'str'     | 'str', 'int', 'float', 'bool' |
+-------------+------------+-----------+-------------------------------+

The comparison operators all compare the value of configuration variable
``var`` (A) to the given ``value`` (B). Note that all environment variables
are loaded into the configuration dictionary and are accessible by name,
prefixed by ``$`` as in a UNIX shell.

Note that in XML you should specify ``<`` and ``>`` as ``&lt;`` and ``%gt;``,
which can be a nuisance, thus FORTRAN text style operators are also provided.

* ``=``, ``==``, or ``eq``: A equals B

* ``!=`` or ``ne``: A does not equal B

* ``<`` or ``lt``: A is less than B

* ``<=`` or ``le``: A is less than or equal to B

* ``>`` or ``gt``: A is greater than B

* ``>=`` or ``ge``: A is greater than or equal to B

Example
~~~~~~~~

.. code-block:: xml

   <TEST var="RunMCS" value="1" type="bool"/>


<AND>
^^^^^^
The ``<AND>`` element takes no attributes. It can contain any number of
``<TEST>``, ``<AND>``, or ``<OR>`` elements. It evaluates to True if
all of its direct children elements evaluate to True. The evaluation of
elements stops as soon as one evaluates to False.

Example
~~~~~~~~
The following example requires both that variable ``RunMCS`` has
a "True" value, and that ``OtherVar`` equals "foo".

.. code-block:: xml

   <AND>
     <TEST var="RunMCS" value="1" type="bool"/>
     <TEST var="OtherVar" value="foo"/>
   </AND>

<OR>
^^^^^^
The ``<OR>`` element takes no attributes. It can contain any number of
``<TEST>``, ``<AND>``, or ``<OR>`` elements. It evaluates to True if
any of its direct children elements evaluate to True. The evaluation of
elements stops as soon as one evaluates to True.

Example
~~~~~~~~
The following example requires that variable ``RunMCS`` has
a "True" value, or, that ``OtherVar`` equals "foo" (or both).

.. code-block:: xml

   <OR>
     <TEST var="RunMCS" value="1" type="bool"/>
     <TEST var="OtherVar" value="foo"/>
   </OR>
