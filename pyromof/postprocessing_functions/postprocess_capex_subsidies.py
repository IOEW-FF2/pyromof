from pyromof.postprocessing_functions.postprocess_policies_functions import (
    receive_capex_data,
)
from pyromof.preprocessing_functions import preprocessing_input_data


def postprocess_lump_sum_capex_subsidy(data):

    policies, _, yearly_biochar_output = receive_capex_data(data)

    subsidy_per_biochar_ton = policies.loc[
        policies["policy"] == "Subsidy for pyrolysis investment costs", "value 1"
    ].values[0]
    total_subsidy = subsidy_per_biochar_ton * yearly_biochar_output
    total_subsidy = total_subsidy.round(1)
    return {"pyrolysis_capex_subsidy": total_subsidy}


def postprocess_percentage_capex_subsidy(data):
    policies, converters, yearly_biochar_output = receive_capex_data(data)

    percentage_subsidy = (
        1
        / 100
        * policies.loc[
            policies["policy"] == "Percentage subsidy for pyrolysis investment costs", "value 1"
        ].values[0]
    )
    pyrolysis_capex = converters.loc[converters["label"] == "pyrolysis", "capex"].values[0]
    subsidy_per_biochar_ton = percentage_subsidy * pyrolysis_capex
    total_subsidy = subsidy_per_biochar_ton * yearly_biochar_output
    total_subsidy = total_subsidy.round(1)
    return {"pyrolysis_capex_subsidy": total_subsidy}


if __name__ == "__main__":
    data, time, scenario = preprocessing_input_data.preprocess("input_data.xlsx")
    postprocess_lump_sum_capex_subsidy(scenario, data)
    # postprocess_percentage_capex_subsidy(scenario, data)
