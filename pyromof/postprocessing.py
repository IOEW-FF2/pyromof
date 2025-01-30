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


ROOT_PATH = Path(__file__).parent.parent
RESULTS = os.path.join(ROOT_PATH, "results")
DUMPING_SPACE = os.path.join(ROOT_PATH, "dumping_space")


def add_items_to_scalar_results(
    dictionary: dict, type: str, scalar_results
):
    new_df = pd.DataFrame(
        {
            "variable": list(dictionary.keys()),
            "type": [type] * len(dictionary),
            "value": list(dictionary.values()),
        }
    )
    return pd.concat([scalar_results, new_df], ignore_index=True)



def convert_result_sequences_to_df(results_data):
    results = processing.convert_keys_to_strings(results_data)
    flows = [x for x in results.keys() if x[1] is not None]
    df_sequences = pd.DataFrame(columns=flows)
    for flow in flows:
        df_sequences[flow] = results[flow]["sequences"]
    df_scalars = pd.DataFrame(columns=flows)
    for flow in flows:
        df_scalars[flow] = results[flow]["scalars"]
    return df_sequences, df_scalars



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



def calculate_variable_costs_per_flow_per_timestep():
    '''
    This function takes the result sequences (flows per timestep) and the variable costs from csv files and
    multiplies them. The results are returned as a dataframe and stored in a csv file.
    '''
    sequences = pd.read_csv(os.path.join(RESULTS, "sequences.csv"), sep=";", index_col=0)
    varcosts = pd.read_csv(
        os.path.join(DUMPING_SPACE, "variable_costs_from_model.csv"), sep=";", index_col=0
    )
    varcosts = varcosts.set_index(
        sequences.index[:-1]
    )  # -1 because the index in flows in one time step longer than the data

    # Create a new dataframe with the same structure as the sequences dataframe to store the cost sequences
    effective_variable_costs = pd.DataFrame(
        index=sequences.index, columns=sequences.columns
    )
    # Calculate the effective variable costs by multiplying the sequences with the variable costs
    for col in effective_variable_costs.columns:
        effective_variable_costs[col] = sequences[col] * varcosts[col]
    # Save the result as csv
    effective_variable_costs.to_csv(
        os.path.join(RESULTS, "effective_variable_costs.csv"), sep=";"
    )
    return effective_variable_costs



def add_sums_to_scalar_results(effective_variable_costs, sequences, scalar_results):
    '''
    Calculate sums of the effective variable costs and append them to the scalar
    results if they are not 0
    '''
    sums = effective_variable_costs.sum(axis=0)
    non_zero_dict = {index: value for index, value in sums.items() if value != 0}
    scalar_results = add_items_to_scalar_results(
        non_zero_dict, "sum of variable costs [Euros]", scalar_results
    )

    # Calculate the sums of the flows and append them to the scalar results

    sums = sequences.sum(axis=0)
    sums = sums.to_dict()
    scalar_results = add_items_to_scalar_results(sums, "sum of flow [kWh]", scalar_results)

    return scalar_results

def add_investment_amount_to_scalar_results(investment:bool, scalars, scalar_results):
    # Extract non-NaN-values from the scalars df and append them to the scalar results
    if investment is True:
        scalars = scalars.dropna(axis=1)
        dict = {}
        for columnName, columnData in scalars.items():
            dict[columnName] = columnData["invest"]
        scalar_results = add_items_to_scalar_results(
            dict, "built capacity [kW]", scalar_results
        )
        # The unit here should be kWh per timestep. It is kW because the timesteps are hours.
        # Multiplied with the epc for pyrolysis, this yields the annuity for investment costs.
    return scalar_results

if __name__ == "__main__":
    
    es = EnergySystem()
    es.restore(DUMPING_SPACE, "es_dump.oemof")

    logging.info("The EnergySystem is restored.")

    # Read in the scenario and set investment variable
    scenario = es.results["scenario"]
    if "investment" in scenario:
        investment = True
    else:
        investment = False

    # Meta-information could be assessed in es.results["meta"] to retreive the objective variable.

    scalar_results = pd.DataFrame(columns=["variable", "type", "value"])

    scalar_results = add_items_to_scalar_results(
    {"objective": es.results["meta"]["objective"]}, "objective [Euros]", scalar_results
    )

    es.results = es.results["main"]

    nodes = [x for x in es.results.keys() if x[1] is None]  # This is only storage

    # These are dictionaries with "sequences" as key and the relevant sequences for each node in a dataframe:
    if investment is True:
        results_pyrolysis_energy = views.node(es.results, "conversion_orc_invest")
        results_pyrolysis = views.node(es.results, "pyrolysis_invest")
    else:
        results_pyrolysis_energy = views.node(es.results, "conversion_orc")
        results_pyrolysis = views.node(es.results, "pyrolysis")
    results_heat_demand = views.node(es.results, "heat_demand_ht")

    plot_figures_for(results_pyrolysis_energy, "pyrolysis_outputs_energy.png")
    plot_figures_for(results_pyrolysis, "pyrolysis.png")
    plot_figures_for(results_heat_demand, "results_heat_demand.png")

    sequences, scalars = convert_result_sequences_to_df(results_data=es.results)
    sequences.to_csv(os.path.join(RESULTS, "sequences.csv"), sep=";")

    effective_variable_costs = calculate_variable_costs_per_flow_per_timestep()
    scalar_results = add_sums_to_scalar_results(effective_variable_costs, sequences, scalar_results)
    scalar_results = add_investment_amount_to_scalar_results(investment, scalars, scalar_results)

    # Save scalar results when all are collected
    scalar_results.to_csv(os.path.join(RESULTS, "scalar_results.csv"), sep=";")