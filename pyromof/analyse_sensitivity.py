import os
import shutil
from functools import reduce
from pathlib import Path

from pyromof import preprocessing_functions, optimize, postprocessing
import pandas as pd

from pyromof.policies.implement_policies import implement_policies

def analyze_sensitivity():
    # Insert here the parameters. Only two decimal places are possible!
    parameters = {
        "component_type": "storage",  # must be plural
        "component": "syngas_storage",
        "variable": "capex",
        "min": 40,
        "max": 40,
        "step": 1,
    }

    # Select the scenario here:
    scenario = "stromflex_h2"

    # Definition of the time period
    data, time, scenario = preprocessing_functions.preprocessing_input_data.preprocess(
        "input_data.xlsx"
    )
    data = implement_policies(data, scenario)

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
    value_range = [
        x / 100
        for x in range(
            int(parameters["min"] * 100),
            int(parameters["max"] * 100) + int(parameters["step"] * 100),
            int(parameters["step"] * 100),
        )
    ]
    # Somewhat complicated workaround because "range" only accepts integers
    for parameter_value in value_range:
        print(parameter_value)
        df_name = parameters["component_type"]
        data[df_name].loc[
            data[df_name]["label"] == parameters["component"],
            parameters["variable"],
        ] = parameter_value

        # OPTIMIZATION
        es, om, investment, epcs = optimize.create_energysystem(
            META_INFO=META_INFO,
            data=data,
            time=time,
            scenario=scenario,
        )
        optimize.save_results(es, om, investment, epcs, META_INFO, DUMPING_SPACE, scenario, time)

        # POSTPROCESSING

        result_dfs = postprocessing.postprocess()

        postprocessing.check_scalar_costs_consistency(result_dfs["scalar_results"])

        result_dfs["scalar_results"].rename(columns={"value": parameter_value}, inplace=True)
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