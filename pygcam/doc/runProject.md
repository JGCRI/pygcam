runProject.py
=============

runProject.py is a workflow management script for GCAM. It reads a single XML input
file that defines one or more projects, one or more scenarios, and one or more
workflow steps. The file elements are described below.

Projects
--------
The element `<projects>` encloses one or more `<project>` elements and zero or 
more `<defaults>` elements. The `<projects>` element has no attributes.

A `<project>` defines a set of variables, scenarios, and workflow steps, as described
below.

The element `<defaults>` sets default values for variables and workflow steps. This 
allows definitions to be shared across projects, reducing redundancy. Individual 
projects can be override variables and declare new variables and steps as needed.
The `<defaults>` element has no attributes.

Scenarios
---------
The `<scenario>` element describes a single GCAM scenario, which is either a baseline
scenario or a policy scenario. Each scenario must have a unique name within the project.
Scenarios are "active" by default, but can be deactivated by specifying the attribute
`active="0"`.

Each project must define exactly one active baseline scenario, defined by specifying
the attribute `baseline="1"`.

The setup tools expect each scenario to be defined in a sub-directory below the 
project directory. By default the sub-directory is named the same as the scenario,
but this can be defined separately using the `subdir="otherName"` attribute.

For example,

    <scenario name="biodiesel-1" subdir="biodiesel" active="0"/>
    
defines a scenario named `biodiesel-1` that is found in the sub-directory 
`biodiesel`, but the scenario is not currently active, so it is ignored when
the project is run.

Steps
-----
The element `<steps>` contains a series of `<step>` declarations, and has no
attributes.

A `<step>` describes one step in the workflow. Each step has a name and an integer
sequence number, neither of which needs to be unique. Steps can be referenced by 
name from the command-line to run all steps of the given name(s).

Steps are generalized by using variable definitions, some of which are set directly
by the user and other which are set by the runProject.py script at run-time. Variables
are described below.

By default all steps are run. If the user specifies steps to run on the command-line,
then only those steps are run. If the attribute `runFor="baseline"` is set, the step 
is run only when processing the baseline scenario. If `runFor="policy"` is set, the 
step is run only or *non*-baseline strategies. By default steps are run for both 
baseline and policy scenarios.

For example, 

    <step seq="10" name="gcam" runFor="baseline">
   
defines a step with named "gcam", with sequence number "10", that is run only 
for the baseline scenario.

For example, the block:

    <steps>
        <step seq="05" name="setup" runFor="baseline">{scenarioSrcDir}/{setup}</step>
        <step seq="10" name="gcam"  runFor="baseline">queueGCAM.py -l -S {projectXmlDir} -s {baseline} -w {scenarioWsDir} -P</step>
        <step seq="15" name="query" runFor="baseline">batchQuery.py -v -o {batchDir} -w {scenarioWsDir} -s {scenario} -Q "{queryPath}" "@{queryFile}"</step>
        <step seq="20" name="setup" runFor="policy">{scenarioSrcDir}/{setup}</step>
        <step seq="25" name="gcam"  runFor="policy">queueGCAM.py -l -S {projectXmlDir} -s {scenario} -w {scenarioWsDir} -P</step>
        <step seq="30" name="query" runFor="policy">batchQuery.py -v -o {batchDir} -w {scenarioWsDir} -s {scenario} -Q {queryPath} "@{queryFile}"</step>
        <step seq="45" name="diff" runFor="policy">computeDiffs.sh {baseline} {scenario}</step>
        <step seq="50" name="plotDiffs" runFor="policy">chartGCAM.py {diffPlotArgs} --reference {baseline} --scenario {scenario} --fromFile {plotDiffsFile}</step>
    </steps>

defines a series of steps that calls setup scripts, runs GCAM, runs a set of XML batch 
queries, computes differences between policy and baseline scenarios, and plots the
differences.

Steps are sorted by their integer sequence number. By definition, steps with the
same sequence number are order independent; they can run in any order. 

Steps can be defined in the `<defaults>` section, in which case they apply to all
projects. Projects, however, can add, delete, or redefine steps. To redefine a step,
the project defines a `<step>` with the same values for the attributes `name`, 
`seq`, and `runFor`. A default step can be deleted by redefining it with no text
value, e.g., 

    <step seq="10" name="gcam" runFor="base"/>

Steps defined in projects that do not match default steps are added to the set 
in the order indicated by `seq`.

