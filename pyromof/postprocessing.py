import os
import pandas as pd
from pathlib import Path
from pyromof import helpers
from oemof.solph import (
    EnergySystem,
    processing,
)


def add_items_to_scalar_results(dictionary: dict, type: str, scalar_results):
    """
    This functions adds given data to an existing dataframe with scalar results.
    The existing dataframe must have the columns "variable", "type" and "value".
    The input dict must contain the variable and value for each item. The type
    must be valid for all items in the dictionary.
    """
    new_df = pd.DataFrame(
        {
            "variable": list(dictionary.keys()),
            # Insert the given type for all new rows:
            "type": [type] * len(dictionary),
            "value": list(dictionary.values()),
        }
    )
    return pd.concat([scalar_results, new_df], ignore_index=True)


def convert_result_sequences_to_df(results_data):
    """
    This function extracts all the sequences and all scalars from the flows
    from the results data and stores them in three dataframes: one for sequences,
    one for scalars, and a separate one for the storage content sequences.
    Sequences are saved with the flow names as columnnames and a datetime index.
    """
    results = processing.convert_keys_to_strings(results_data)
    flows = [x for x in results.keys() if x[1] != "None"]
    nodes = [x for x in results.keys() if x[1] == "None"]
    df_sequences = pd.DataFrame(columns=flows)
    df_scalars = pd.DataFrame(columns=flows)
    df_storage_content = pd.DataFrame()
    df_storage_losses = pd.DataFrame()
    for flow in flows:
        df_sequences[flow] = results[flow]["sequences"][
            "flow"
        ]  # Besides the "flow" column there can be columns "positive_gradient" etc.
        df_scalars[flow] = results[flow]["scalars"]
    for node in nodes:
        df_scalars[node] = results[node]["scalars"]
        df_storage_content[node] = results[node]["sequences"]["storage_content"]
    #       df_storage_losses[node] = results[node]["sequences"]["storage_losses"]
    #       Storage losses are stored in this format only in dispatch mode.
    for df in [df_sequences, df_scalars, df_storage_content, df_storage_losses]:
        df.columns = [" to ".join(x) for x in df.columns]
    return df_sequences, df_scalars, df_storage_content, df_storage_losses


def calculate_variable_costs_per_flow_per_timestep(path_sequences, path_varcosts):
    """
    This function takes the result sequences (flows per timestep) and the variable costs from csv files and
    multiplies them. The results are returned as a dataframe.
    """
    sequences = pd.read_csv(path_sequences, sep=";", index_col=0)
    varcosts = pd.read_csv(path_varcosts, sep=";", index_col=0)
    varcosts = varcosts.set_index(
        sequences.index[:-1]
    )  # -1 because the index in sequences in one time step longer than the data

    # Create a new dataframe with the same structure as the sequences dataframe to store the cost sequences
    effective_variable_costs = pd.DataFrame(
        index=sequences.index, columns=sequences.columns
    )
    # Calculate the effective variable costs by multiplying the sequences with the variable costs
    for col in effective_variable_costs.columns:
        effective_variable_costs[col] = sequences[col] * varcosts[col]
    return effective_variable_costs


def add_sums_to_scalar_results(effective_variable_costs, sequences, scalar_results):
    """
    Calculate sums of the effective variable costs and append them to the scalar
    results if they are not 0
    """
    sums = effective_variable_costs.sum(axis=0)
    non_zero_dict = {index: value for index, value in sums.items() if value != 0}
    scalar_results = add_items_to_scalar_results(
        non_zero_dict, "sum of variable costs [Euros]", scalar_results
    )

    # Calculate the sums of the flows and append them to the scalar results

    sums = sequences.sum(axis=0)
    sums = sums.to_dict()
    scalar_results = add_items_to_scalar_results(
        sums, "sum of flow [kWh]", scalar_results
    )

    return scalar_results


