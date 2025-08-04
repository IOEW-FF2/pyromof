# Usage of pyromof

The main task in using pyromof is to prepare the input data. Afterwards, the model has to be created and optimized (in optimize.py), it should be postprocessed to store the results in a readable format (in postprocessing.py) and the results can be plotted (in plotting.py). It is also possible to compare the results of different scenarios in a plot (compare_scenarios.py) or to do a sensitivity analysis (analyse_sensitivity.py). In the following, the different steps and options therein will be explained.

## Preparing the input data
A template for the input data is provided in the docs folder. It is an excel file that must be located in the top layer of the pyromof folder and must be named "input_data.xlsx". Within the input data, there must be the sheets "general", "sink", "source", "converter", "storage" and "profiles". Other sheets will be ignored. The sheet "general" must contain a value for the weighted average costs of capital (wacc). In the converter sheet at least a component named "pyrolysis" must exist. All other components can be freely added or removed as long as the system is in itself complete.
Below is a list of the available components and their implemented attributes:


|Type|Component|Attributes|
|----|---------|----------|
|sink|biochar market|variable costs|
|    |co2 market    |nominal capacity, minimum, variable costs|
|    |electricit grid|nominal capacity, minimum, variable costs|
|    |heat market ht|nominal capacity, minimum, variable costs|
|    |heat market lt|nominal capacity, fix profile, variable costs|
|    |oil market|variable costs|
|    |h2 market|variable costs|
|    |torch|variable costs|
|    |heat lt excess|variable costs|
|source|biomass|nominal capacity, variable costs|
|       |heat source|variable costs|

List of attributes for converters:
|component|no. inp.|no. outp.|attributes inv. mode|attributes dispatch mode|
|---------|----------|-----------|----------|---|
|orc|1|2|ep costs|- |
|chp|1|3|ep costs, existing capacity|nominal capacity|
|power to heat|1|1|ep costs|nominal capacity|
|h2 filtration|1|1|ep costs|nominal capacity|
|pyrolysis|2|3|*ep costs*, startup costs, minimum downtime, minimum load share, *maximum capacity*, *existing capacity*, out 1 max decrease, out 2 max corresponding increase|*nominal capacity*, *positive gradient limit*, startup costs, minimum load share, minimum downtime, out 1 max decrease, out 2 max corresponding increase|
|combustor hot|1|1|ep costs|-|
|combustor cold|1|1|not implemented|-|
|condensor|1|2|not implemented|-|
|biomass dryer|2|1|not implemented|-|

The ep costs are not a direct input but are calculated from the capex, the lifetime and the wacc.

For storage, all storage types have the same attributes. These are as follows:

|no. inp.|no. outp.|attributes|
|--------|---------|--------------------|
|1      |   1      |loss rate, initial storage level, inflow conversion factor, outflow conversion factor, nominal storage capacity|

In investment mode, the nominal storage capacity is calculated from capex, lifetime and wacc. It would also be possible to implement a capex for storage and withdrawel.

For an explanation of the attributes you may read the [documentation of oemof solph](https://oemof-solph.readthedocs.io/en/stable/reference/oemof.solph.flow.html).

Two costum attributes have been added for the pyrolysis component in this model: out 1 max decrease and out max 2 corresponding increase. The two values together are used to define a minimum ratio between outputs 1 and 2:
```math
ratio_{min} = \frac{eff(out1) + eff(out1)*\text{out\_1\_max\_decrease}}{eff(out2) + eff(out2) *\text{out\_2\_corresponding\_increase}}
```
$ratio_{max}$ is given by the unchanged relation between the two output efficiencies.

The scenario in the input data can be a single scenario, multiple scenarios separated by commas or the word *all*. In any case there must be a string in the scenario column for every row that has a label, otherwise the model will throw an error.

## Building and optimizing the model
To build and optimize the model you have to run the script *optimize.py*. By default, the script will ask you which scenario you want to optimize, and you can type it into the terminal. Only the date range must be set directly in the code in the section "Definition of the time period".

*optimize.py* will also ask you if you want to visualize the energy system in dash. If you say yes it runs the optimization again and asks you a second time, and if you repeat a yes you can see the visualization if you copy the indicated link into your browser.

## Postprocessing
Postprocessing is very straight forward by running *postprocessing.py*. The script will also ask you which scenario it shall postprocess.

To speed up the work flow when working on one scenario I recommend to set the scenario directly in the code and execute the script *pipeline.py* to run *optimize.py* and *postprocessing.py* in direct succession.

## Plotting
Plotting with *plotting.py* simply requires executing the script and again answering the scenario prompt. In *compare_scenarios.py* you will be prompted to type in multiple scenarios separated by commas. The script will plot the scalar results (= mostly summed up costs and flows over the entire period) in bar charts next to each other.

## Sensitivity analysis
A sensitivity analysis can be done with *analyse_sensitivity.py*. Here you have to adjust the parameters directly in the script. The parameters to be set are the component type (sinks, sources, converters or storage), the component, the target parameter, its minimum value, its maximum value and the step width. Furthermore, you must also set the scenario and the time period directly in the script.