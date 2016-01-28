runProject.py
=============

runProject.py is a workflow management script for GCAM. It reads a single XML input
file that defines one or more projects, one or more scenarios, and one or more
workflow steps. The workflow steps for the chosen projectd and scenario(s) are run
in the order defined. The script was developed for use with the [gcam-utils](https://bitbucket.org/plevin/gcam-utils/wiki/Home) scripts, however any scripts or programs can be called in workflow 'steps'.

Command-line usage and the `project.xml` file elements are described below.

## Command-line Usage

    $ runProject.py -h
    usage: runProject.py [-h] [-l] [-L] [-n] [-p PROJECTFILE] [-s STEPS]
                         [-S SCENARIOS] [--vars] [-v] [-V]
                         project
    
    Perform a series of steps typical for a GCAM-based analysis. This script reads
    instructions from the file project.xml, the location of which is taken from
    the user's pygcam.cfg file.
    
    positional arguments:
      project               The project to run.
    
    optional arguments:
      -h, --help            show this help message and exit
      -l, --listSteps       List the steps defined for the given project and exit.
                            Dynamic variables (created at run-time) are not
                            displayed.
      -L, --listScenarios   List the scenarios defined for the given project and
                            exit. Dynamic variables (created at run-time) are not
                            displayed.
      -n, --noRun           Display the commands that would be run, but don't run
                            them.
      -p PROJECTFILE, --projectFile PROJECTFILE
                            The directory into which to write the modified files.
                            Default is taken from config file variable
                            GCAM.ProjectXmlFile, if defined, otherwise the default
                            is './project.xml'.
      -s STEPS, --step STEPS
                            The steps to run. These must be names of steps defined
                            in the project.xml file. Multiple steps can be given
                            in a single (comma-delimited) argument, or the -s flag
                            can be repeated to indicate additional steps. By
                            default, all steps are run.
      -S SCENARIOS, --scenario SCENARIOS
                            Which of the scenarios defined for the given project
                            should be run. Multiple scenarios can be given in a
                            single (comma-delimited) argument, or the -S flag can
                            be repeated to indicate additional steps. By default,
                            all active scenarios are run.
      --vars                List variables and their values
      -v, --verbose         Show diagnostic output
      -V, --version         show program's version number and exit

#### Examples

Run all steps for project Foo:

    runProject.py Foo

Run all steps for project Foo, but only for scenarios 'baseline' and 'policy-1':

    runProject Foo -S baseline,policy1
    
or, equivalently:

    runProject Foo -S baseline -S policy1

Run steps 'setup' and 'gcam' for scenario 'baseline' only

    runProject Foo -s setup,gcam -S baseline,policy-1

Show the commands that would be executed for the above command, but don't run them:

    runProject Foo -s setup,gcam -S baseline,policy-1 -n

## XML elements used to describe projects (project.xml)

###Projects

The element `<projects>` encloses one or more `<project>` elements and zero or 
more `<defaults>` elements. The `<projects>` element has no attributes.

A `<project>` defines a set of variables, scenarios, and workflow steps, as described
below.

The element `<defaults>` sets default values for variables and workflow steps. This 
allows definitions to be shared across projects, reducing redundancy. Individual 
projects can be override variables and declare new variables and steps as needed.
The `<defaults>` element has no attributes.

----
###Scenarios

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

----
###Steps

The element `<steps>` contains a series of `<step>` declarations, and has no
attributes. Multiple `<steps>` elements are allowed.

A `<step>` describes one step in the workflow. Each step has a name and a sequence
number, which can be integer or float. Steps (from one or more `<steps>` sections)
are sorted by sequence number before execution. By definition, steps with the same
same sequence number are order independent; they can run in any order. 

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

Steps can be defined in the `<defaults>` section, in which case they apply to all
projects. Projects, however, can add, delete, or redefine steps. To redefine a step,
the project defines a `<step>` with the same values for the attributes `name`, 
`seq`, and `runFor`. A default step can be deleted by redefining it with no text
value, e.g., 

    <step seq="10" name="gcam" runFor="baseline"/>

Steps defined in projects that do not match default steps are added to the set 
in the order indicated by `seq`.

----
###Variables

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

#### Variables containing variables
In some cases, a variable contains a variable reference that should be 
evaluated before it is substituted into a command string. To do this, set
the attribute `eval="1"`. Default is `eval="0"`.

#### Config file variables

Any `<var>` can take its value from the value of a configuration file 
(`~/.config/pygcam.cfg`) variable by specifying the attribute `configVar="XXX"`,
where *XXX* is the name of the config file variable to copy. For example:

	<var name="queryFile" configVar="GCAM.QueryFile"/>

assigns to the variable `queryFile` the value from the configuration file 
variable named `GCAM.QueryFile`.

#### Required variables
There are three required variables:

* `<var name="wsRoot">` -- Set this to the top-level directory holding
run-time workspaces. The GCAM workspace name is the computed value
{wsRoot}/{project}/{scenario}.

* `<var name="xmlsrc">` -- Set this to the top-level directory holding source
files for the setup tools. Scenario source files are in the computed value
{xmlsrc}/{project}/{scenarioSubdir}.

* `<var name="localXml">` -- Set this to the top-level directory holding XML
files generated by the setup tools. Scenario files are found at computed
location {localXml}/{project}/{scenarioSubdir}

#### Automatic variables
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

#### File variables

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

* `evaluate` indicates whether to perform variable substitution on the
<text> values when writing the temporary file, as is done before executing
<step> commands. By default, `evaluate="1"`, i.e., variable substitution
is performed. Disable this by specifying `evaluate="0"`.

For example, 

    <tmpFile varName="queryTempFile" dir="/tmp/myProject">
        <text>some text {scenario}</text>
        <text>other text</text>
    </tmpFile>
    
defines a temporary file that should be created in the directory "/tmp/myProject",
with the contents being the text in the two `<text>` elements. The pathname of the
temp file is assigned to the variable `queryTempFile`, which can be used in any
`<step>` command. Since the attribute `evaluate="0"` is not specified, the text
values are evaluated when writing them to the temp file, so `{scenario}` in the 
first line is replaced with the name of the scenario being processed.

The `<text>` element can take an option `tag` attribute, which, provides a unique
name to a line of text so that projects can selectively drop lines by redefining
an empty `<text>` element with the same tag name. For example, if the defaults
section has this definition:

    <tmpFile varName="queryTempFile" dir="/tmp/myProject">
        <text>line 1</text>
        <text tag="2">line 2</text>
    </tmpFile>

a project can cause the second line to be dropped when writing the temp file, 
by specifying:

    <tmpFile varName="queryTempFile" dir="/tmp/myProject">
        <text tag="2"/>
    </tmpFile>
    
----------

## Example project.xml file

    <projects>
      <defaults>
		<vars>
			<!-- Required variables -->
			<var name="workspaceRoot" configVar="GCAM.WorkspaceRoot"/>
			<var name="xmlsrc" configVar="GCAM.XmlSrc"/>
			<var name="localXml" configVar="GCAM.LocalXml"/>

			<!-- User variables, used only by defined steps -->
			<var name="setup">setup.py</var>
			<var name="startYear">2015</var>
			<var name="endYear">2050</var>
			<var name="shockYear">2020</var>
			<var name="queryDir" configVar="GCAM.QueryDir"/>
			<var name="repoBin" configVar="GCAM.RepoBin"/>
			<var name="queryPath" configVar="GCAM.QueryPath"></var>
		</vars>
		<steps>
			<step seq="1" name="setup" runFor="baseline">{scenarioSrcDir}/{setup}</step>
			<step seq="2" name="gcam"  runFor="baseline">queueGCAM.py -l -S {projectXmlDir} -s {baseline} -w {scenarioWsDir} -P</step>
			<step seq="3" name="query" runFor="baseline">batchQuery.py -v -o {batchDir} -w {scenarioWsDir} -s {scenario} -Q "{queryPath}" "@{queryFile}"</step>
			<step seq="4" name="setup" runFor="policy">{scenarioSrcDir}/{setup}</step>
			<step seq="5" name="gcam"  runFor="policy">queueGCAM.py -l -S {projectXmlDir} -s {scenario} -w {scenarioWsDir} -P</step>
			<step seq="6" name="query" runFor="policy">batchQuery.py -v -o {batchDir} -w {scenarioWsDir} -s {scenario} -Q {queryPath} "@{queryFile}"</step>
			<step seq="7" name="plotScen">chartGCAM.py {scenPlotArgs} --scenario {scenario} --fromFile {scenPlots}</step>
			<step seq="7" name="diff"  runFor="policy">csvDiff.py -D {projectWsDir} -y {years} -Y {shockYear} -q {queryFile} -i {baseline} {scenario}</step>
			<step seq="8" name="plotDiff" runFor="policy">chartGCAM.py {diffPlotArgs} --reference {baseline} --scenario {scenario} --fromFile {diffPlots}</step>
			<step seq="9" name="xlsx"  runFor="policy">csvDiff.py -D {diffsDir} -c -y {years} -Y {shockYear} -o diffs.xlsx *.csv</step>
			<step seq="9" name="xlsx"  runFor="policy">csvDiff.py -D {diffsDir} -c -y {years} -Y {shockYear} -o "{scenario}-annual.xlsx" -i *.csv</step>
		</steps>
		
		<tmpFile varName="queryFile" evaluate="0">
			<text>Residue_biomass_production</text>
			<text>refined-liquids-prod-by-tech</text>
			<text>Purpose-grown_biomass_production</text>
			<text>Kyoto_gas_forcing</text>
		</tmpFile>
		
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
	  </defaults>

      <project name="Paper1">
		<scenario name="base-1" subdir="baseline" baseline="1"/>
		<scenario name="corn-1" subdir="corn"/>
		<scenario name="stover-1" subdir="stover" active="0"/>
		<scenario name="switchgrass-1" subdir="switchgrass" active="0"/>
		<scenario name="biodiesel-1" subdir="biodiesel" active="0"/>
	  </project>
	</projects>
