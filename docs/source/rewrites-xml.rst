rewriteSets.xml
=================
The ``rewriteSets.xml`` file defines named sets of rewrite statements that
can be added to queries defined in a separate :doc:`query-xml` file, or in
a ``<queries>`` element within a :doc:`project-xml` file.

XML elements
------------

The elements that comprise the ``rewriteSets.xml`` file are described below.

.. seealso::
   Some elements of the ``rewriteSets.xml`` file can contain ``<CONDITIONAL>``
   elements, as described below. See :doc:`conditional-xml` for further details.

<rewriteSets>
^^^^^^^^^^^^^
This is the outermost element, which takes no attributes and contains one
or more ``<rewriteSet>`` elements. It may also contain ``<CONDITIONAL>``
elements.

<rewriteSet>
^^^^^^^^^^^^^
This element defines a set of rewrites, assigns the set a unique name, and
specifies the default 'level' to use if not overridden in the ``queries.xml``
file when the rewrite set is referenced. If the ``append-values`` flag is
"true", rows are written out for all elements including those with zero results.
When the rewrite sets are inserted into a query file, ``level`` is set to "true"
if any of the rewrite sets specified ``append-values="true"``, otherwise the
value is set to "false".

If ``byAEZ="true"``, each rewrite is expanded to 18 elements with the same
'to' attribute, but with the 'from' attributes formed by appending 'AEZ'
and zero-padded, 2-digit integers from 1 to 18. In the example below, the
element

    .. code-block:: xml

       <rewriteSet name="landCover" level="LandLeaf" byAEZ="true">
           <rewrite from="biomass" to="Biomass"/>
           ...
       </rewriteSet>

is expanded in the generated query file to:

    .. code-block:: xml

       <rewrite from="biomassAEZ01" to="Biomass"/>
       <rewrite from="biomassAEZ02" to="Biomass"/>
       <rewrite from="biomassAEZ03" to="Biomass"/>
       <rewrite from="biomassAEZ04" to="Biomass"/>
       <rewrite from="biomassAEZ05" to="Biomass"/>
       <rewrite from="biomassAEZ06" to="Biomass"/>
       <rewrite from="biomassAEZ07" to="Biomass"/>
       <rewrite from="biomassAEZ08" to="Biomass"/>
       <rewrite from="biomassAEZ09" to="Biomass"/>
       <rewrite from="biomassAEZ10" to="Biomass"/>
       <rewrite from="biomassAEZ11" to="Biomass"/>
       <rewrite from="biomassAEZ12" to="Biomass"/>
       <rewrite from="biomassAEZ13" to="Biomass"/>
       <rewrite from="biomassAEZ14" to="Biomass"/>
       <rewrite from="biomassAEZ15" to="Biomass"/>
       <rewrite from="biomassAEZ16" to="Biomass"/>
       <rewrite from="biomassAEZ17" to="Biomass"/>
       <rewrite from="biomassAEZ18" to="Biomass"/>

The ``<rewriteSet>`` element may contain ``<CONDITIONAL>`` elements.

<rewrite>
^^^^^^^^^^^^^
The ``<rewrite>`` element defines a label rewrite. If the element
specifies ``byAEZ="true"``, the element is expanded as described
above. If all elements in a rewriteSet are to be expanded by AEZ,
it is more convenient to specify this once in the ``<rewriteSet>``
element.

The resulting ``<rewrite>`` statements are inserted into the query
file and processed as usual by the GCAM batch query processor:

   * If the "to" value is empty, any row with a matching value is
     dropped from the result set.

   * If the "to" value specified a new name, the label is rewritten
     using the new name and grouped with other values having that
     name. This is used to aggregate values, e.g., from 32 regions
     to a smaller number. In the example below, the ``resultSet``
     named ``eightRegions`` maps the 32 standard GCAM regions into
     8 regions.

   * If a value is not specified, or if the "from" and "to" values
     are the same, the row is processed normally.

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| from        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+
| to          | yes        | (none)    | text     |
+-------------+------------+-----------+----------+
| byAEZ       | no         | (none)    | text     |
+-------------+------------+-----------+----------+


