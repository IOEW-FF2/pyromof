import pandas as pd

from pyromof.preprocessing_functions import implement_preprocessing_input_data_functions
from pyromof.preprocessing_functions.define_preprocessing_input_data_functions import (
    retrieve_scenario_from_input_data,
)


def receive_biochar_output(data):

    investment = (
        data["converters"].loc[data["converters"]["label"] == "pyrolysis", "investment"].values[0]
    )

    if not investment:
        biochar_output = (
            8.76
            * data["converters"]
            .loc[data["converters"]["label"] == "pyrolysis", "nominal_capacity"]
            .values[0]
        )

    else:
        biochar_output = 1  # Ich weiß aktuell wie die Zeile heißt, Pfad noch hinzufügen

    return biochar_output


def lump_sum_pyrolysis_subsidy(data):

    biochar_output = receive_biochar_output(data)

    subsidy_per_biochar_ton = (
        data["policies"]
        .loc[data["policies"]["policy"] == "Subsidy for pyrolysis investment costs", "value 1"]
        .values[0]
    )
    total_subsidy = subsidy_per_biochar_ton * biochar_output
    total_subsidy = round(total_subsidy, 1)
    return {"pyrolysis_capex_subsidy": total_subsidy}


def percentage_pyrolysis_subsidy(data):
    biochar_output = receive_biochar_output(data)

    percentage_subsidy = (
        1
        / 100
        * data["policies"]
        .loc[
            data["policies"]["policy"] == "Percentage subsidy for pyrolysis investment costs",
            "value 1",
        ]
        .values[0]
    )
    pyrolysis_capex = (
        data["converters"].loc[data["converters"]["label"] == "pyrolysis", "capex"].values[0]
    )
    subsidy_per_biochar_ton = percentage_subsidy * pyrolysis_capex
    total_subsidy = subsidy_per_biochar_ton * biochar_output
    total_subsidy = round(total_subsidy, 1)
    return {"pyrolysis_capex_subsidy": total_subsidy}


def lump_sum_storage_subsidy(data, subsidy_value, subsidized_storage, scalar_objective):

    scenario = retrieve_scenario_from_input_data(data["general"])
    file_path = f"./results/{scenario}/results/scalar_results.csv"
    storage_invest_results = pd.read_csv(file_path, sep=";")

    subsidy = data["policies"].loc[data["policies"]["policy"] == subsidy_value, "value 1"].values[0]
    storage_investment = storage_invest_results.loc[
        storage_invest_results["variable"] == scalar_objective, "value"
    ].values[0]

    total_subsidy = subsidy * storage_investment
    total_subsidy = round(total_subsidy, 1)

    return {subsidized_storage: total_subsidy}


def percentage_storage_subsidy(data, subsidy_value, subsidized_storage, scalar_objective):

    scenario = retrieve_scenario_from_input_data(data["general"])
    file_path = f"./results/{scenario}/results/scalar_results.csv"
    storage_invest_results = pd.read_csv(file_path, sep=";")
    storage_capex = (
        data["storage"].loc[data["storage"]["label"] == subsidized_storage, "capex"].values[0]
    )
    percentage_subsidy = (
        1
        / 100
        * data["policies"].loc[data["policies"]["policy"] == subsidy_value, "value 1"].values[0]
    )
    storage_investment = storage_invest_results.loc[
        storage_invest_results["variable"] == scalar_objective, "value"
    ].values[0]
    subsidy_per_installed_capacity = percentage_subsidy * storage_capex
    total_subsidy = subsidy_per_installed_capacity * storage_investment
    total_subsidy = round(total_subsidy, 1)
    return {subsidized_storage: total_subsidy}


if __name__ == "__main__":
    data, time, scenario = implement_preprocessing_input_data_functions.preprocess(
        "input_data.xlsx"
    )
    lump_sum_pyrolysis_subsidy(data)
    percentage_pyrolysis_subsidy(data)
    lump_sum_storage_subsidy(
        data,
        "electricity storage lump sum subsidy",
        "electricity_storage",
        "electricity_storage_invest to None",
    )
    percentage_storage_subsidy(
        data,
        "electricity storage percentage subsidy",
        "electricity_storage",
        "electricity_storage_invest to None",
    )
