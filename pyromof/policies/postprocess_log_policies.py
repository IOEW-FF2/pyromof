import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from pyromof.policies.implement_policies import check_policy_choice_compatibility
from pyromof.policies.postprocess_capex_subsidies import (
    postprocess_lump_sum_capex_subsidy,
    postprocess_percentage_capex_subsidy,
)
from pyromof.policies.postprocess_feed_in_tarrif import postprocess_feed_in_tarrif
from pyromof.policies.postprocess_sliding_premium import postprocess_sliding_premium
from pyromof.postprocessing import add_items_to_scalar_results
from pyromof.preprocessing_functions import preprocessing_input_data


def log_postprocessed_policies(scenario, data):
    log_time = datetime.now()
    policies = data["policies"]
    activated_policies = policies.loc[policies["activate"] == "x", "policy"].tolist()
    check_policy_choice_compatibility(policies)

    for policy_name in activated_policies:
        if policy_name == "Fixed feed-in remuneration":
            sum_feed_in_revenue, sum_government_payment, sum_market_payment = (
                postprocess_feed_in_tarrif(scenario, data)
            )

        elif policy_name == "Sliding premium":
            sum_feed_in_revenue, sum_government_payment, sum_market_payment = (
                postprocess_sliding_premium(scenario, data)
            )

        elif policy_name == "Subsidy for pyrolysis investment costs":
            pyrolysis_capex_subsidy = postprocess_lump_sum_capex_subsidy

        elif policy_name == "Percentage subsidy for pyrolysis investment costs":
            pyrolysis_capex_subsidy = postprocess_percentage_capex_subsidy
        # längerfristig capex subsidy für storage als weitere Spalte implementieren,
        # nicht zusammen mit pyrolysis subsidy

    # create csv file with payment sums
    results_dir = Path(__file__).resolve().parents[2] / "results" / scenario / "results"
    df2 = pd.DataFrame({})

    sum_dict = {
        "log_time": log_time,
        "activated_policies": activated_policies,  # wschl falscher Datentyp für Excel Spalte
        "government_payment_share (euro)": sum_government_payment,
        "electricity_market_payment_share (euro)": sum_market_payment,
        "revenue_fed_in_electricity (euro)": sum_feed_in_revenue,
        "pyrolysis_capex_subsidy": pyrolysis_capex_subsidy,
    }

    revenue_sums = add_items_to_scalar_results(sum_dict, "sliding_premium", df2.copy())

    revenue_sums.to_csv(
        os.path.join(results_dir, "electricity_revenue_data.csv"), index=False, sep=";"
    )


if __name__ == "__main__":
    data, time, scenario = preprocessing_input_data.preprocess("input_data.xlsx")