Variables
---------
Variables provide text that can be used in the command templates defined by
`<step>` elements. To access the variable, the name is enclosed in curly braces,
 e.g., `{project}`, which evaluates to the name of the project.

Variables can be defined in the `<defaults>` section, in which case they can be
accessed by all projects. Variable can be added or redefined in `<project>` 
definitions. Two special types of variables (config file variables and automatic
variables) are described further below.

The `<vars>` element contains a series of `<var>` declarations. Values can be
assigned directly to variable names, as in:

    <var name="myVar">foo</var>

which assigns the value `foo` to the variable named `myVar`, which can be
referenced in a `<step>` as `{myVar}`.

### Config file variables

Any `<var>` can take its value from the value of a configuration file 
(`~/.config/pygcam.cfg`) variable by specifying the attribute `configVar="XXX"`,
where *XXX* is the name of the config file variable to copy. For example:

	<var name="queryFile" configVar="GCAM.QueryFile"/>

assigns to the variable `queryFile` the value from the configuration file 
variable named `GCAM.QueryFile`.

### Required variables
There are three required variables:

* `<var name="wsRoot">` -- Set this to the top-level directory holding
run-time workspaces. The GCAM workspace name is the computed value
{wsRoot}/{project}/{scenario}.

* `<var name="xmlsrc">` -- Set this to the top-level directory holding source
files for the setup tools. Scenario source files are in the computed value
{xmlsrc}/{project}/{scenarioSubdir}.

* `<var name="local-xml">` -- Set this to the top-level directory holding XML
files generated by the setup tools. Scenario files are found at computed
location {local-xml}/{project}/{scenarioSubdir}

### Automatic variables
runProject.py creates several convenience variables at run-time that are accessible
in the commands for any <step>. These included:

* `{project}` : the project name
* `{scenario}` : scenario name
* `{baseline}` : the name of the scenario with baseline="1"
* `{reference}` : a synonym for baseline
* `{step}` : the name of the currently running step
* `{years}` : {startYear}-{endYear}
* `{projectSubdir}` : subdir defined in the <project>; defaults to project name.
* `{projectSrcDir}` : {xmlSrc}/{projectSubdir}
* `{projectWsDir}` : {wsRoot}/{projectSubdir}
* `{projectXmlDir}` : {local-xml}/{projectSubdir}
* `{scenarioSubdir}` : subdir for the current scenario; default is scenario name
* `{scenarioSrcDir}` : {projectSrcDir}/scenarioSubdir}
* `{scenarioXmlDir}` : {projectXmlDir/scenarioSubdir}
* `{scenarioWsDir}` : {projectWsDir}/{scenario}
* `{diffsDir}` : {scenarioWsDir}/diffs
* `{batchDir}` : {scenarioWsDir}/batch-{scenarioName}

### File variables

To avoid a proliferation of files, it is possible to define the contents of a
temporary file directly in the project XML file. At run-time, the temporary
file is created; the given lines, defined by `<text>` elements, are written
to the file, and the name of the temporary file is assigned to the given 
variable name.

The `<tmpFile>` element defines several attributes:

* `varName` (required) which will contain the pathname of the temporary file
created by runProject.py
 
* `dir` (optional) defines the directory in which to create the temp file 
Default is "/tmp".

* `delete` indicates whether to delete the temporary file when runProject
exits. By default, `delete="1"`, i.e., the temp files are deleted. The value 
`delete="0"` may be useful for debugging.

* `replace` indicates whether file contents defined in a project should be
replace or append to the default value for this file variable. By default,
values are appended, i.e., `replace="0"`. Setting `replace="1"` causes the
project values to replace the default values.

For example, 

    <tmpFile varName="queryTempFile" dir="/tmp/runProject">
        <text>line 1</text>
        <text>line 2</text>
    </tmpFile>
    
defines a temporary file that should be created in the directory "/tmp/runProject",
with the contents being the text in the two `<text>` elements. The pathname of the
temp file is assigned to the variable `queryTempFile`, which can be used in any
`<step>` command.

The `<text>` element can take an option `tag` attribute, which, provides a unique
name to a line of text so that projects can selectively drop lines by redefining
an empty `<text>` element with the same tag name. For example, if the defaults
section has this definition:

    <tmpFile varName="queryTempFile" dir="/tmp/runProject">
        <text>line 1</text>
        <text tag="2">line 2</text>
    </tmpFile>

a project can cause the second line to be dropped when writing the temp file, 
by specifying:

    <tmpFile varName="queryTempFile" dir="/tmp/runProject">
        <text tag="2"/>
    </tmpFile>
