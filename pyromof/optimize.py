from oemof import solph
import pandas as pd
import pyomo.environ as po
from typeguard import typechecked
from typing import Tuple

import os
import shutil
import numpy as np
from pathlib import Path
from oemof.network.graph import create_nx_graph
from oemof.tools import economics
from pyromof import helpers
from pyomo.environ import Constraint


@typechecked
def define_and_create_folders(ROOT_PATH: Path, scenario: str):
    RESULTS = Path(os.path.join(ROOT_PATH, "results"))
    # Create folder for the scenario within the results folder if it doesn't exist yet
    Path(os.path.join(RESULTS, scenario)).mkdir(exist_ok=True)
    SCENARIO_PATH = Path(os.path.join(RESULTS, scenario))
    # Create folders for meta_info and dumping_space
    Path(os.path.join(SCENARIO_PATH, "meta_info")).mkdir(exist_ok=True)
    META_INFO = Path(os.path.join(SCENARIO_PATH, "meta_info"))
    Path(os.path.join(SCENARIO_PATH, "dumping_space")).mkdir(exist_ok=True)
    DUMPING_SPACE = Path(os.path.join(SCENARIO_PATH, "dumping_space"))
    return SCENARIO_PATH, META_INFO, DUMPING_SPACE


def read_raw_data(relative_file_path):
    profiles = pd.read_excel(relative_file_path, sheet_name="profiles")
    sinks = pd.read_excel(relative_file_path, sheet_name="sink")
    sources = pd.read_excel(relative_file_path, sheet_name="source")
    converters = pd.read_excel(relative_file_path, sheet_name="converter")
    storage = pd.read_excel(relative_file_path, sheet_name="storage")
    general = pd.read_excel(relative_file_path, sheet_name="general")
    return profiles, sinks, sources, converters, storage, general


@typechecked
def matches_scenario(scenario_to_check: str, scenario_wanted: str) -> bool:
    """
    Checks wether the string "scenario to check" is either "all" or includes the "scenario_wanted".
    "scenario_wanted" should be the scenario to be optimized, and "scenario_to_check" a scenario field
    from the input data.
    """
    return scenario_to_check == "all" or scenario_wanted in scenario_to_check


@typechecked
def filter_input_data_by_scenario(
    sinks: pd.DataFrame,
    sources: pd.DataFrame,
    converters: pd.DataFrame,
    storage: pd.DataFrame,
    scenario_wanted: str,
):
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


