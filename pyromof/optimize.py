from oemof import solph
import pandas as pd

import os
import shutil
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
scenario = input("Which scenario shall be optimized? ")

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

# Save current input data version in the scenario folder
# (filtering them for the data used in the scenario would be better but is too much for now)
shutil.copy("input_data.xlsx", os.path.join(META_INFO, "input_data.xlsx"))

# Initiate an investment variable as False that will be overwritten
# with True if any component with investment is added.
# This information is required for the postprocessing.
investment = False

# Definition of the time period
time = pd.date_range("2023-01-02", periods=3, freq="h")

# Read in wacc for investment optimization
wacc = general.loc[general["item"] == "wacc", "value"].item()

# Initiate dict to store annuities
epcs = {}

# Model definition
es = solph.EnergySystem(timeindex=time)


def matches_scenario(scenario_to_check, scenario_wanted):
    """
    Checks wether the string "scenario to check" is either "all" or includes the "scenario_wanted".
    "scenario_wanted" should be the scenario to be optimized, and "scenario_to_check" a scenario field
    from the input data.
    """
    return scenario_to_check == "all" or scenario_wanted in scenario_to_check


def filter_input_data_by_scenario(sinks, sources, converters, storage, scenario_wanted):
    dfs = {
        "sinks": sinks,
        "sources": sources,
        "converters": converters,
        "storage": storage,
    }
    dfs = {
        name: df[df["scenario"].apply(matches_scenario, args=(scenario_wanted,))]
        for name, df in dfs.items()
    }
    return dfs["sinks"], dfs["sources"], dfs["converters"], dfs["storage"]


def extract_components_and_buses_from_input_data(
    sinks, sources, converters, storage, scenario_wanted
):
    """
    Takes the dfs from the input data sheets and the selected scenario and extracts
    (1) the components included in the scenario and (2) the buses which are connected
    to these components. The buses are returned as a dataframe with one column named
    "label" and the components are returned as a list.
    """

    # Create component list for the selected scenario
    components = (
        sinks["label"].tolist()
        + sources["label"].tolist()
        + converters["label"].tolist()
        + storage["label"].tolist()
    )

    # Create list of unique buses for the selected scenario
    buses = (
        sinks["bus_in"].tolist()
        + sources["bus_out"].tolist()
        + converters[["bus_in_1", "bus_in_2", "bus_out_1", "bus_out_2", "bus_out_3"]]
        .stack()
        .tolist()
        + storage[["bus_in", "bus_out"]].stack().tolist()
    )
    # Filter unique values
    buses = set(buses)
    # Convert back to list
    buses = list(buses)
    # Convert to dataframe
    buses_df = pd.DataFrame(data={"label": buses})
    return buses_df, components


sinks, sources, converters, storage = filter_input_data_by_scenario(
    sinks, sources, converters, storage, scenario
)
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
print(
    "Adding the following components to the energysystem (if they are all implemented in the code):"
)
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

if "oil_market" in components:
    row = sinks.loc[sinks.label == "oil_market", :]
    oil_market = solph.components.Sink(
        label="oil_market",
        inputs={
            busd[row.bus_in.item()]: solph.Flow(
                variable_costs=row.variable_costs.item(),
            )
        },
    )
    es.add(oil_market)

if "h2_market" in components:
    row = sinks.loc[sinks.label == "h2_market", :]
    h2_market = solph.components.Sink(
        label="h2_market",
        inputs={
            busd[row.bus_in.item()]: solph.Flow(
                variable_costs=row.variable_costs.item(),
            )
        },
    )
    es.add(h2_market)

if "torch" in components:
    row = sinks.loc[sinks.label == "torch", :]
    torch = solph.components.Sink(
        label="torch",
        inputs={
            busd[row.bus_in.item()]: solph.Flow(
                variable_costs=row.variable_costs.item(),
            )
        },
    )
    es.add(torch)

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

