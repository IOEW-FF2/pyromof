from oemof import solph
import pandas as pd

import os
from pathlib import Path
from oemof.network.graph import create_nx_graph
from oemof.tools import economics
from pyromof import helpers

# Reading in the raw data
profiles = pd.read_excel("input_data.xlsx", sheet_name="profiles")
sinks = pd.read_excel("input_data.xlsx", sheet_name="sink")
sources = pd.read_excel("input_data.xlsx", sheet_name="source")
converters = pd.read_excel("input_data.xlsx", sheet_name="converter")
storage = pd.read_excel("input_data.xlsx", sheet_name="storage")
general = pd.read_excel("input_data.xlsx", sheet_name="general")

# Read in the scenario and set investment variable
scenario = general.loc[general["item"] == "scenario", "value"].item()
print("Selected scenario: " + scenario)

ROOT_PATH = Path(__file__).parent.parent
RESULTS = os.path.join(ROOT_PATH, "results")
# Create folder for the scenario within the results folder if it doesn't exist yet
Path(os.path.join(RESULTS, scenario)).mkdir(exist_ok=True)
SCENARIO_PATH = os.path.join(RESULTS, scenario)
# Create folders for meta_info and dumping_space
Path(os.path.join(SCENARIO_PATH, "meta_info")).mkdir(exist_ok=True)
META_INFO = os.path.join(SCENARIO_PATH, "meta_info")
Path(os.path.join(SCENARIO_PATH, "dumping_space")).mkdir(exist_ok=True)
DUMPING_SPACE = os.path.join(SCENARIO_PATH, "dumping_space")

# Initiate an investment variable as False that will be overwritten
# with True if any component with investment is added.
# This information is required for the postprocessing.
investment = False

# Definition of the time period
time = pd.date_range("2023-01-02", periods=145, freq="h")

# Read in wacc for investment optimization
wacc = general.loc[general["item"] == "wacc", "value"].item()

# Initiate dataframe to store annuities


# Model definition
es = solph.EnergySystem(timeindex=time)


def matches_scenario(scenario_to_check, scenario_wanted):
    """
    Checks wether the string "scenario to check" is either "all" or includes the "scenario_wanted".
    "scenario_wanted" should be the scenario to be optimized, and "scenario_to_check" a scenario field
    from the input data.
    """
    return scenario_to_check == "all" or scenario_wanted in scenario_to_check


def extract_components_and_buses_from_input_data(
    sinks, sources, converters, storage, scenario_wanted
):
    """
    Takes the dfs from the input data sheets and the selected scenario and extracts
    (1) the components included in the scenario and (2) the buses which are connected
    to these components. The buses are returned as a dataframe with one column named
    "label" and the components are returned as a list.
    """
    # Filter input data sheets by scenario
    filtered_sinks = sinks[
        sinks["scenario"].apply(matches_scenario, args=(scenario_wanted,))
    ]
    filtered_sources = sources[
        sources["scenario"].apply(matches_scenario, args=(scenario_wanted,))
    ]
    filtered_converters = converters[
        converters["scenario"].apply(matches_scenario, args=(scenario_wanted,))
    ]
    filtered_storage = storage[
        storage["scenario"].apply(matches_scenario, args=(scenario_wanted,))
    ]

    # Create component list for the selected scenario
    components = (
        filtered_sinks["label"].tolist()
        + filtered_sources["label"].tolist()
        + filtered_converters["label"].tolist()
        + filtered_storage["label"].tolist()
    )

    # Create list of unique buses for the selected scenario
    buses = (
        filtered_sinks["bus_in"].tolist()
        + filtered_sources["bus_out"].tolist()
        + filtered_converters[
            ["bus_in_1", "bus_in_2", "bus_out_1", "bus_out_2", "bus_out_3"]
        ]
        .stack()
        .tolist()
        + filtered_storage[["bus_in", "bus_out"]].stack().tolist()
    )
    # Filter unique values
    buses = set(buses)
    # Convert back to list
    buses = list(buses)
    # Convert to dataframe
    buses_df = pd.DataFrame(data={"label": buses})
    return buses_df, components


buses, components = extract_components_and_buses_from_input_data(
    sinks, sources, converters, storage, scenario
)

# Create Bus objects from buses table

print("Adding the following buses to the energy system:")
print(buses)

nodes = []
busd = {}

for i, b in buses.iterrows():
    bus = solph.Bus(label=b["label"])
    nodes.append(bus)
    busd[b["label"]] = bus
    es.add(bus)


# Create other components
print("Adding the following components to the energysystem:")
print(components)

# SINKS
if "biochar_market" in components:
    row = sinks.loc[sinks.label == "biochar_market", :]
    biochar_market = solph.components.Sink(
        label="biochar_market",
        inputs={
            busd[row.bus_in.item()]: solph.Flow(
                variable_costs=row.variable_costs.item()
            )
        },
    )
    es.add(biochar_market)

if "co2_market" in components:
    row = sinks.loc[sinks.label == "co2_market", :]
    co2_market = solph.components.Sink(
        label="co2_market",
        inputs={
            busd[row.bus_in.item()]: solph.Flow(
                variable_costs=row.variable_costs.item()
            )
        },
    )
    es.add(co2_market)

if "electricity_grid" in components:
    row = sinks.loc[sinks.label == "electricity_grid", :]
    electricity_grid = solph.components.Sink(
        label="electricity_grid",
        inputs={
            busd[row.bus_in.item()]: solph.Flow(
                variable_costs=row.variable_costs.item()
            )
        },
    )
    es.add(electricity_grid)

