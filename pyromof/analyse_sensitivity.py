import os
import shutil
from pathlib import Path
from functools import reduce
import pandas as pd
import optimize
import postprocessing


if __name__ == "__main__":

    parameters = {
        "component_type": "sinks",
        "component": "biochar_market",
        "variable": "variable_costs",
        "min": -1000,
        "max": 0,
        "step": 200,
    }

    # scenario = input("For which scenario shall the results be postprocessed? ")
    scenario = "minimalexample"

    profiles, sinks, sources, converters, storage, general = optimize.read_raw_data(
        "input_data.xlsx"
    )
    input_data = {
        "profiles": profiles,
        "sinks": sinks,
        "sources": sources,
        "converters": converters,
        "storage": storage,
        "general": general,
    }

    ROOT_PATH = Path(__file__).parent.parent
    SCENARIO_PATH = os.path.join(ROOT_PATH, "results", scenario)
    RESULTS = os.path.join(SCENARIO_PATH, "results")
    parameter_name = parameters["component"] + "_" + parameters["variable"]
    print(parameter_name)
    Path(os.path.join(RESULTS, "sensitivity")).mkdir(exist_ok=True)
    Path(os.path.join(RESULTS, "sensitivity", parameter_name)).mkdir(exist_ok=True)
    THIS_SENSITIVITY = Path(os.path.join(RESULTS, "sensitivity", parameter_name))

    # Definition of the time period
    time = pd.date_range(
        start="2023-01-02", end="2023-01-03", freq="h", inclusive="both"
    )

    # These folders will be deleted again in the end
    # Create folders for meta_info and dumping_space
    Path(os.path.join(THIS_SENSITIVITY, "meta_info")).mkdir(exist_ok=True)
    META_INFO = Path(os.path.join(THIS_SENSITIVITY, "meta_info"))
    Path(os.path.join(THIS_SENSITIVITY, "dumping_space")).mkdir(exist_ok=True)
    DUMPING_SPACE = Path(os.path.join(THIS_SENSITIVITY, "dumping_space"))

    # Loop over the steps below, changing the sensitivity parameter in the raw data each time
    all_dfs = []
    for parameter_value in range(
        parameters["min"], parameters["max"] + parameters["step"], parameters["step"]
    ):
        print(parameter_value)
        df_name = parameters["component_type"]
        input_data[df_name].loc[
            input_data[df_name]["label"] == parameters["component"],
            parameters["variable"],
        ] = parameter_value

        # OPTIMIZATION
        es, om, investment, epcs = optimize.create_energysystem(
            META_INFO,
            profiles,
            sinks,
            sources,
            converters,
            storage,
            general,
            time,
            scenario,
        )
        optimize.save_results(
            es, om, investment, epcs, META_INFO, DUMPING_SPACE, scenario
        )

        # POSTPROCESSING

        # Create an empty dataframe for the scalar results:
        scalar_results = pd.DataFrame(columns=["variable", "type", "value"])

        # From the meta information, only the objective value is interesting for the results.
        # Store this value in the scalar results remove the meta part from the results:

        scalar_results = postprocessing.add_items_to_scalar_results(
            {"objective": es.results["meta"]["objective"]},
            "objective [Euros]",
            scalar_results,
        )

        es.results = es.results["main"]

        nodes = [x for x in es.results.keys() if x[1] is None]  # This is only storage

        sequences, scalars, storage_contents, storage_losses = (
            postprocessing.convert_result_sequences_to_df(results_data=es.results)
        )

        effective_variable_costs = (
            postprocessing.calculate_variable_costs_per_flow_per_timestep(
                sequences,
                os.path.join(DUMPING_SPACE, "variable_costs_from_model.csv"),
            )
        )

        scalar_results = postprocessing.add_sums_to_scalar_results(
            effective_variable_costs, sequences, scalar_results
        )
        if investment is True:
            scalar_results = postprocessing.add_investment_amount_to_scalar_results(
                investment, scalars, scalar_results, DUMPING_SPACE
            )

        postprocessing.check_scalar_costs_consistency(scalar_results)

        scalar_results.rename(columns={"value": parameter_value}, inplace=True)
        print(scalar_results)

        all_dfs.append(scalar_results)

    merged_df = reduce(
        lambda left, right: pd.merge(left, right, on=["variable", "type"], how="outer"),
        all_dfs,
    )
    # Save scalar results when all are collected
    merged_df.to_csv(
        os.path.join(THIS_SENSITIVITY, "scalar_results_" + parameter_name + ".csv"),
        sep=";",
    )

    # Delete folders dumping space and meta info
    shutil.rmtree(DUMPING_SPACE)
    shutil.rmtree(META_INFO)
