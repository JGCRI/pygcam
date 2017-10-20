.. _protect-xml:


landProtection.xml
=======================

The :ref:`protect <protect>` sub-command of :doc:`gcamtool` generates XML
input files for GCAM that "protect" land by removing it from consideration
by the model as a productive land area. It reads a single XML input file that
defines one or protection scenarios, which can specify the fraction the original land
area in any combination of `{Shrubland, Grassland, UnmanagedPasture, UnmanagedForest}`,
by region or groups of regions.

Command-line usage is documented on the :ref:`gt protect <protect>` page.
The ``landProtection.xml`` file elements are described below.

XML elements
------------

The elements that comprise the project.xml file are described below.

<landProtection>
^^^^^^^^^^^^^^^^

The top-most element, ``<landProtection>``, encloses one or more ``<group>``
or ``<scenario>`` elements.

<group>
^^^^^^^^^

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

The ``<group>`` element assigns a name to a set of regions (each defined in a
``<region>`` element or other groups so
they can be referred to in land protection scenarios.

For example, we can define
a group called ``Europe`` consisting of all the GCAM European regions as follows:

  .. code-block:: xml

   <group name="Europe">
      <region>EU-12</region>
      <region>EU-15</region>
      <region>Europe_Eastern</region>
      <region>Europe_Non_EU</region>
      <region>European Free Trade Association</region>
   </group>

We can also define other groups that refer to existing groups:

  .. code-block:: xml

   <group name="MyGroup">
      <region>Europe</region>
      <region>USA</region>
      <region>China<region>
   </group>

For convenience, the group ``Global`` is defined by the script; it contains
all 32 GCAM regions.

<scenario>
^^^^^^^^^^

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

A ``<scenario>`` element assigns a name to a set of
``<protectedRegion>`` elements.


<protectedRegion>
^^^^^^^^^^^^^^^^^^^

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

A ``<protectedRegion>`` element contains one or more
``<protection>`` nodes, and assigns these to the region
given by the ``name`` attribute.

Regions are processed in the order defined. Any redefinition of a
protection in a region overwrites what was given previously. This
allows the use of groups followed by differentiation for individual
regions within the group. (See the example XML file, below.)

<protection>
^^^^^^^^^^^^^^^^^^^

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| fraction    | yes        | (none)    | float    |
+-------------+------------+-----------+----------+

A ``<protection>`` element defines the percentage of land
of one or more land classes (defined in ``<landClass>`` elements)
to protect in the region named by the enclosing ``<protectedRegions>`` element.


Example landProtection.xml file
--------------------------------

This file defines several groups of regions and uses these in a
scenario named ``scen1``. See the in-line comments for more details.

  .. code-block:: xml

    <landProtection>
       <!--
       Define a set of groups that we will use in our protection
       scenario definitions.
       -->
       <group name="Developing">
           <region>Africa_Eastern</region>
           <region>Africa_Northern</region>
           <region>Africa_Southern</region>
           <region>Africa_Western</region>
           <region>Central America and Caribbean</region>
           <region>Central Asia</region>
           <region>Colombia</region>
           <region>Middle East</region>
           <region>Pakistan</region>
           <region>South America_Northern</region>
           <region>South America_Southern</region>
           <region>South Asia</region>
           <region>Southeast Asia</region>
       </group>

       <group name="MiddleIncome">
           <region>Brazil</region>
           <region>China</region>
           <region>India</region>
           <region>Indonesia</region>
           <region>Mexico</region>
           <region>South Africa</region>
       </group>

       <!--
       The group "Europe" is not used directly as a protectedRegion, but
       as an element in the definition of group "Developed", below.
       -->
       <group name="Europe">
           <region>EU-12</region>
           <region>EU-15</region>
           <region>Europe_Eastern</region>
           <region>Europe_Non_EU</region>
           <region>European Free Trade Association</region>
       </group>

       <group name="Developed">
           <region>Argentina</region>
           <region>Australia_NZ</region>
           <region>Canada</region>
           <!--
           Group names (e.g., Europe) are expanded to the underlying
           regions
           -->
           <region>Europe</region>
           <region>Japan</region>
           <region>Russia</region>
           <region>South Korea</region>
           <region>Taiwan</region>
           <region>USA</region>
       </group>

       <!-- Define a scenario that uses the groups defined above -->
       <scenario name="scen1">

           <!--
           For developing regions, we will protect half of unmanaged forest and
           pasture and 25% of shrubland and grassland.
           -->
           <protectedRegion name="Developing">
               <protection fraction="0.5">
                   <landClass>UnmanagedForest</landClass>
                   <landClass>UnmanagedPasture</landClass>
               </protection>
               <protection fraction="0.25">
                   <landClass>Shrubland</landClass>
                   <landClass>Grassland</landClass>
               </protection>
           </protectedRegion>

           <!-- similarly for middle income regions, with different fractions -->
           <protectedRegion name="MiddleIncome">
               <protection fraction="0.7">
                   <landClass>UnmanagedForest</landClass>
                   <landClass>UnmanagedPasture</landClass>
               </protection>
               <protection fraction="0.4">
                   <landClass>Shrubland</landClass>
                   <landClass>Grassland</landClass>
               </protection>
           </protectedRegion>

           <!-- This overrides Brazil's definition in MiddleIncome -->
           <protectedRegion name="Brazil">
               <protection fraction="0.5">
                   <landClass>UnmanagedForest</landClass>
               </protection>
               <protection fraction="0.4">
                   <landClass>UnmanagedPasture</landClass>
                   <landClass>Shrubland</landClass>
                   <landClass>Grassland</landClass>
               </protection>
           </protectedRegion>

           <!-- Protect more land in developed regions -->
           <protectedRegion name="Developed">
               <protection fraction="0.9">
                   <landClass>UnmanagedForest</landClass>
                   <landClass>UnmanagedPasture</landClass>
               </protection>
               <protection fraction="0.5">
                   <landClass>Shrubland</landClass>
                   <landClass>Grassland</landClass>
               </protection>
           </protectedRegion>
       </scenario>
    </landProtection>