def add_investment_amount_to_scalar_results(investment: bool, scalars, scalar_results):
    """
    Extract non-NaN-values from the scalars df and append them to the scalar results.
    The scalars df should be composed of the scalars of all flows taken from the raw results
    data: results[flow]["scalars"]
    """
    scalars = scalars.dropna(axis=1)
    dict = {}
    for columnName, columnData in scalars.items():
        dict[columnName] = columnData["invest"]
    scalar_results = add_items_to_scalar_results(
        dict, "built capacity [kW]", scalar_results
    )
    epcs = pd.read_csv(
        os.path.join(DUMPING_SPACE, "epcs_from_optimization.csv"), sep=";"
    )
    investmentcost_dict = {}
    for key, value in dict.items():
        investmentcost_dict[key] = (
            dict[key] * epcs.loc[epcs["object"] == key, "value"].item()
        )
    scalar_results = add_items_to_scalar_results(
        investmentcost_dict,
        "equivalent periodical costs of investment [Euros]",
        scalar_results,
    )
    # The unit here should be kWh per timestep. It is kW because the timesteps are hours.
    return scalar_results


def check_scalar_costs_consistency(scalar_data):
    """
    Check whether the sum of the monetary scalar results is equal to the objective variable
    and print a warning if not
    """
    scalar_costs = helpers.filter_cost_items_from_scalar_data(scalar_results)
    objective = scalar_results.loc[
        scalar_results["variable"] == "objective", "value"
    ].item()
    if scalar_costs.value.sum() - objective > 0.1:
        print(
            "Warning: Some cost or revenue scalars must be missing in the scalar results. "
            "The sum of the cost and revenue data is ",
            scalar_costs.value.sum(),
            "whereas the objective is ",
            objective,
        )


if __name__ == "__main__":

    scenario = input("For which scenario shall the results be postprocessed? ")

    ROOT_PATH = Path(__file__).parent.parent
    SCENARIO_PATH = os.path.join(ROOT_PATH, "results", scenario)
    DUMPING_SPACE = os.path.join(SCENARIO_PATH, "dumping_space")
    # Create a results folder if it doesn't exist yet
    Path(os.path.join(SCENARIO_PATH, "results")).mkdir(exist_ok=True)
    RESULTS = os.path.join(SCENARIO_PATH, "results")

    es = EnergySystem()
    es.restore(DUMPING_SPACE, "es_dump.oemof")

    # Read in the scenario and set investment variable
    scenario, investment = helpers.retreive_scenario_from_results(es)

    # Create an empty dataframe for the scalar results:

    scalar_results = pd.DataFrame(columns=["variable", "type", "value"])

    # From the meta information, only the objective value is interesting for the results.
    # Store this value in the scalar results remove the meta part from the results:

    scalar_results = add_items_to_scalar_results(
        {"objective": es.results["meta"]["objective"]},
        "objective [Euros]",
        scalar_results,
    )

    es.results = es.results["main"]

    nodes = [x for x in es.results.keys() if x[1] is None]  # This is only storage

    sequences, scalars, storage_contents, storage_losses = (
        convert_result_sequences_to_df(results_data=es.results)
    )
    sequences.to_csv(os.path.join(RESULTS, "sequences.csv"), sep=";")
    storage_contents.to_csv(os.path.join(RESULTS, "storage_contents.csv"), sep=";")
    storage_losses.to_csv(os.path.join(RESULTS, "storage_losses.csv"), sep=";")

    effective_variable_costs = calculate_variable_costs_per_flow_per_timestep(
        os.path.join(RESULTS, "sequences.csv"),
        os.path.join(DUMPING_SPACE, "variable_costs_from_model.csv"),
    )
    # Save the result as csv
    effective_variable_costs.to_csv(
        os.path.join(RESULTS, "effective_variable_costs.csv"), sep=";"
    )
    scalar_results = add_sums_to_scalar_results(
        effective_variable_costs, sequences, scalar_results
    )
    if investment is True:
        scalar_results = add_investment_amount_to_scalar_results(
            investment, scalars, scalar_results
        )

    check_scalar_costs_consistency(scalar_results)

    # Save scalar results when all are collected
    scalar_results.to_csv(os.path.join(RESULTS, "scalar_results.csv"), sep=";")
