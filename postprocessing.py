import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import logging

from oemof.solph import (
    EnergySystem,
    processing,
    views,
)

logging.basicConfig(
    filename=os.path.join("meta_info", "logging.log"),
    format="%(asctime)s %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    encoding="utf-8",
    level=logging.INFO,
)


ROOT_PATH = Path(__file__).parent
RESULTS = os.path.join(ROOT_PATH, "results")
DUMPING_SPACE = os.path.join(ROOT_PATH, "dumping_space")

es = EnergySystem()
es.restore(DUMPING_SPACE, "es_dump.oemof")

logging.info("The EnergySystem is restored.")

# Meta-information could be assessed in es.results["meta"] to retreive the objective variable.

scalar_results = pd.DataFrame(columns=["variable", "type", "value"])


def add_items_to_scalar_results(
    dictionary: dict, type: str, scalar_results=scalar_results
):
    new_df = pd.DataFrame(
        {
            "variable": list(dictionary.keys()),
            "type": [type] * len(dictionary),
            "value": list(dictionary.values()),
        }
    )
    return pd.concat([scalar_results, new_df], ignore_index=True)


scalar_results = add_items_to_scalar_results(
    {"objective": es.results["meta"]["objective"]}, "objective [Euros]", scalar_results
)

es.results = es.results["main"]

nodes = [x for x in es.results.keys() if x[1] is None]  # This is only storage


def convert_result_sequences_to_df(results_data=es.results):
    results = processing.convert_keys_to_strings(results_data)
    flows = [x for x in results.keys() if x[1] is not None]
    df = pd.DataFrame(columns=flows)
    for flow in flows:
        df[flow] = results[flow]["sequences"]
    return df


# These are dictionaries with "sequences" as key and the relevant sequences for each node in a dataframe:
results_pyrolysis_energy = views.node(es.results, "conversion_orc")
results_pyrolysis_material = views.node(es.results, "conversion_bc")
results_pyrolysis = views.node(es.results, "pyrolysis")
results_heat_demand = views.node(es.results, "heat_demand")


def plot_figures_for(element: dict, filename):
    figure, axes = plt.subplots(figsize=(10, 5))
    element["sequences"].plot(ax=axes, kind="line", drawstyle="steps-post")
    plt.legend(
        loc="upper center",
        prop={"size": 8},
        bbox_to_anchor=(0.5, 1.25),
        ncol=2,
    )
    # labels = [element["sequences"].columns[i][0][0] for i in range(len(element["sequences"].columns))]
    # # Would be nice to shorten the labels, but it's not always the first element that is relevant.
    # This depends on whether the bus is an in- or outflow.
    labels = [
        element["sequences"].columns[i][0]
        for i in range(len(element["sequences"].columns))
    ]
    axes.legend(labels=labels)
    axes.set_ylabel("kWh")
    figure.subplots_adjust(top=0.8)
    figure.savefig(os.path.join(RESULTS, filename))
    element["sequences"].to_csv(os.path.join(RESULTS, filename + ".csv"))


plot_figures_for(results_pyrolysis_energy, "pyrolysis_outputs_energy.png")
plot_figures_for(results_pyrolysis_material, "pyrolysis_outputs_material.png")
plot_figures_for(results_pyrolysis, "pyrolysis.png")
plot_figures_for(results_heat_demand, "results_heat_demand.png")

# Multiply flow results data and variable costs for every time step to obtain optimal variable costs
# per flow per timestep

flows = convert_result_sequences_to_df(results_data=es.results)
flows.to_csv(os.path.join(RESULTS, "flows.csv"), sep=";")
flows = pd.read_csv(os.path.join(RESULTS, "flows.csv"), sep=";", index_col=0)
varc = pd.read_csv(
    os.path.join(DUMPING_SPACE, "variable_costs_from_model.csv"), sep=";", index_col=0
)
varc = varc.set_index(
    flows.index[:-1]
)  # -1 because the index in flows in one time step longer than the data

effective_variable_costs = pd.DataFrame(index=flows.index, columns=flows.columns)
for col in effective_variable_costs.columns:
    effective_variable_costs[col] = flows[col] * varc[col]
effective_variable_costs.to_csv(
    os.path.join(RESULTS, "effective_variable_costs.csv"), sep=";"
)

# Calculate sums of the effective variable costs and append them to the scalar
# results if they are not 0

sums = effective_variable_costs.sum(axis=0)
non_zero_dict = {index: value for index, value in sums.items() if value != 0}
scalar_results = add_items_to_scalar_results(
    non_zero_dict, "sum of variable costs [Euros]", scalar_results
)

# Calculate the sums of the flows and append them to the scalar results

sums = flows.sum(axis=0)
sums = sums.to_dict()
scalar_results = add_items_to_scalar_results(sums, "sum of flow [kWh]", scalar_results)

# Save scalar results when all are collected
scalar_results.to_csv(os.path.join(RESULTS, "scalar_results.csv"), sep=";")
