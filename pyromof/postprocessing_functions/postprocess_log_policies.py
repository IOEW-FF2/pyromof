import os
from pathlib import Path

import pandas as pd

from pyromof.postprocessing_functions.postprocess_capex_subsidies import (
    postprocess_lump_sum_capex_subsidy,
    postprocess_percentage_capex_subsidy,
)
from pyromof.postprocessing_functions.postprocess_feed_in_tariff import postprocess_feed_in_tariff
from pyromof.postprocessing_functions.postprocess_sliding_premium import postprocess_sliding_premium
from pyromof.preprocessing_functions import implement_preprocessing_input_data_functions
from pyromof.preprocessing_functions.preprocess_implement_policies import (
    check_policy_choice_compatibility,
)


def log_postprocessed_policies(scenario, data):

    policies = data["policies"]

    activated_policies = policies.loc[policies["activate"] == "x", "policy"].dropna().tolist()

    active_opex = (
        policies.loc[
            (policies["activate"] == "x") & (policies["policy category"] == "opex"), "policy"
        ]
        .dropna()
        .tolist()
    )
    opex_label = " + ".join(active_opex)

    check_policy_choice_compatibility(policies)
    print("active policies:", activated_policies)

    policy_functions = {
        "feed in tariff": {"function": postprocess_feed_in_tariff, "type": "opex"},
        "sliding premium": {"function": postprocess_sliding_premium, "type": "opex"},
        "Percentage subsidy for pyrolysis investment costs": {
            "function": postprocess_percentage_capex_subsidy,
            "type": "capex",
        },
        "Subsidy for pyrolysis investment cost": {
            "function": postprocess_lump_sum_capex_subsidy,
            "type": "capex",
        },
    }
    rows = []

    for policy in activated_policies:
        entry = policy_functions.get(policy)
        if entry is None:
            continue

        function = entry["function"]
        policy_type = entry["type"]

        result = function(scenario, data)

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
    log_postprocessed_policies(scenario, data)