@typechecked
def extract_components_and_buses_from_input_data(
    sinks: pd.DataFrame,
    sources: pd.DataFrame,
    converters: pd.DataFrame,
    storage: pd.DataFrame,
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


@typechecked
def create_energysystem(
    META_INFO,
    profiles: pd.DataFrame,
    sinks: pd.DataFrame,
    sources: pd.DataFrame,
    converters: pd.DataFrame,
    storage: pd.DataFrame,
    general: pd.DataFrame,
    time,
    scenario: str,
) -> Tuple[solph.EnergySystem, solph.Model, bool, dict]:
    # Initiate an investment variable as False that will be overwritten
    # with True if any component with investment is added.
    # This information is required for the postprocessing.
    investment = False

    # Read in wacc for investment optimization
    wacc = general.loc[general["label"] == "wacc", "value"].item()

    # Initiate dict to store annuities
    epcs = {}

    # Model definition
    es = solph.EnergySystem(timeindex=time)

    sinks, sources, converters, storage = filter_input_data_by_scenario(
        sinks, sources, converters, storage, scenario
    )
    buses, components = extract_components_and_buses_from_input_data(
        sinks, sources, converters, storage
    )

    buses.loc[len(buses.index)] = ["b_valuable_biochar"]
    buses.loc[len(buses.index)] = ["b_chp_cap"]
    
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
    
    def get_value_or_profile(row, column_name, profiles):
        value = row[column_name].item()
        return profiles[value] if isinstance(value, str) else value
    
    # SINKS
    if "biochar_market" in components:
        row = sinks.loc[sinks.label == "biochar_market", :]
        pyrolysis_row = converters.loc[converters.label == "pyrolysis"]
        if pyrolysis_row.investment.item() is True:  
            biochar_market = solph.components.Sink(
                label="biochar_market",
                inputs={
                    busd[row.bus_in.item()]: solph.Flow(
                        variable_costs=row.variable_costs.item()
                    )
                },
            )
        else:
            biochar_market = solph.components.Sink(
                label="biochar_market",
                inputs={
                    busd["b_valuable_biochar"]: solph.Flow(
                        variable_costs=row.variable_costs.item()
                    ),
                },
            )
        es.add(biochar_market)

    if "co2_market" in components:
        row = sinks.loc[sinks.label == "co2_market", :]
        co2_market = solph.components.Sink(
            label="co2_market",
            inputs={
                busd[row.bus_in.item()]: solph.Flow(
                    # nominal_capacity=row.nominal_capacity.item(),
                    # min=row["min"].item(),
                    # max=row["max"].item(),
                    variable_costs=row.variable_costs.item(),
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
                    nominal_capacity=row.nominal_capacity.item(),
                    min= get_value_or_profile(row, "min", profiles),
                    max= get_value_or_profile(row, "max", profiles),
                    variable_costs=get_value_or_profile(row, "variable_costs", profiles),
                )
            },
        )
        es.add(electricity_grid)

    if "heat_demand_mt" in components:
        row = sinks.loc[sinks.label == "heat_demand_mt", :]
        heat_demand_ht = solph.components.Sink(
            label="heat_demand_mt",
            inputs={
                busd[row.bus_in.item()]: solph.Flow(
                    nominal_capacity=row.nominal_capacity.item(),
                    min= get_value_or_profile(row, "min", profiles),
                    max= get_value_or_profile(row, "max", profiles),
                    variable_costs=get_value_or_profile(row, "variable_costs", profiles),
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
                    nominal_capacity=row.nominal_capacity.item(),
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

    if "heat_lt_excess" in components:
        row = sinks.loc[sinks.label == "heat_lt_excess", :]
        heat_lt_excess = solph.components.Sink(
            label="heat_lt_excess",
            inputs={
                busd[row.bus_in.item()]: solph.Flow(
                    variable_costs=row.variable_costs.item(),
                )
            },
        )
        es.add(heat_lt_excess)

    # SOURCES
    if "biomass" in components:
        row = sources.loc[sources.label == "biomass", :]
        biomass = solph.components.Source(
            label="biomass",
            outputs={
                busd[row.bus_out.item()]: solph.Flow(
                    nominal_capacity=row.nominal_capacity.item(),
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
                        nominal_capacity=solph.Investment(ep_costs=epc)
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
        # The chp can convert either hot or cold syngas. Because a single component which
        # uses either one input or the other doesn't exist, this is simulated with two chps.
        # For investment optimization, the two chps flow into one investment component instead
        # of a separate investment in both.
        row = converters.loc[converters.label == "chp"]
        if row.investment.item() is True:
            investment = True
            epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
            epcs["b_chp_cap to chp_to_out1"] = epc
            print("epc for chp: ", epc)
            # Create chp for hot gas with b_chp_cap instead of first output
            chp_hot = solph.components.Converter(
                label="chp_hot_invest",
                inputs={busd["b_syngas_hot"]: solph.Flow()},
                outputs={
                    busd["b_chp_cap"]: solph.Flow(),
                    busd[row.bus_out_2.item()]: solph.Flow(),
                    busd[row.bus_out_3.item()]: solph.Flow(),
                },
                conversion_factors={
                    busd["b_syngas_hot"]: row.eff_in_1.item(),
                    busd["b_chp_cap"]: row.eff_out_1.item(),
                    busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                    busd[row.bus_out_3.item()]: row.eff_out_3.item(),
                },
            )
            # Create chp for cold gas with b_chp_cap instead of first output
            chp_cold = solph.components.Converter(
                label="chp_cold_invest",
                inputs={busd["b_syngas_cold"]: solph.Flow()},
                outputs={
                    busd["b_chp_cap"]: solph.Flow(),
                    busd[row.bus_out_2.item()]: solph.Flow(),
                    busd[row.bus_out_3.item()]: solph.Flow(),
                },
                conversion_factors={
                    busd["b_syngas_cold"]: row.eff_in_1.item(),
                    busd["b_chp_cap"]: row.eff_out_1.item(),
                    busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                    busd[row.bus_out_3.item()]: row.eff_out_3.item(),
                },
            )
            # Create a virtual converter with investment that collects the first outputs
            # from chp_hot and chp_cold and converts them into the actual first output
            chp_to_out1 = solph.components.Converter(
                label="chp_to_out1",
                inputs={
                    busd["b_chp_cap"]: solph.Flow(
                        nominal_capacity=solph.Investment(
                        ep_costs=epc, existing=row.existing.item()
                        ),
                    ),
                },
                outputs={
                    busd[row.bus_out_1.item()]: solph.Flow(),
                },
                conversion_factors={
                    busd["b_chp_cap"]: 1,
                    busd[row.bus_out_1.item()]: 1,
                },
            )
            es.add(chp_hot, chp_cold, chp_to_out1)

        elif row.investment.item() is False:
            # Create chp for hot gas
            chp_hot = solph.components.Converter(
                label="chp_hot_invest",
                inputs={busd["b_syngas_hot"]: solph.Flow()},
                outputs={
                    busd[row.bus_out_1.item()]: solph.Flow(
                        nominal_capacity=row.nominal_capacity.item()
                    ),
                    busd[row.bus_out_2.item()]: solph.Flow(),
                    busd[row.bus_out_3.item()]: solph.Flow(),
                },
                conversion_factors={
                    busd["b_syngas_hot"]: row.eff_in_1.item(),
                    busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                    busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                    busd[row.bus_out_3.item()]: row.eff_out_3.item(),
                },
            )
            # Create chp for cold gas with b_chp_cap instead of first output
            chp_cold = solph.components.Converter(
                label="chp_cold_invest",
                inputs={busd["b_syngas_cold"]: solph.Flow()},
                outputs={
                    busd[row.bus_out_1.item()]: solph.Flow(
                        nominal_capacity=row.nominal_capacity.item()
                    ),
                    busd[row.bus_out_2.item()]: solph.Flow(),
                    busd[row.bus_out_3.item()]: solph.Flow(),
                },
                conversion_factors={
                    busd["b_syngas_cold"]: row.eff_in_1.item(),
                    busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                    busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                    busd[row.bus_out_3.item()]: row.eff_out_3.item(),
                },
            )
            es.add(chp_hot, chp_cold)

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
                        nominal_capacity=solph.Investment(ep_costs=epc)
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
                        nominal_capacity=row.nominal_capacity.item()
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
                        nominal_capacity=solph.Investment(ep_costs=epc)
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
                        nominal_capacity=row.nominal_capacity.item()
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
                        min=row.min_load_share.item(),  # Minimal load
                        max=1,  # A maximum is required for linearization
                        # positive_gradient_limit=row.positive_gradient_limit.item(),
                        # Apparently a positive gradient limit isn't possible in investment
                        # optimization. If it is activated, nominal_capacity becomes a NoneType object.
                        nonconvex=solph.NonConvex(
                            startup_costs=row.startup_costs.item(),
                            # minimum_downtime=int(row.minimum_downtime.item()),
                            initial_status=1,
                        ),
                        nominal_capacity=solph.Investment(
                            ep_costs=epc,
                            maximum=row.maximum.item(),  # necessary for linearization
                            existing=row.existing.item(),
                        ),
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
            print(row.nominal_capacity.item())
            pyrolysis = solph.components.Converter(
                label="pyrolysis",
                inputs={
                    busd[row.bus_in_1.item()]: solph.Flow(),
                    busd[row.bus_in_2.item()]: solph.Flow(),
                },
                outputs={
                    busd[row.bus_out_1.item()]: solph.Flow(
                        nominal_capacity=row.nominal_capacity.item(),
                        positive_gradient_limit=row.positive_gradient_limit.item(),
                        # min=row.min_load_share.item(),
                        max=1,
                        nonconvex=solph.NonConvex(
                            minimum_downtime=int(row.minimum_downtime.item()),
                            initial_status=1,
                        ),
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
            # Add a PiecewiseLinearTransformer which consumes biochar if little is produced (i.e. it has lower quality)
            cap = row.nominal_capacity.item()
            threshold = row.min_load_share.item()
            breakpoints = np.array([0, 0.2*cap, 0.3*cap, 0.4*cap, cap])
            x0 = 0.3*cap
            x1 = 0.4*cap
            m = x1 / (x1 - x0)
            rates = np.array([0.0, 0.0, m, 1.0])

            # Calculate function values at breakpoints
            values = [0.0]
            for i in range(len(rates)):
                dx = breakpoints[i+1] - breakpoints[i]
                values.append(values[-1] + rates[i] * dx)
            values = np.array(values)
            # values = np.array([0,0,0,0.4*cap,cap])
            print(values)

            def conversion_function(x):
                return np.interp(x, breakpoints, values)

            biochar_valuator = solph.components.experimental.PiecewiseLinearConverter(
                label="biochar_valuator",
                inputs={busd[row.bus_out_1.item()]: solph.Flow(
                    nominal_capacity=row.nominal_capacity.item(),
                    variable_costs=0
                )},
                outputs={busd["b_valuable_biochar"]: solph.Flow()},
                in_breakpoints=[0, cap * 0.2, cap*0.4, cap*0.6,
                            cap*0.8, cap],

                conversion_function=lambda x: conversion_function(x),
                pw_repn='CC'
            )
            es.add(biochar_valuator)
        es.add(pyrolysis)

    if "heat_exchanger" in components:
        row = converters.loc[converters.label == "heat_exchanger"]
        if row.investment.item() is True:
            investment = True
            epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
            epcs["heat_exchanger_invest to " + row.bus_out_1.item()] = epc
            print("epc for heat_exchanger: ", epc)
            heat_exchanger = solph.components.Converter(
                label="heat_exchanger_invest",
                inputs={
                    busd[row.bus_in_1.item()]: solph.Flow(),
                },
                outputs={
                    busd[row.bus_out_1.item()]: solph.Flow(
                        nominal_capacity=solph.Investment(ep_costs=epc)
                    ),
                },
                conversion_factors={
                    busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                    busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                },
            )
        elif row.investment.item() is False:
            heat_exchanger = solph.components.Converter(
                label="heat_exchanger",
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
        es.add(heat_exchanger)  

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
                        nominal_capacity=solph.Investment(ep_costs=epc)
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
        if row.investment.item() is True:
            investment = True
            epc = economics.annuity(row.capex.item(), row.lifetime.item(), wacc)
            epcs["condensor_invest to " + row.bus_out_1.item()] = epc
            print("epc for condensor: ", epc)
            condensor = solph.components.Converter(
                label="condensor_invest",
                inputs={
                    busd[row.bus_in_1.item()]: solph.Flow(),
                },
                outputs={
                    busd[row.bus_out_1.item()]: solph.Flow(nominal_capacity=solph.Investment(ep_costs=epc)), # cold syngas
                    busd[row.bus_out_2.item()]: solph.Flow(), # heat
                    busd[row.bus_out_3.item()]: solph.Flow(), # oil
                },
                conversion_factors={
                    busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                    busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                    busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                    busd[row.bus_out_3.item()]: row.eff_out_3.item(),
                },
            )
        elif row.investment.item() is False:
            condensor = solph.components.Converter(
                label="condensor",
                inputs={
                    busd[row.bus_in_1.item()]: solph.Flow(),
                },
                outputs={
                    busd[row.bus_out_1.item()]: solph.Flow(), # cold syngas
                    busd[row.bus_out_2.item()]: solph.Flow(), # heat
                    busd[row.bus_out_3.item()]: solph.Flow(), # oil
                },
                conversion_factors={
                    busd[row.bus_in_1.item()]: row.eff_in_1.item(),
                    busd[row.bus_out_1.item()]: row.eff_out_1.item(),
                    busd[row.bus_out_2.item()]: row.eff_out_2.item(),
                    busd[row.bus_out_3.item()]: row.eff_out_3.item(),
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
            epc_nominal_storage_capacity = economics.annuity(
                row.capex, row.lifetime, wacc
            )
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

    if not storage.empty:
        investment = storage.apply(
            lambda row: instantiate_storage(row, investment=investment), axis=1
        ).any()
        investment = bool(
            investment
        )  # Necessary because the function returns numpy.bool
        # which is different from bool and therefore creates a typeguard error.

    

    # Initialise the operational model
    om = solph.Model(es)

    print("The model has been constructed.")


    if "pyrolysis" in components:
        print("Creating costum constraints for pyrolysis")
        row = converters.loc[converters.label == "pyrolysis"]
        
        pyrolysis_component = pyrolysis
        bus_out_1 = busd[row.bus_out_1.item()]
        bus_out_2 = busd[row.bus_out_2.item()]
        eff_out_1 = row.eff_out_1.item()


        def tradeoff_bounds_lower(om, t):
            out1 = om.flow[pyrolysis_component, bus_out_1, t]
            out2 = om.flow[pyrolysis_component, bus_out_2, t]
            min_ratio = (
                eff_out_1 + eff_out_1 * row.out_1_max_decrease.item()
            ) / (
                row.eff_out_2.item()
                + row.eff_out_2.item() * row.out_2_corresponding_increase.item()
            )
            # Only enforce when biochar is active
            return out1 >= min_ratio * out2

        def tradeoff_bounds_upper(om, t):
            out1 = om.flow[pyrolysis_component, bus_out_1, t]
            out2 = om.flow[pyrolysis_component, bus_out_2, t]
            max_ratio = eff_out_1 / row.eff_out_2.item()
            return out1 <= max_ratio * out2
        

        om.tradeoff_lower_constraint = Constraint(om.TIMESTEPS, rule=tradeoff_bounds_lower)
        om.tradeoff_upper_constraint = Constraint(om.TIMESTEPS, rule=tradeoff_bounds_upper)

    # Tell the model to get the dual variables when solving
    # om.receive_duals()

    # Store lp file for debugging
    file_path = os.path.join(META_INFO, "lp_file.lp")
    om.write(file_path, io_options={"symbolic_solver_labels": True})

    # Solve the system
    results = om.solve(solver="cbc")

    # Check solver status
    from pyomo.opt import SolverStatus, TerminationCondition
    if results.solver.status == SolverStatus.error or results.solver.termination_condition == TerminationCondition.infeasible:
        print("\n=== MODEL IS INFEASIBLE ===")
        print(f"Solver Status: {results.solver.status}")
        print(f"Termination Condition: {results.solver.termination_condition}")
        
        # Find conflicting constraints
        print("\n=== CONFLICTING CONSTRAINTS ===")
        infeasible_constraints = []
        for constraint in om.component_objects(Constraint):
            for index in constraint:
                try:
                    c = constraint[index]
                    if c.slack() is None or abs(c.slack()) < 1e-6:
                        infeasible_constraints.append({
                            'name': f"{constraint.name}[{index}]",
                            'lower': c.lower(),
                            'body': c.body(),
                            'upper': c.upper(),
                        })
                except:
                    pass
        
        # Print top 20 conflicting constraints
        for i, constr in enumerate(sorted(infeasible_constraints, key=lambda x: str(x['name']))[:20]):
            print(f"{i+1}. {constr['name']}: {constr['lower']} <= {constr['body']} <= {constr['upper']}")
    
    elif results.solver.termination_condition == TerminationCondition.optimal:
        print("\n=== MODEL SOLVED SUCCESSFULLY ===")
    
    return es, om, investment, epcs


def visualize_network_in_dash(es: solph.EnergySystem):
    if input("Visualize network in dash app? (yes/no) ") == "yes":
        from visualize_network import make_network, shownetwork

        network = make_network(es)
        shownetwork(network)


@typechecked
def save_results(
    es: solph.EnergySystem,
    om: solph.Model,
    investment: bool,
    epcs: dict,
    META_INFO: Path,
    DUMPING_SPACE: Path,
    scenario: str,
    time: pd.date_range,
):
    # Save model structure as a graph in the graphml format. Can be opened e.g. in Gephi.
    filename = os.path.join(META_INFO, "es_graph.graphml")
    create_nx_graph(es, filename=filename)
    # Use tool from Fraunhofer to create more useful network graph

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
        series = list([b for a, b in flows.items() if a == col][0].variable_costs)
        df[col] = series[: len(time) - 1]
    variable_costs = helpers.convert_tuple_columnnames_to_strings(df)
    variable_costs.to_csv(
        os.path.join(DUMPING_SPACE, "variable_costs_from_model.csv"), sep=";"
    )

    # Save the dictionary with ep_costs:
    epcs_df = pd.DataFrame(epcs.items(), columns=["object", "value"])
    epcs_df.to_csv(os.path.join(DUMPING_SPACE, "epcs_from_optimization.csv"), sep=";")

    # dump the EnergySystem
    es.dump(dpath=DUMPING_SPACE, filename="es_dump.oemof")
    print("The results have been saved.")


if __name__ == "__main__":
    profiles, sinks, sources, converters, storage, general = read_raw_data(
        "input_data.xlsx"
    )
    # scenario = input("Which scenario shall be optimized? ")
    scenario = "stromflex_h2"
    # Definition of the time period
    time = pd.date_range(
        start="2025-01-01 00:00", end="2025-01-08 05:00", freq="h", inclusive="both"
    )

    SCENARIO_PATH, META_INFO, DUMPING_SPACE = define_and_create_folders(
        Path(__file__).parent.parent, scenario
    )
    # Save current input data version in the scenario folder
    # (filtering them for the data used in the scenario would be better but is too much for now)
    shutil.copy("input_data.xlsx", os.path.join(META_INFO, "input_data.xlsx"))

    es, om, investment, epcs = create_energysystem(
        META_INFO=META_INFO,
        profiles=profiles,
        sinks=sinks,
        sources=sources,
        converters=converters,
        storage=storage,
        general=general,
        time=time,
        scenario=scenario,
    )
    visualize_network_in_dash(es)
    save_results(es, om, investment, epcs, META_INFO, DUMPING_SPACE, scenario, time)
