.. _project-xml:


project.xml
===============

The ``run`` sub-command of :doc:`gcamtool` provides workflow management
for GCAM. It reads a single XML input file that defines one or more projects,
one or more groups of scenarios, one or more scenarios, and one or more workflow
steps. The workflow steps for the chosen project and scenario(s) are run
in the order defined. The script was developed for use with other :doc:`gcamtool`
sub-commands, however any scripts or programs can be called in workflow
'steps'.

Command-line usage is describe on the :ref:`gt run<run>` page.
The ``project.xml`` file elements are described below. The :ref:`new <new>`
sub-command copies a generic ``project.xml`` file into the newly created
project directory, which should be modified to suit your needs.

Note that the :ref:`run <run>` sub-command provides several options that
list elements of the ``project.xml`` file. Use the ``-l``, ``-L``, and ``-g`` to
list steps, scenarios, and groups, respectively.

XML elements
------------

The elements that comprise the project.xml file are described below.

.. seealso::
   Some elements of the ``project.xml`` file can contain ``<CONDITIONAL>``
   elements, as described below. See :doc:`conditional-xml` for further details.

<projects>
^^^^^^^^^^

The top-most element, ``<projects>``, encloses one or more ``<project>``
elements and zero or more ``<defaults>`` elements. The ``<projects>``
element takes no attributes.

<project>
^^^^^^^^^

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| name        | yes        | (none)    | text     |
+-------------+------------+-----------+----------+

A ``<project>`` requires a 'name' attribute, and defines a set of
variables, scenario groups, scenarios, and workflow steps, as described
below. The ``<project>`` element may contain ``<CONDITIONAL>`` elements.

<defaults>
^^^^^^^^^^

The optional ``<defaults>`` element sets default values for variables and
workflow steps. This allows definitions to be shared across projects,
reducing redundancy. Individual projects can override and/or declare new
variables steps as needed. The ``<defaults>`` element takes no
attributes.

.. note::
  The use of ``<scenarioGroup>`` in the ``project.xml`` is deprecated. The
  scenarios must now be defined in a separate ``scenarios.xml`` file, and
  referenced in the ``project.xml`` file using the ``<scenariosFile>`` element.

<scenariosFile>
^^^^^^^^^^^^^^^^^
The element ``<scenariosFile>`` identifies the file containing scenario
descriptions. See :doc:`scenarios-xml` for a description of that file.

+-------------+------------+-----------+---------------------------------+
| Attribute   | Required   | Default   | Values                          |
+=============+============+===========+=================================+
| name        | yes        | (none)    | the path to the scenarios.xml   |
+-------------+------------+-----------+---------------------------------+

If the pathname given by the `name` attribute is not an absolute path,
it is interpreted relative to the directory holding the ``project.xml``.

<steps>
^^^^^^^

The element ``<steps>`` contains a one or more ``<step>`` elements, and
takes no attributes. Multiple ``<steps>`` elements are allowed.
The ``<steps>`` element may contain ``<CONDITIONAL>`` elements.

<step>
^^^^^^

+-------------+------------+-----------+---------------------------------+
| Attribute   | Required   | Default   | Values                          |
+=============+============+===========+=================================+
| name        | yes        | (none)    | text                            |
+-------------+------------+-----------+---------------------------------+
| seq         | yes        |(see text) | integer                         |
+-------------+------------+-----------+---------------------------------+
| runFor      | no         | "all"     | {"baseline", "policy", "all"}   |
+-------------+------------+-----------+---------------------------------+
| group       | no         | ""        | the name of a scenario group    |
+-------------+------------+-----------+---------------------------------+
| optional    | no         | "false"   | {"true", "false"}               |
+-------------+------------+-----------+---------------------------------+

A ``<step>`` describes one step in the workflow. Each step has a name
and an integer sequence number. Sequence numbers can be specified using
the ``seq`` attribute, otherwise the steps are numbered in the order they
occur in the file, starting with 1. Each step is assigned 1 more than the
maximum step number already used: this includes automatically generated
sequence numbers and any that are specified explicitly.

