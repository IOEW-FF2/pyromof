import os
import shutil
from pathlib import Path
from functools import reduce
import pandas as pd
import optimize
import postprocessing


if __name__ == "__main__":

    # Insert here the parameters. Only two decimal places are possible!
    parameters = {
        "component_type": "sources",  # must be plural
        "component": "heat_source",
        "variable": "variable_costs",
        "min": 0.1,
        "max": 1000.1,
        "step": 100,
    }

    # scenario = input("For which scenario shall the sensitivity be analyzed? ")
    scenario = "stromflex_h2"

    # Definition of the time period
    time = pd.date_range(
        start="2023-01-02", end="2023-01-03", freq="h", inclusive="both"
    )

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

    # These folders will be deleted again in the end
    # Create folders for meta_info and dumping_space
    Path(os.path.join(THIS_SENSITIVITY, "meta_info")).mkdir(exist_ok=True)
    META_INFO = Path(os.path.join(THIS_SENSITIVITY, "meta_info"))
    Path(os.path.join(THIS_SENSITIVITY, "dumping_space")).mkdir(exist_ok=True)
    DUMPING_SPACE = Path(os.path.join(THIS_SENSITIVITY, "dumping_space"))

    # Loop over the steps below, changing the sensitivity parameter in the raw data each time
    all_dfs = []
    range = [
        x / 100
        for x in range(
            int(parameters["min"] * 100),
            int(parameters["max"] * 100) + int(parameters["step"] * 100),
            int(parameters["step"] * 100),
        )
    ]
    # Somewhat complicated workaround because "range" only accepts integers
    for parameter_value in range:
        print(parameter_value)
        df_name = parameters["component_type"]
        input_data[df_name].loc[
            input_data[df_name]["label"] == parameters["component"],
            parameters["variable"],
        ] = parameter_value

        # OPTIMIZATION
        # TODO: Use dict for input data everywhere instead of this loose list of dfs
        es, om, investment, epcs = optimize.create_energysystem(
            META_INFO=META_INFO,
            profiles=input_data["profiles"],
            sinks=input_data["sinks"],
            sources=input_data["sources"],
            converters=input_data["converters"],
            storage=input_data["storage"],
            general=input_data["general"],
            time=time,
            scenario=scenario,
        )
        optimize.save_results(
            es, om, investment, epcs, META_INFO, DUMPING_SPACE, scenario
        )

        # POSTPROCESSING

        result_dfs = postprocessing.postprocess(es, DUMPING_SPACE, investment)

        postprocessing.check_scalar_costs_consistency(result_dfs["scalar_results"])

        result_dfs["scalar_results"].rename(
            columns={"value": parameter_value}, inplace=True
        )
        print(result_dfs["scalar_results"])

        all_dfs.append(result_dfs["scalar_results"])

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
