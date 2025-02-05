from oemof import solph
import pandas as pd

import os
from pathlib import Path
from oemof.network.graph import create_nx_graph
from oemof.tools import economics
from pyromof import helpers

ROOT_PATH = Path(__file__).parent.parent
META_INFO = os.path.join(ROOT_PATH, "meta_info")
DUMPING_SPACE = os.path.join(ROOT_PATH, "dumping_space")

# Reading in the raw data
profiles = pd.read_excel("input_data.xlsx", sheet_name="profiles")
sinks = pd.read_excel("input_data.xlsx", sheet_name="sink")
sources = pd.read_excel("input_data.xlsx", sheet_name="source")
transformers = pd.read_excel("input_data.xlsx", sheet_name="transformer")
storage = pd.read_excel("input_data.xlsx", sheet_name="storage")
general = pd.read_excel("input_data.xlsx", sheet_name="general")

# Read in the scenario and set investment variable
scenario = general.loc[general["item"] == "scenario", "value"].item()
print("Selected scenario: " + scenario)

# Definition of the time period
time = pd.date_range("2023-01-02", periods=145, freq="h")

# Read in wacc for investment optimization
wacc = general.loc[general["item"] == "wacc", "value"].item()

# Initiate dataframe to store annuities


# Model definition
es = solph.EnergySystem(timeindex=time)

nodes = []
busd = {}


def matches_scenario(scenario_to_check, scenario_wanted):
    return scenario_to_check == "all" or scenario_wanted in scenario_to_check


def extract_components_and_buses_from_input_data(
    sinks, sources, transformers, storage, scenario_wanted
):
    print(scenario_wanted)
    filtered_sinks = sinks[
        sinks["scenario"].apply(matches_scenario, args=(scenario_wanted,))
    ]
    filtered_sources = sources[
        sources["scenario"].apply(matches_scenario, args=(scenario_wanted,))
    ]
    filtered_transformers = transformers[
        transformers["scenario"].apply(matches_scenario, args=(scenario_wanted,))
    ]
    filtered_storage = storage[
        storage["scenario"].apply(matches_scenario, args=(scenario_wanted,))
    ]

    components = (
        filtered_sinks["label"].tolist()
        + filtered_sources["label"].tolist()
        + filtered_transformers["label"].tolist()
        + filtered_storage["label"].tolist()
    )

    buses = (
        filtered_sinks["bus_in"].tolist()
        + filtered_sources["bus_out"].tolist()
        + filtered_transformers[
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
    buses_df = pd.DataFrame(data={"label": buses})
    return buses_df, components


buses, components = extract_components_and_buses_from_input_data(
    sinks, sources, transformers, storage, scenario
)

print("Adding the following buses to the energy system:")
print(buses)
# Create Bus objects from buses table

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

# TRANSFORMERS

if "conversion_orc" in components:
    row = transformers.loc[transformers.label == "conversion_orc"]
    if row.investment.item() == True:
        print(
            "Warning: Investment optimisation is not yet implemented for conversion_orc. It is treated as dispatch."
        )
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        print("epc for conversion_orc: ", epc)
        conversion_orc = solph.components.Transformer(
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
    elif row.investment.item() == False:
        conversion_orc = solph.components.Transformer(
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
    row = transformers.loc[transformers.label == "pyrolysis"]
    if row.investment.item() == True:
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        print("epc for pyrolysis: ", epc)
        pyrolysis = solph.components.Transformer(
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
    elif row.investment.item() == False:
        pyrolysis = solph.components.Transformer(
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
    row = transformers.loc[transformers.label == "combustor_hot"]
    if row.investment.item() == True:
        print(
            "Warning: Investment optimisation is not yet implemented for combustor_hot. It is treated as dispatch."
        )
        combustor_hot = solph.components.Transformer(
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
    elif row.investment.item() == False:
        combustor_hot = solph.components.Transformer(
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