In general, using the generated sequence numbers will suffice. Assigning
your own sequence numbers allows you to group or order commands in any manner
while ensuring that the commands are executed in the correct order. The
other reason to assign sequence numbers is to be able to define optional
steps in a ``<defaults>`` section that can be overridden in a ``<project>``
section, as described :ref:`below <sequence-override-label>`.

Steps (from one or more ``<steps>`` sections) are sorted by sequence number
before execution. By definition, steps with the same sequence number are
order independent; they can run in any order.

The text value of a step can be any command you want to run. Many of the
common workflow steps are built into ``gt`` and these can be
invoked by using the name of a gt sub-command *preceded by the @ symbol*
and following it with any desired parameters accepted by that sub-command.
For example, a step that runs GCAM might look like this:

  .. code-block:: xml

     <step seq="1" name="gcam"  runFor="baseline">@gcam -l -S {projectXmlDir} -s {baseline} -w {scenarioWsDir} -P</step>


Steps can be generalized by using variable definitions, as shown in
the example above. Several variables are set by the ``run``
sub-command at run-time;  these are are described below. The user
can also define variables, as described in the next section.

By default all steps are run. If the user specifies steps to run on the
command-line, then only those steps are run. If the attribute
``runFor="baseline"`` is set, the step is run only when processing the
baseline scenario. If ``runFor="policy"`` is set, the step is run only
or *non*-baseline strategies. By default steps are run for both baseline
and policy scenarios.

If a step's "optional" attribute is set to "true", the step is run only if
it is explicitly mentioned via the ``-s`` flag; by default it is not run.
This allows you to define steps that are used only occasionally. Optional
steps are identified as such in the output of the ``run -l`` sub-command
and flag.

If the ``group`` attribute is set, the step is run only when processing
the named scenario group. This allows you to define steps specific to
different scenario groups.

