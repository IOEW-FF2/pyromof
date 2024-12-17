from oemof import solph
import pandas as pd

import os
from pathlib import Path
from oemof.network.graph import create_nx_graph

ROOT_PATH = Path(__file__).parent

# Reading in the raw data
buses = pd.read_excel("input_data.xlsx", sheet_name = "buses")
profiles = pd.read_excel("input_data.xlsx", sheet_name = "profiles")
sinks = pd.read_excel("input_data.xlsx", sheet_name = "sink")
sources = pd.read_excel("input_data.xlsx", sheet_name = "source")
transformers = pd.read_excel("input_data.xlsx", sheet_name = "transformer")
storage = pd.read_excel("input_data.xlsx", sheet_name = "storage")

# Definition of the time period
time = pd.date_range("2023-01-02", periods=145, freq="h") # 145 Would also be possible

# Model definition
es = solph.EnergySystem(timeindex=time)

nodes = []
busd = {}

# Create Bus objects from buses table

for i, b in buses.iterrows():
    bus = solph.Bus(label=b["label"])
    nodes.append(bus)
    busd[b["label"]] = bus
    es.add(bus)


# Create other components

### SINKS
row = sinks.loc[sinks.label == "biochar_market", :]
biochar_market = solph.components.Sink(
    label = "biochar_market",
    inputs = {busd[row.bus.item()]: solph.Flow(variable_costs=row.variable_costs.item())}
)

row = sinks.loc[sinks.label == "co2_market", :]
co2_market = solph.components.Sink(
    label = "co2_market",
    inputs = {busd[row.bus.item()]: solph.Flow(variable_costs=row.variable_costs.item())}
)

row = sinks.loc[sinks.label == "electricity_grid", :]
electricity_grid = solph.components.Sink(
    label = "electricity_grid",
    inputs = {busd[row.bus.item()]: solph.Flow(variable_costs=row.variable_costs.item())}
)

row = sinks.loc[sinks.label == "heat_demand", :]
heat_demand = solph.components.Sink(
    label = "heat_demand",
    inputs = {busd[row.bus.item()]: solph.Flow(nominal_value=row.amount.item(), fix=profiles[row.profile.item()], variable_costs=row.variable_costs.item())}
)

row = sinks.loc[sinks.label == "heat_demand_with_orc", :]
heat_demand_with_orc = solph.components.Sink(
    label = "heat_demand_with_orc",
    inputs = {busd[row.bus.item()]: solph.Flow(nominal_value=row.amount.item(), fix=profiles[row.profile.item()], variable_costs=row.variable_costs.item())}
)

# TODO: b_heat_2 muss auch Input für heat_demand sein. Dazu muss die Tabellenstruktur verändert werden, um mehrere Inputs für die gleiche Senke zu erlauben.

### SOURCES
row = sources.loc[sources.label == "biomass", :]
biomass = solph.components.Source(
    label="biomass",
    outputs = {busd[row.bus_out.item()]: solph.Flow(nominal_value=row.amount.item(), variable_costs=row.variable_costs.item())}
)

row = sources.loc[sources.label == "heat_source", :]
heat_source = solph.components.Source(
    label="heat_source",
    outputs = {busd[row.bus_out.item()]: solph.Flow(variable_costs=row.variable_costs.item())}
)

### TRANSFORMER
row = transformers.loc[transformers.label == "conversion_bc"]
conversion_bc = solph.components.Transformer(
    label = "conversion_bc",
    inputs = {busd[row.bus_in_1.item()]: solph.Flow()},
    outputs = {busd[row.bus_out_1.item()]: solph.Flow(), busd[row.bus_out_2.item()]: solph.Flow()},
    conversion_factors = {busd[row.bus_in_1.item()]: row.eff_in_1.item(), busd[row.bus_out_1.item()]: row.eff_out_1.item(), busd[row.bus_out_2.item()]: row.eff_out_2.item()}
)

row = transformers.loc[transformers.label == "conversion_orc"]
conversion_orc = solph.components.Transformer(
    label = "conversion_orc",
    inputs = {busd[row.bus_in_1.item()]: solph.Flow()},
    outputs = {busd[row.bus_out_1.item()]: solph.Flow(), busd[row.bus_out_2.item()]: solph.Flow()},
    conversion_factors = {busd[row.bus_in_1.item()]: row.eff_in_1.item(), busd[row.bus_out_1.item()]: row.eff_out_1.item(), busd[row.bus_out_2.item()]: row.eff_out_2.item()}
)

row = transformers.loc[transformers.label == "pyrolysis"]
pyrolysis = solph.components.Transformer(
    label = "pyrolysis",
    inputs = {busd[row.bus_in_1.item()]: solph.Flow(), busd[row.bus_in_2.item()]: solph.Flow()},
    outputs = {busd[row.bus_out_1.item()]: solph.Flow(), busd[row.bus_out_2.item()]: solph.Flow()},
    conversion_factors = {busd[row.bus_in_1.item()]: row.eff_in_1.item(), busd[row.bus_in_2.item()]: row.eff_in_2.item(),
                          busd[row.bus_out_1.item()]: row.eff_out_1.item(), busd[row.bus_out_2.item()]: row.eff_out_2.item()}
)

# Add elements to the energy system

es.add(biochar_market, co2_market, electricity_grid, heat_demand, biomass, heat_source, conversion_bc, conversion_orc, pyrolysis, heat_demand_with_orc)
print("The model has been constructed.")

# Initialise the operational model
om = solph.Model(es)

# Store lp file for debugging
file_path = os.path.join(ROOT_PATH, "lp_file.lp")
om.write(file_path, io_options = {"symbolic_solver_labels": True})

# Solve the system
om.solve(solver="cbc")

graph = create_nx_graph(es, filename='es_graph.graphml')

# get results from the solved model
es.params = solph.processing.parameter_as_dict(es)
es.results = solph.processing.results(om)

# dump the EnergySystem
es.dump(dpath=ROOT_PATH, filename='es_dump.oemof')
print("The results have been saved.")