if "orc" in components:
    row = converters.loc[converters.label == "orc"]
    if row.investment.item() is True:
        investment = True
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        epcs["orc_invest to " + row.bus_out_1.item()] = epc
        print("epc for orc: ", epc)
        orc = solph.components.Converter(
            label="orc_invest",
            inputs={busd[row.bus_in_1.item()]: solph.Flow()},
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=solph.Investment(ep_costs=epc)
                ),
                busd[row.bus_out_2.item()]: solph.Flow(),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                busd[row.bus_out_2.item()]: row.eff_out_2.item(),
            },
        )
    elif row.investment.item() is False:
        orc = solph.components.Converter(
            label="orc",
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
    es.add(orc)

if "chp" in components:
    row = converters.loc[converters.label == "chp"]
    if row.investment.item() is True:
        investment = True
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        epcs["chp_invest to " + row.bus_out_1.item()] = epc
        print("epc for chp: ", epc)
        chp = solph.components.Converter(
            label="chp_invest",
            inputs={busd[row.bus_in_1.item()]: solph.Flow()},
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=solph.Investment(ep_costs=epc)
                ),
                busd[row.bus_out_2.item()]: solph.Flow(),
                busd[row.bus_out_3.item()]: solph.Flow(),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                busd[row.bus_out_3.item()]: row.eff_out_3.item(),
            },
        )
    elif row.investment.item() is False:
        chp = solph.components.Converter(
            label="chp",
            inputs={busd[row.bus_in_1.item()]: solph.Flow()},
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=row.capacity.item()
                ),
                busd[row.bus_out_2.item()]: solph.Flow(),
                busd[row.bus_out_3.item()]: solph.Flow(),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                busd[row.bus_out_3.item()]: row.eff_out_3.item(),
            },
        )
    es.add(chp)

if "power_to_heat" in components:
    row = converters.loc[converters.label == "power_to_heat"]
    if row.investment.item() is True:
        investment = True
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        epcs["power_to_heat_invest to " + row.bus_out_1.item()] = epc
        print("epc for power_to_heat: ", epc)
        power_to_heat = solph.components.Converter(
            label="power_to_heat_invest",
            inputs={busd[row.bus_in_1.item()]: solph.Flow()},
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=solph.Investment(ep_costs=epc)
                ),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
            },
        )
    elif row.investment.item() is False:
        power_to_heat = solph.components.Converter(
            label="power_to_heat",
            inputs={busd[row.bus_in_1.item()]: solph.Flow()},
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=row.capacity.item()
                ),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
            },
        )
    es.add(power_to_heat)

if "h2_filtration" in components:
    row = converters.loc[converters.label == "h2_filtration"]
    if row.investment.item() is True:
        investment = True
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        epcs["h2_filtration_invest to " + row.bus_out_1.item()] = epc
        print("epc for h2_filtration: ", epc)
        h2_filtration = solph.components.Converter(
            label="h2_filtration_invest",
            inputs={busd[row.bus_in_1.item()]: solph.Flow()},
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=solph.Investment(ep_costs=epc)
                ),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
            },
        )
    elif row.investment.item() is False:
        h2_filtration = solph.components.Converter(
            label="h2_filtration",
            inputs={busd[row.bus_in_1.item()]: solph.Flow()},
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=row.capacity.item()
                ),
            },
            conversion_factors={
                busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                busd[row.bus_out_1.item()]: row.eff_out_1.item(),
            },
        )
    es.add(h2_filtration)