if "heat_demand_ht" in components:
    row = sinks.loc[sinks.label == "heat_demand_ht", :]
    heat_demand_ht = solph.components.Sink(
        label="heat_demand_ht",
        inputs={
            busd[row.bus_in.item()]: solph.Flow(
                nominal_value=row.amount.item(),
                fix=profiles[row.profile.item()],
                variable_costs=row.variable_costs.item(),
            )
        },
    )
    es.add(heat_demand_ht)

if "heat_demand_lt" in components:
    row = sinks.loc[sinks.label == "heat_demand_lt", :]
    heat_demand_lt = solph.components.Sink(
        label="heat_demand_lt",
        inputs={
            busd[row.bus_in.item()]: solph.Flow(
                nominal_value=row.amount.item(),
                fix=profiles[row.profile.item()],
                variable_costs=row.variable_costs.item(),
            )
        },
    )
    es.add(heat_demand_lt)

# SOURCES
if "biomass" in components:
    row = sources.loc[sources.label == "biomass", :]
    biomass = solph.components.Source(
        label="biomass",
        outputs={
            busd[row.bus_out.item()]: solph.Flow(
                nominal_value=row.amount.item(),
                variable_costs=row.variable_costs.item(),
            )
        },
    )
    es.add(biomass)

if "heat_source" in components:
    row = sources.loc[sources.label == "heat_source", :]
    heat_source = solph.components.Source(
        label="heat_source",
        outputs={
            busd[row.bus_out.item()]: solph.Flow(
                variable_costs=row.variable_costs.item()
            )
        },
    )
    es.add(heat_source)

# CONVERTERS

if "conversion_orc" in components:
    row = converters.loc[converters.label == "conversion_orc"]
    if row.investment.item() is True:
        investment = True
        print(
            "Warning: Investment optimisation is not yet implemented for conversion_orc."
        )
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        print("epc for conversion_orc: ", epc)
        conversion_orc = solph.components.Converter(
            label="conversion_orc_invest",
            inputs={busd[row.bus_in_1.item()]: solph.Flow()},
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(),
                busd[row.bus_out_2.item()]: solph.Flow(),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                busd[row.bus_out_2.item()]: row.eff_out_2.item(),
            },
        )
    elif row.investment.item() is False:
        conversion_orc = solph.components.Converter(
            label="conversion_orc",
            inputs={busd[row.bus_in_1.item()]: solph.Flow()},
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(),
                busd[row.bus_out_2.item()]: solph.Flow(),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                busd[row.bus_out_2.item()]: row.eff_out_2.item(),
            },
        )
    es.add(conversion_orc)

if "pyrolysis" in components:
    row = converters.loc[converters.label == "pyrolysis"]
    if row.investment.item() is True:
        investment = True
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        print("epc for pyrolysis: ", epc)
        pyrolysis = solph.components.Converter(
            label="pyrolysis_invest",
            inputs={
                busd[row.bus_in_1.item()]: solph.Flow(),
                busd[row.bus_in_2.item()]: solph.Flow(),
            },
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=solph.Investment(ep_costs=epc)
                ),
                busd[row.bus_out_2.item()]: solph.Flow(),
                busd[row.bus_out_3.item()]: solph.Flow(),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_in_2.item()]: row.eff_in_2.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                busd[row.bus_out_3.item()]: row.eff_out_3.item(),
            },
        )
    elif row.investment.item() is False:
        pyrolysis = solph.components.Converter(
            label="pyrolysis",
            inputs={
                busd[row.bus_in_1.item()]: solph.Flow(),
                busd[row.bus_in_2.item()]: solph.Flow(),
            },
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(),
                busd[row.bus_out_2.item()]: solph.Flow(),
                busd[row.bus_out_3.item()]: solph.Flow(),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_in_2.item()]: row.eff_in_2.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                busd[row.bus_out_3.item()]: row.eff_out_3.item(),
            },
        )
    es.add(pyrolysis)

if "combustor_hot" in components:
    row = converters.loc[converters.label == "combustor_hot"]
    if row.investment.item() is True:
        investment = True
        print(
            "Warning: Investment optimisation is not yet implemented for combustor_hot."
        )
        combustor_hot = solph.components.Converter(
            label="combustor_hot",
            inputs={
                busd[row.bus_in_1.item()]: solph.Flow(),
            },
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
            },
        )
    elif row.investment.item() is False:
        combustor_hot = solph.components.Converter(
            label="combustor_hot",
            inputs={
                busd[row.bus_in_1.item()]: solph.Flow(),
            },
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
            },
        )
    es.add(combustor_hot)


# Initialise the operational model
om = solph.Model(es)

print("The model has been constructed.")

# Tell the model to get the dual variables when solving
# om.receive_duals()

# Store lp file for debugging
file_path = os.path.join(META_INFO, "lp_file.lp")
om.write(file_path, io_options={"symbolic_solver_labels": True})

# Solve the system
om.solve(solver="cbc")

# Save model structure as a graph in the graphml format. Can be opened e.g. in Gephi.
filename = os.path.join(META_INFO, "es_graph.graphml")
graph = create_nx_graph(es, filename=filename)

# get results from the solved model
es.params = solph.processing.parameter_as_dict(es)
es.results["main"] = solph.processing.results(om)
es.results["meta"] = solph.processing.meta_results(om)
es.results["scenario"] = scenario
es.results["investment"] = investment

flows = solph.processing.convert_keys_to_strings(om.flows)
columns = [a for a, b in flows.items()]
df = pd.DataFrame(columns=columns)
for col in df.columns:
    df[col] = [b for a, b in flows.items() if a == col][0].variable_costs
variable_costs = helpers.convert_tuple_columnnames_to_strings(df)
variable_costs.to_csv(
    os.path.join(DUMPING_SPACE, "variable_costs_from_model.csv"), sep=";"
)

# dump the EnergySystem
es.dump(dpath=DUMPING_SPACE, filename="es_dump.oemof")
print("The results have been saved.")
