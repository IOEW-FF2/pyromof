import os
from pathlib import Path

import pandas as pd

from pyromof.postprocessing_functions.capex_policies import (
    lump_sum_pyrolysis_subsidy,
    lump_sum_storage_subsidy,
    percentage_pyrolysis_subsidy,
    percentage_storage_subsidy,
)
from pyromof.postprocessing_functions.opex_policies import (
    postprocess_feed_in_tariff,
    postprocess_sliding_premium,
)
from pyromof.preprocessing_functions import implement_preprocessing_input_data_functions
from pyromof.preprocessing_functions.preprocess_implement_policies import (
    check_policy_choice_compatibility,
)


def log_postprocessed_policies(data):

    activated_policies = (
        data["policies"].loc[data["policies"]["activate"] == "x", "policy"].dropna().tolist()
    )

    active_opex = (
        data["policies"]
        .loc[
            (data["policies"]["activate"] == "x") & (data["policies"]["policy category"] == "opex"),
            "policy",
        ]
        .dropna()
        .tolist()
    )
    opex_label = " + ".join(active_opex)

    check_policy_choice_compatibility(data["policies"])
    print("active policies:", activated_policies)

    policy_functions = {
        "feed in tariff": {
            "function": postprocess_feed_in_tariff,
            "type": "opex",
        },
        "sliding premium": {
            "function": postprocess_sliding_premium,
            "type": "opex",
        },
        "Percentage subsidy for pyrolysis investment costs": {
            "function": percentage_pyrolysis_subsidy,
            "type": "capex",
            "subsidy_value": "Percentage subsidy for pyrolysis investment costs",
            "subsidized_investment": "pyrolysis",
            "scalar_objective": "pyrolysis_invest to b_biochar",
        },
        "Subsidy for pyrolysis investment cost": {
            "function": lump_sum_pyrolysis_subsidy,
            "type": "capex",
            "subsidy_value": "Subsidy for pyrolysis investment cost",
            "subsidized_investment": "pyrolysis",
            "scalar_objective": "pyrolysis_invest to b_biochar",
        },
        "electricity storage lump sum subsidy": {
            "function": lump_sum_storage_subsidy,
            "type": "capex",
            "subsidy_value": "electricity storage lump sum subsidy",
            "subsidized_investment": "electricity_storage",
            "scalar_objective": "electricity_storage_invest to None",
        },
        "electricity storage percentage subsidy": {
            "function": percentage_storage_subsidy,
            "type": "capex",
            "subsidy_value": "electricity storage percentage subsidy",
            "subsidized_investment": "electricity_storage",
            "scalar_objective": "electricity_storage_invest to None",
        },
        "heat storage lump sum subsidy": {
            "function": lump_sum_storage_subsidy,
            "type": "capex",
            "subsidy_value": "heat storage lump sum subsidy",
            "subsidized_investment": "heat_storage",
            "scalar_objective": "heat_storage_invest to None",
        },
        "heat storage percentage subsidy": {
            "function": percentage_storage_subsidy,
            "type": "capex",
            "subsidy_value": "heat storage percentage subsidy",
            "subsidized_investment": "heat_storage",
            "scalar_objective": "heat_storage_invest to None",
        },
        "hydrogen storage lump sum subsidy": {
            "function": lump_sum_storage_subsidy,
            "type": "capex",
            "subsidy_value": "hydrogen storage lump sum subsidy",
            "subsidized_investment": "h2_storage",
            "scalar_objective": "h2_storage_invest to None",
        },
        "hydrogen storage percentage subsidy": {
            "function": percentage_storage_subsidy,
            "type": "capex",
            "subsidy_value": "hydrogen storage percentage subsidy",
            "subsidized_investment": "h2_storage",
            "scalar_objective": "h2_storage_invest to None",
        },
        "syngas storage lump sum subsidy": {
            "function": lump_sum_storage_subsidy,
            "type": "capex",
            "subsidy_value": "syngas storage lump sum subsidy",
            "subsidized_investment": "syngas_storage",
            "scalar_objective": "syngas_storage_invest to None",
        },
        "syngas storage percentage subsidy": {
            "function": percentage_storage_subsidy,
            "type": "capex",
            "subsidy_value": "syngas storage percentage subsidy",
            "subsidized_investment": "syngas_storage",
            "scalar_objective": "syngas_storage_invest to None",
        },
    }
    rows = []

    for policy in activated_policies:
        entry = policy_functions.get(policy)
        if entry is None:
            continue

        function = entry["function"]
        policy_type = entry["type"]

        kwargs = {}
        if (
            "subsidy_value" in entry
            and "subsidized_investment" in entry
            and "scalar_objective" in entry
        ):
            kwargs["subsidy_value"] = entry["subsidy_value"]
            kwargs["subsidized_investment"] = entry["subsidized_investment"]
            kwargs["scalar_objective"] = entry["scalar_objective"]
        result = function(data, **kwargs) if kwargs else function(data)

        if policy_type == "opex":
            label = opex_label
        else:
            label = policy

        for name, value in result.items():
            rows.append(
                {
                    "name": name,
                    "policy category": policy_type,
                    "relevant activated policies": label,
                    "value (euro)": value,
                }
            )
    df = pd.DataFrame(rows)

    results_dir = Path(__file__).resolve().parents[2] / "results" / scenario / "results"

    df.to_csv(os.path.join(results_dir, "policies_subsidies.csv"), index=False, sep=";")


if __name__ == "__main__":
    data, time, scenario = implement_preprocessing_input_data_functions.preprocess(
        "input_data.xlsx"
    )
    log_postprocessed_policies(data)
