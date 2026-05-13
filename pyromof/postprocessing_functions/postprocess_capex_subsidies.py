import pandas as pd

from pyromof.postprocessing_functions.postprocess_policies_functions import (
    receive_pyrolysis_capex_data,
)
from pyromof.preprocessing_functions import implement_preprocessing_input_data_functions
from pyromof.preprocessing_functions.define_preprocessing_input_data_functions import (
    retrieve_scenario_from_input_data,
)


def postprocess_lump_sum_capex_subsidy(data):

    policies, _, biochar_output = receive_pyrolysis_capex_data(data)

    subsidy_per_biochar_ton = policies.loc[
        policies["policy"] == "Subsidy for pyrolysis investment costs", "value 1"
    ].item()
    total_subsidy = subsidy_per_biochar_ton * biochar_output
    total_subsidy = total_subsidy.round(1)
    return {"pyrolysis_capex_subsidy": total_subsidy}


def postprocess_percentage_capex_subsidy(data):
    policies, converters, biochar_output = receive_pyrolysis_capex_data(data)

    percentage_subsidy = (
        1
        / 100
        * policies.loc[
            policies["policy"] == "Percentage subsidy for pyrolysis investment costs", "value 1"
        ].values[0]
    )
    pyrolysis_capex = converters.loc[converters["label"] == "pyrolysis", "capex"].item()
    subsidy_per_biochar_ton = percentage_subsidy * pyrolysis_capex
    total_subsidy = subsidy_per_biochar_ton * biochar_output
    total_subsidy = total_subsidy.round(1)
    return {"pyrolysis_capex_subsidy": total_subsidy}


def lump_sum_storage_subsidy(data, subsidized_storage):

    scenario = retrieve_scenario_from_input_data(data["general"])
    file_path = f"./results/{scenario}/results/scalar_results.csv"
    storage_invest_results = pd.read_scv(file_path, sep=";")

    subsidy = (
        data["policies"].loc[data["subsidies"]["label"] == subsidized_storage, "value 1"].item()
    )
    storage_investment = storage_invest_results.loc[
        storage_invest_results["variable"] == subsidized_storage, "value"
    ].item()

    total_subsidy = (subsidy * storage_investment).round(1)

    return {subsidized_storage: total_subsidy}


def percentage_storage_subsidy(data, subsidized_storage):

    scenario = retrieve_scenario_from_input_data(data["general"])
    file_path = f"./results/{scenario}/results/scalar_results.csv"
    storage_invest_results = pd.read_scv(file_path, sep=";")
    storage_capex = (
        data["storage"].loc[data["storage"]["label"] == subsidized_storage, "capex"].item()
    )
    percentage_subsidy = (
        1
        / 100
        * data["policies"].loc[data["subsidies"]["label"] == subsidized_storage, "value 1"].item()
    )
    storage_investment = storage_invest_results.loc[
        storage_invest_results["variable"] == subsidized_storage, "value"
    ].item()
    subsidy_per_installed_capacity = percentage_subsidy * storage_capex
    total_subsidy = (subsidy_per_installed_capacity * storage_investment).round(1)

    return {subsidized_storage: total_subsidy}


if __name__ == "__main__":
    data, time, scenario = implement_preprocessing_input_data_functions.preprocess(
        "input_data.xlsx"
    )
    postprocess_lump_sum_capex_subsidy(scenario, data)
    # postprocess_percentage_capex_subsidy(scenario, data)