if "pyrolysis" in components:
    row = converters.loc[converters.label == "pyrolysis"]
    if row.investment.item() is True:
        investment = True
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        epcs["pyrolysis_invest to " + row.bus_out_1.item()] = epc
        print("epc for pyrolysis: ", epc)
        pyrolysis = solph.components.Converter(
            label="pyrolysis_invest",
            inputs={
                busd[row.bus_in_1.item()]: solph.Flow(),
                busd[row.bus_in_2.item()]: solph.Flow(),
            },
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=solph.Investment(
                        ep_costs=epc, maximum=150
                    ),  # A maximum is required for linearization
                    # min=0.5,
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
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=row.capacity.item()
                    #                    nominal_value=1000,
                    #                    positive_gradient_limit=row.positive_gradient_limit.item(),
                    #                    min=0.5,
                    #                   # Only has an effect if the plant shuts down:
                    #                    nonconvex=solph.NonConvex(minimum_downtime=5, initial_status=1),
                    #
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
    es.add(pyrolysis)

if "combustor_hot" in components:
    row = converters.loc[converters.label == "combustor_hot"]
    if row.investment.item() is True:
        investment = True
        epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
        epcs["combustor_hot_invest to " + row.bus_out_1.item()] = epc
        print("epc for combustor_hot: ", epc)
        combustor_hot = solph.components.Converter(
            label="combustor_hot_invest",
            inputs={
                busd[row.bus_in_1.item()]: solph.Flow(),
            },
            outputs={
                busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_value=solph.Investment(ep_costs=epc)
                ),
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

if "combustor_cold" in components:
    row = converters.loc[converters.label == "combustor_cold"]
    combustor_cold = solph.components.Converter(
        label="combustor_cold",
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
    es.add(combustor_cold)

if "condensor" in components:
    row = converters.loc[converters.label == "condensor"]
    condensor = solph.components.Converter(
        label="condensor",
        inputs={
            busd[row.bus_in_1.item()]: solph.Flow(),
        },
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
    es.add(condensor)

if "biomass_dryer" in components:
    row = converters.loc[converters.label == "biomass_dryer"]
    biomass_dryer = solph.components.Converter(
        label="biomass_dryer",
        inputs={
            busd[row.bus_in_1.item()]: solph.Flow(),
            busd[row.bus_in_2.item()]: solph.Flow(),
        },
        outputs={
            busd[row.bus_out_1.item()]: solph.Flow(),
        },
        conversion_factors={
            busd[row.bus_in_1.item()]: row.eff_in_1.item(),
            busd[row.bus_in_2.item()]: row.eff_in_2.item(),
            busd[row.bus_out_1.item()]: row.eff_out_1.item(),
        },
    )
    es.add(biomass_dryer)


# STORAGE


def instantiate_storage(row, investment):
    """
    Instantiates the storage type provided in the given row of the dataframe "storage".
    The investment variable is set to True in case one of the storage types has
    investment optimization and is returned.
    """
    if row.investment is True:
        label = row.label + "_invest"
        epc_nominal_storage_capacity = economics.annuity(row.capex, row.lifetime, wacc)
        epcs[label + " to None"] = epc_nominal_storage_capacity
        print("epc for ", label, " : ", epc_nominal_storage_capacity)
        investment = True
        storage = solph.components.GenericStorage(
            label=label,
            inputs={
                busd[row.bus_in]: solph.Flow(),
            },  # The flows could also be constrained by a nominal capacity or variable costs.
            outputs={
                busd[row.bus_out]: solph.Flow(),
            },
            loss_rate=row.loss_rate,
            initial_storage_level=row.initial_storage_level,
            inflow_conversion_factor=row.inflow_conversion_factor,
            outflow_conversion_factor=row.outflow_conversion_factor,
            nominal_storage_capacity=solph.Investment(
                ep_costs=epc_nominal_storage_capacity
            ),
        )
    elif row.investment is False:
        storage = solph.components.GenericStorage(
            label=row.label,
            inputs={
                busd[row.bus_in]: solph.Flow(),
            },
            outputs={
                busd[row.bus_out]: solph.Flow(),
            },
            loss_rate=row.loss_rate,
            initial_storage_level=row.initial_storage_level,
            inflow_conversion_factor=row.inflow_conversion_factor,
            outflow_conversion_factor=row.outflow_conversion_factor,
            nominal_storage_capacity=row.nominal_storage_capacity,
        )
    es.add(storage)

    return investment


investment = storage.apply(instantiate_storage, investment=investment, axis=1)

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
# Use tool from Fraunhofer to create more useful network graph
if input("Visualize network in dash app? (yes/no) ") == "yes":
    from visualize_network import make_network, shownetwork

    network = make_network(es)
    shownetwork(network)

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

# Save the dictionary with ep_costs:
epcs = pd.DataFrame(epcs.items(), columns=["object", "value"])
epcs.to_csv(os.path.join(DUMPING_SPACE, "epcs_from_optimization.csv"), sep=";")

# dump the EnergySystem
es.dump(dpath=DUMPING_SPACE, filename="es_dump.oemof")
print("The results have been saved.")