Example
^^^^^^^^
This is an example of a file defining rewrite sets.

  .. code-block:: xml

     <rewriteSets>
        <rewriteSet name="eightRegions" level="region" append-values="true">
            <rewrite from="USA" to="United States"/>
            <rewrite from="Brazil" to="Brazil"/>
            <rewrite from="Canada" to="Rest of World"/>
            <rewrite from="China" to="China"/>
            <rewrite from="Africa_Eastern" to="Africa"/>
            <rewrite from="Africa_Northern" to="Africa"/>
            <rewrite from="Africa_Southern" to="Africa"/>
            <rewrite from="Africa_Western" to="Africa"/>
            <rewrite from="Japan" to="Rest of Asia"/>
            <rewrite from="South Korea" to="Rest of Asia"/>
            <rewrite from="India" to="Rest of Asia"/>
            <rewrite from="Central America and Caribbean" to="Rest of South America"/>
            <rewrite from="Central Asia" to="Rest of Asia"/>
            <rewrite from="EU-12" to="Europe Union 27"/>
            <rewrite from="EU-15" to="Europe Union 27"/>
            <rewrite from="Europe_Eastern" to="Rest of World"/>
            <rewrite from="Europe_Non_EU" to="Rest of World"/>
            <rewrite from="European Free Trade Association" to="Rest of World"/>
            <rewrite from="Indonesia" to="Rest of Asia"/>
            <rewrite from="Mexico" to="Rest of South America"/>
            <rewrite from="Middle East" to="Rest of World"/>
            <rewrite from="Pakistan" to="Rest of Asia"/>
            <rewrite from="Russia" to="Rest of World"/>
            <rewrite from="South Africa" to="Africa"/>
            <rewrite from="South America_Northern" to="Rest of South America"/>
            <rewrite from="South America_Southern" to="Rest of South America"/>
            <rewrite from="South Asia" to="Rest of Asia"/>
            <rewrite from="Southeast Asia" to="Rest of Asia"/>
            <rewrite from="Taiwan" to="Rest of Asia"/>
            <rewrite from="Argentina" to="Rest of South America"/>
            <rewrite from="Colombia" to="Rest of South America"/>
            <rewrite from="Australia_NZ" to="Rest of Asia"/>
        </rewriteSet>

        <rewriteSet name="food" level="input">
            <rewrite from="Corn" to="Grains"/>
            <rewrite from="FiberCrop" to="Other"/>
            <rewrite from="MiscCrop" to="Other"/>
            <rewrite from="OilCrop" to="Other"/>
            <rewrite from="OtherGrain" to="Grains"/>
            <rewrite from="PalmFruit" to="Other"/>
            <rewrite from="Rice" to="Grains"/>
            <rewrite from="Root_Tuber" to="Other"/>
            <rewrite from="SugarCrop" to="Other"/>
            <rewrite from="Wheat" to="Grains"/>
            <rewrite from="regional beef" to="Meat"/>
            <rewrite from="Dairy" to="Meat"/>
            <rewrite from="OtherMeat_Fish" to="Meat"/>
            <rewrite from="Pork" to="Meat"/>
            <rewrite from="Poultry" to="Meat"/>
            <rewrite from="SheepGoat" to="Meat"/>
        </rewriteSet>

        <!--
        This rewriteSet specifies byAEZ="true", which causes each rewrite to be
        expanded to 18 elements with the same 'to' attribute, but with the 'from'
        attributes formed by appending 'AEZ' and zero-padded, 2-digit integers
        from 1 to 18, i.e., biomassAEZ01, biomassAEZ02, ..., biomassAEZ18.
        -->
        <rewriteSet name="landCover" level="LandLeaf" byAEZ="true">
            <rewrite from="biomass" to="Biomass"/>
            <rewrite from="Corn" to="Cropland"/>
            <rewrite from="eucalyptus" to="Cropland"/>
            <rewrite from="FiberCrop" to="Cropland"/>
            <rewrite from="FodderGrass" to="Cropland"/>
            <rewrite from="FodderHerb" to="Cropland"/>
            <rewrite from="Forest" to="Forest (managed)"/>
            <rewrite from="Grassland" to="Grass"/>
            <rewrite from="Jatropha" to="Cropland"/>
            <rewrite from="MiscCrop" to="Cropland"/>
            <rewrite from="OilCrop" to="Cropland"/>
            <rewrite from="OtherArableLand" to="Cropland"/>
            <rewrite from="OtherGrain" to="Cropland"/>
            <rewrite from="PalmFruit" to="Cropland"/>
            <rewrite from="Pasture" to="Pasture (grazed)"/>
            <rewrite from="ProtectedGrassland" to="Other arable land"/>
            <rewrite from="ProtectedShrubland" to="Other arable land"/>
            <rewrite from="ProtectedUnmanagedForest" to="Forest (unmanaged)"/>
            <rewrite from="ProtectedUnmanagedPasture" to="Pasture (other)"/>
            <rewrite from="Rice" to="Cropland"/>
            <rewrite from="RockIceDesert" to="Other land"/>
            <rewrite from="Root_Tuber" to="Cropland"/>
            <rewrite from="Shrubland" to="Other arable land"/>
            <rewrite from="SugarCrop" to="Cropland"/>
            <rewrite from="Tundra" to="Other land"/>
            <rewrite from="UnmanagedForest" to="Forest (unmanaged)"/>
            <rewrite from="UnmanagedPasture" to="Pasture (other)"/>
            <rewrite from="UrbanLand" to="Other land"/>
            <rewrite from="Wheat" to="Cropland"/>
            <rewrite from="willow" to="Cropland"/>
            <rewrite from="SugarcaneEthanol" to="Cropland"/>
        </rewriteSet>
     </rewriteSets>
