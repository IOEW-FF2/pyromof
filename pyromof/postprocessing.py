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


def add_sums_to_scalar_results(data, description, scalar_results):
    """
    Calculate sums of the data and append them to the scalar results if they are not 0.

    Args:
        data: DataFrame to sum (sequences or costs)
        description: Description of the data type for the results (e.g., "sum of flow [kWh]")
        scalar_results: Existing scalar results dataframe

    Returns:
        Updated scalar results dataframe
    """
    sums = data.sum(axis=0)
    dict = {index: value for index, value in sums.items()}
    scalar_results = add_items_to_scalar_results(dict, description, scalar_results)
    return scalar_results


def add_objective_to_scalar_results(results, scalar_results):
    scalar_results = add_items_to_scalar_results(
        {"objective": results["meta"]["objective"]},
        "objective [Euros]",
        scalar_results,
    )
    return scalar_results


def convert_result_sequences_to_df(results_data):
    """
    This function extracts all the sequences and all scalars from the flows
    from the results data and stores them in dataframes.
    Also captures additional columns like positive_gradient, biochar_status, etc.
    """
    results = processing.convert_keys_to_strings(results_data)
    flows = [x for x in results.keys() if x[1] != "None"]
    nodes = [x for x in results.keys() if x[1] == "None"]

    df_sequences = pd.DataFrame()
    df_additional_columns = pd.DataFrame()
    df_scalars = pd.DataFrame(columns=flows)
    df_storage_content = pd.DataFrame()

    for flow in flows:
        flow_name = " to ".join(flow)
        sequences_data = results[flow]["sequences"]

        # Add the flow column
        if "flow" in sequences_data.columns:
            df_sequences[flow_name] = sequences_data["flow"]

        # Capture all other columns (positive_gradient, biochar_status, etc.)
        additional_cols = [col for col in sequences_data.columns if col != "flow"]
        for col in additional_cols:
            col_name = f"{flow_name} ({col})"
            df_additional_columns[col_name] = sequences_data[col]

        df_scalars[flow_name] = results[flow]["scalars"]

    for node in nodes:
        node_name = " to ".join(node)
        df_scalars[node_name] = results[node]["scalars"]
        df_storage_content[node_name] = results[node]["sequences"]["storage_content"]

    return (
        df_sequences,
        df_scalars,
        df_storage_content,
        df_additional_columns,
    )


def calculate_variable_costs_per_flow_per_timestep(sequences, path_varcosts):
    """
    This function takes the result sequences (flows per timestep) and the variable costs from csv files and
    multiplies them. The results are returned as a dataframe.
    """
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


def add_investment_amount_to_scalar_results(
    investment: bool, scalars, scalar_results, DUMPING_SPACE
):
    """
    Extract non-NaN-values from the scalars df and append them to the scalar results.
    The scalars df should be composed of the scalars of all flows taken from the raw results
    data: results[flow]["scalars"]
    """
    scalars = scalars.dropna(axis=1, how="all")
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


def check_scalar_costs_consistency(scalar_results):
    """
    Check whether the sum of the monetary scalar results is equal to the objective variable
    and print a warning if not
    """
    print("Checking the completeness of the cost scalars")
    scalar_costs = helpers.filter_cost_items_from_scalar_data(scalar_results)
    objective = scalar_results.loc[
        scalar_results["variable"] == "objective", "value"
    ].item()
    sum = scalar_costs.value.sum().item()
    assert type(sum - objective) is type(
        0.1
    ), "The data types are not coherent, a consistency check is not possible."
    if objective - sum > 0.1:
        print(
            "Some cost or revenue scalars must be missing in the scalar results. "
            "The sum of the cost and revenue data is ",
            scalar_costs.value.sum(),
            "whereas the objective is ",
            objective,
            ". The difference of ",
            objective - sum,
            " will be added as undefined costs to the scalar results.",
        )
        scalar_results = add_items_to_scalar_results(
            {"unallocated costs": objective - sum},
            "sum of unallocated costs [Euros]",
            scalar_results,
        )
    return scalar_results


def postprocess(es, DUMPING_SPACE, investment):
    # Create an empty dataframe for the scalar results:

    scalar_results = pd.DataFrame(columns=["variable", "type", "value"])

    # From the meta information, only the objective value is interesting for the results.
    # Store this value in the scalar results remove the meta part from the results:

    sequences, scalars, storage_contents, additional_columns = (
        convert_result_sequences_to_df(results_data=es.results["main"])
    )

    effective_variable_costs = calculate_variable_costs_per_flow_per_timestep(
        sequences,
        os.path.join(DUMPING_SPACE, "variable_costs_from_model.csv"),
    )

    # Remove all columns from sequences were the column name does not start with "b_"
    # Because buses are balanced one column per bus is sufficient.
    sequences = sequences.loc[:, sequences.columns.str.startswith("b_")]

    ## Create scalar results
    scalar_results = add_objective_to_scalar_results(es.results, scalar_results)

    scalar_results = add_sums_to_scalar_results(
        sequences, "sum of flow [kWh]", scalar_results
    )
    scalar_results = add_sums_to_scalar_results(
        effective_variable_costs, "sum of variable costs [Euros]", scalar_results
    )
    if investment is True:
        scalar_results = add_investment_amount_to_scalar_results(
            investment, scalars, scalar_results, DUMPING_SPACE
        )

    return {
        "sequences": sequences,
        "storage_contents": storage_contents,
        "effective_variable_costs": effective_variable_costs,
        "scalar_results": scalar_results,
        "additional_columns": additional_columns,
    }


if __name__ == "__main__":

    general = pd.read_excel("input_data.xlsx", sheet_name="general")
    scenario = general.loc[general["label"] == "scenario", "value"].item()

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

    result_dfs = postprocess(es, DUMPING_SPACE, investment)

    result_dfs["scalar_results"] = check_scalar_costs_consistency(
        result_dfs["scalar_results"]
    )

    # Save all results
    result_dfs["effective_variable_costs"].to_csv(
        os.path.join(RESULTS, "effective_variable_costs.csv"), sep=";"
    )
    result_dfs["sequences"].to_csv(os.path.join(RESULTS, "sequences.csv"), sep=";")
    result_dfs["storage_contents"].to_csv(
        os.path.join(RESULTS, "storage_contents.csv"), sep=";"
    )
    result_dfs["scalar_results"].to_csv(
        os.path.join(RESULTS, "scalar_results.csv"), sep=";"
    )
    result_dfs["additional_columns"].to_csv(
        os.path.join(RESULTS, "additional_columns.csv"), sep=";"
    )