For example, the block:

  .. code-block:: xml

     <steps>
        <step name="setup" runFor="baseline">@setup -b {baseline} -g {scenarioGroup} -S {scenarioSubdir} -p {endYear} -y {shockYear}-{endYear}</step>
		<step name="gcam"  runFor="baseline">@gcam -S {projectXmlDir} -s {baseline} -w {scenarioWsDir}</step>
		<step name="query" runFor="baseline">@query -o {batchDir} -w {scenarioWsDir} -s {scenario} -Q "{queryPath}" "@{queryFile}"</step>
		<step name="setup" runFor="policy">@setup -b {baseline} -s {scenario} -g {scenarioGroup} -S {scenarioSubdir} -p {endYear} -y {shockYear}-{endYear}</step>
		<step name="gcam"  runFor="policy">@gcam -S {projectXmlDir} -s {scenario} -w {scenarioWsDir}</step>
		<step name="query" runFor="policy">@query -o {batchDir} -w {scenarioWsDir} -s {scenario} -Q "{queryPath}" "@{queryFile}"</step>
		<step name="plot"  runFor="all">@chart {scenPlotArgs} --scenario {scenario} --fromFile {scenPlots}</step>
		<step name="diff"  runFor="policy">@diff -D {sandboxDir} -y {years} -Y {shockYear} -q {queryFile} -i {baseline} {scenario}</step>
		<step name="plotDiff" runFor="policy">@chart {diffPlotArgs} --reference {baseline} --scenario {scenario} --fromFile {diffPlots}</step>
		<step name="xlsx" runFor="policy">@diff -D {diffsDir} -c -y {years} -Y {shockYear} -o "{scenario}-annual.xlsx" -i {diffsDir}/*.csv</step>
     </steps>

defines a series of steps that calls setup scripts, runs GCAM, runs a
set of XML batch queries, computes differences between policy and
baseline scenarios, plots the individual scenarios and the differences,
and generates .XLSX files with the differences--one with the values
directly from GCAM, the other with annually-interpolated values.

  .. _sequence-override-label:

Steps can be defined in the ``<defaults>`` section, in which case they
apply to all projects. Projects, however, can add, delete, or redefine
steps. To redefine a step, the project defines a ``<step>`` with the
same values for the attributes ``name``, ``seq``, and ``runFor``. A
default step can be effectively deleted by redefining it with no text
value, e.g.,

  .. code-block:: xml

    <step seq="9" name="xlsx" runFor="baseline"/>

Steps defined in projects that do not match default steps are added to
the set in the order indicated by ``seq``.

<vars>
^^^^^^

The ``<vars>`` element encloses a list of ``<var>`` elements, and takes
no attributes. The ``<vars>`` element may contain ``<CONDITIONAL>`` elements.

<var>
^^^^^

+-------------+------------+-----------+-----------------------------------+
| Attribute   | Required   | Default   | Values                            |
+=============+============+===========+===================================+
| name        | yes        | (none)    | text                              |
+-------------+------------+-----------+-----------------------------------+
| eval        | no         | "0"       | {"0", "1"}                        |
+-------------+------------+-----------+-----------------------------------+

Variables provide text that can be used in the command templates defined
by ``<step>`` elements. To access the variable, the name is enclosed in
curly braces, e.g., ``{project}``, which evaluates to the name of the
project.

Variables can be defined in the ``<defaults>`` section, in which case
they can be accessed by all projects. Variable can be added or redefined
in ``<project>`` definitions. (Automatic variables are described further below.)

The ``<vars>`` element contains a series of ``<var>`` declarations.
Values can be assigned directly to variable names, as in:

  .. code-block:: xml

    <var name="myVar">foo</var>

which assigns the value ``foo`` to the variable named ``myVar``, which
can be referenced in a ``<step>`` as ``{myVar}``.

Variables containing variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In some cases, a variable contains a variable reference that should be
evaluated before it is substituted into a command string. To do this,
set the attribute ``eval="1"``. Default is ``eval="0"``.

Config file variables
~~~~~~~~~~~~~~~~~~~~~

Value for the current project are loaded from the configuration file
(``~/.pygcam.cfg``) automatically. Note that the names are
case sensitive. See :doc:`config` for a list of defined variables.


Automatic variables
~~~~~~~~~~~~~~~~~~~

The ``run`` sub-command creates several convenience variables at run-time
that are accessible in the command steps. These include:

+--------------------+-----------------------------------------------------------------+
| Variable           | Value                                                           |
+====================+=================================================================+
|``{baseline}``      | the name of the scenario with baseline="1"                      |
+--------------------+-----------------------------------------------------------------+
|``{baselineDir}``   | the sandbox sub-directory for the baseline scenario             |
+--------------------+-----------------------------------------------------------------+
|``{batchDir}``      | ``{scenarioWsDir}/batch-{scenarioName}``                        |
+--------------------+-----------------------------------------------------------------+
|``{diffsDir}``      | ``{scenarioWsDir}/diffs``                                       |
+--------------------+-----------------------------------------------------------------+
|``{project}``       | the project name                                                |
+--------------------+-----------------------------------------------------------------+
|``{projectSrcDir}`` | ``{xmlSrc}/{scenarioGroup}/{projectSubdir}`` if                 |
|                    | ``useGroupDir=1`` is specified for scenarioGroup, else          |
|                    | ``{xmlSrc}/{projectSubdir}``                                    |
+--------------------+-----------------------------------------------------------------+
|``{projectSubdir}`` | subdir defined in the ; defaults to project name.               |
+--------------------+-----------------------------------------------------------------+
|``{projectWsDir}``  | ``{wsRoot}/{scenarioGroup}/{projectSubdir}`` if                 |
|                    | ``useGroupDir=1`` is specified for scenarioGroup, else          |
|                    | ``{wsRoot}/{projectSubdir}``                                    |
+--------------------+-----------------------------------------------------------------+
|``{projectXmlDir}`` | ``{local-xml}/{scenarioGroup}/{projectSubdir}`` if              |
|                    | ``useGroupDir=1`` is specified for scenarioGroup, else          |
|                    | ``{local-xml}/{projectSubdir}``                                 |
+--------------------+-----------------------------------------------------------------+
|``{reference}``     | a synonym for ``{baseline}``                                    |
+--------------------+-----------------------------------------------------------------+
|``{scenario}``      | scenario name                                                   |
+--------------------+-----------------------------------------------------------------+
|``{scenarioGroup}`` | the name of scenario group                                      |
+--------------------+-----------------------------------------------------------------+
|``{scenarioSubdir}``| subdir for the current scenario; default is | scenario name     |
+--------------------+-----------------------------------------------------------------+
|``{scenarioSrcDir}``| ``{projectSrcDir}/scenarioSubdir}``                             |
+--------------------+-----------------------------------------------------------------+
|``{scenarioXmlDir}``| ``{projectXmlDir/scenario}``                                    |
+--------------------+-----------------------------------------------------------------+
|``{scenarioWsDir}`` | ``{GCAM.SandboxRoot}/{scenario}``                               |
+--------------------+-----------------------------------------------------------------+
|``{step}``          | the name of the currently running step                          |
+--------------------+-----------------------------------------------------------------+

<tmpFile>
^^^^^^^^^

+-------------+------------+-----------+--------------------------+
| Attribute   | Required   | Default   | Values                   |
+=============+============+===========+==========================+
| varName     | yes        | (none)    | text                     |
+-------------+------------+-----------+--------------------------+
| dir         | no         | "/tmp"    | a legal directory name   |
+-------------+------------+-----------+--------------------------+
| delete      | no         | "1"       | {"0", "1"}               |
+-------------+------------+-----------+--------------------------+
| replace     | no         | "0"       | {"0", "1"}               |
+-------------+------------+-----------+--------------------------+
| eval        | no         | "1"       | {"0", "1"}               |
+-------------+------------+-----------+--------------------------+

To avoid a proliferation of files, it is possible to define the contents
of a temporary file directly in the project XML file. At run-time, the
temporary file is created; the given lines, defined by ``<text>``
elements, are written to the file, and the name of the temporary file is
assigned to the given variable name.

The ``<tmpFile>`` element defines several attributes:

-  ``varName`` (required) which will contain the pathname of the
   temporary file created by the ``run`` sub-command.

-  ``dir`` (optional) defines the directory in which to create the temp
   file Default is "/tmp".

-  ``delete`` indicates whether to delete the temporary file when
   ``run`` exits. By default, ``delete="1"``, i.e., the temp files
   are deleted. The value ``delete="0"`` may be useful for debugging.

-  ``replace`` indicates whether file contents defined in a project
   should be replace or append to the default value for this file
   variable. By default, values are appended, i.e., ``replace="0"``.
   Setting ``replace="1"`` causes the project values to replace the
   default values.

-  ``eval`` indicates whether to perform variable substitution on the
   values when writing the temporary file, as is done before executing
   commands. By default, ``evaluate="1"``, i.e., variable substitution
   is performed. Disable this by specifying ``evaluate="0"``, e.g., if
   part of your text might be confused for a variable reference.

For example,

  .. code-block:: xml

    <tmpFile varName="queryTempFile" dir="/tmp/myProject">
        <text>some text {scenario}</text>
        <text>other text</text>
    </tmpFile>

defines a temporary file that should be created in the directory
"/tmp/myProject", with the contents being the text in the two ``<text>``
elements. The pathname of the temp file is assigned to the variable
``queryTempFile``, which can be used in any ``<step>`` command. Since
the attribute ``evaluate="0"`` is not specified, the text values are
evaluated when writing them to the temp file, so ``{scenario}`` in the
first line is replaced with the name of the scenario being processed.

<text>
^^^^^^

+-------------+------------+-----------+----------+
| Attribute   | Required   | Default   | Values   |
+=============+============+===========+==========+
| tag         | no         | (none)    | text     |
+-------------+------------+-----------+----------+

The ``<text>`` element can take an option ``tag`` attribute, which
provides a unique name to a line of text so that projects can
selectively drop the line by redefining an a ``<text>`` element with the
same tag name. To delete a value, provide no value. For example, if the
defaults section has this definition:

  .. code-block:: xml

    <tmpFile varName="queryTempFile" dir="/tmp/myProject">
        <text>line 1</text>
        <text tag="2">line 2</text>
    </tmpFile>

a project can cause the second line to be dropped when writing the temp
file, by specifying:

  .. code-block:: xml

    <tmpFile varName="queryTempFile" dir="/tmp/myProject">
        <text tag="2"/>
    </tmpFile>

<queries>
^^^^^^^^^

The project file supports the same `<queries>` elements and sub-elements
that can appear in a separate :doc:`query XML file <query-xml>`, allowing
queries to be consolidated within the project.xml file, or managed separately.

The queries listed in the `<queries>` element are used both to execute batch
XML queries against the GCAM database, and to drive the `diff` step in the
standard project.xml, which calls the `diff` sub-command.

The ``<queries>`` element may contain ``<CONDITIONAL>`` elements.

Example project.xml file
------------------------

  .. code-block:: xml

     <projects>
        <project name="paper1">
          <vars>
            <!-- User variables, used only by defined steps -->
            <var name="startYear">2015</var>
            <var name="endYear">2050</var>
            <var name="years" eval="1">{startYear}-{endYear}</var>
            <var name="shockYear">2020</var>
            <var name="queryPath" eval="1">{GCAM.QueryDir}:{GCAM.QueryDir}/Main_queries_customized.xml</var>
          </vars>

          <steps>
            <step name="setup" runFor="baseline">@setup -b {baseline} -g {scenarioGroup} -S {scenarioSubdir} -p {endYear} -y {shockYear}-{endYear}</step>
            <step name="gcam" runFor="baseline">@gcam -S {projectXmlDir} -s {baseline} -w {scenarioWsDir}</step>
            <step name="query" runFor="baseline">@query -o {batchDir} -w {scenarioWsDir} -s {scenario} -Q "{queryPath}" "@{queryFile}"</step>
            <step name="setup" runFor="policy">@setup -b {baseline} -s {scenario} -g {scenarioGroup} -S {scenarioSubdir} -p {endYear} -y {shockYear}-{endYear}</step>
            <step name="gcam" runFor="policy">@gcam -S {projectXmlDir} -s {scenario} -w {scenarioWsDir}</step>
            <step name="query" runFor="policy">@query -o {batchDir} -w {scenarioWsDir} -s {scenario} -Q "{queryPath}" "@{queryFile}"</step>
            <step name="plot" runFor="all">@chart {scenPlotArgs} --scenario {scenario} --fromFile {scenPlots}</step>
            <step name="diff" runFor="policy">@diff -D {sandboxDir} -y {years} -Y {shockYear} -q {queryFile} -i {baseline} {scenario}</step>
            <step name="plotDiff" runFor="policy">@chart {diffPlotArgs} --reference {baseline} --scenario {scenario} --fromFile {diffPlots}</step>
            <step name="xlsx" runFor="policy">@diff -D {diffsDir} -c -y {years} -Y {shockYear} -o "{scenario}-annual.xlsx" -i {diffsDir}/*.csv</step>
          </steps>

          <queries varName="queryXmlFile" defaultMap="regions">
            <query name="Land_Allocation">
              <rewriter name="GTAP-BIO-ADV"/>
              <rewriter name="landCover"/>
            </query>
            <query name="Ag_Production_by_Crop_Type">
              <rewriter name="eightRegions"/>
              <rewriter name="landCover"/>
            </query>
          </queries>

          <vars>
            <var name="scenPlotArgs" eval="1">--verbose -D {batchDir} --outputDir figures --years {years} --label --labelColor black --box --enumerate</var>
            <var name="diffPlotArgs" eval="1">-D {diffsDir} --outputDir figures --years {years}</var>
            <var name="scenRefCsv" eval="1">{scenario}-{reference}.csv</var>
          </vars>

          <tmpFile varName="diffPlots">
            <text>Residue_biomass_production-{scenRefCsv} -Y 'EJ biomass' -n 4 -T '$\Delta$ Residue biomass production' -x sector-by-year.png -I sector</text>
            <text>Residue_biomass_production-{scenRefCsv} -Y 'EJ biomass' -n 4 -T '$\Delta$ Residue biomass production' -x region-by-year.png -I region</text>
            <text>refined-liquids-prod-by-tech-{scenRefCsv} -I technology -T '$\Delta$ Refined liquid fuels production' -c region -n 3</text>
            <text>Purpose-grown_biomass_production-{scenRefCsv} -Y "EJ biomass" -n 4 -c output -I region -z -T '$\Delta$ Purpose-grown biomass production' -x by-region.png</text>
            <text>Kyoto_gas_forcing-{scenRefCsv} -Y 'W/m$^2$' --timeseries -T '$\Delta$ Kyoto Gas Forcing'</text>
          </tmpFile>
        </project>
     </projects>

