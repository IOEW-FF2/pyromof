import os
from pathlib import Path

import pandas as pd

from pyromof.policies.implement_policies import (
    get_activated_policies,
    receive_and_refine_electricity_price_data,
)
from pyromof.postprocessing import add_items_to_scalar_results


def receive_data(scenario: str, data: dict) -> tuple[pd.Series, pd.Series, float, float]:

    policies = data["policies"]

    pyrolysis_electricity_output = pd.read_csv(
        f"./results/{scenario}/results/sequences.csv", sep=";", index_col=0, parse_dates=True
    )["b_electricity to electricity_grid"]

    electricity_price = receive_and_refine_electricity_price_data(data["profiles"])

    return (electricity_price, pyrolysis_electricity_output, policies)


def add_sums_to_log_file(
    sum_government_payment, sum_feed_in_revenue, sum_market_payment, scenario, policies
):

    activated_policies = get_activated_policies(policies)
    # create csv file with payment sums
    results_dir = Path(__file__).resolve().parents[2] / "results" / scenario / "results"
    df2 = pd.DataFrame({})

    sum_dict = {
        "activated_policies": activated_policies,
        "government_payment_share (euro)": sum_government_payment,
        "electricity_market_payment_share (euro)": sum_market_payment,
        "revenue_fed_in_electricity (euro)": sum_feed_in_revenue,
    }
    revenue_sums = add_items_to_scalar_results(sum_dict, "sliding_premium", df2.copy())

    revenue_sums.to_csv(
        os.path.join(results_dir, "electricity_revenue_data.csv"), index=False, sep=";"
    )


def receive_capex_data(scenario, data):

    policies = data["policies"]
    converters = data["converters"]

    yearly_biochar_output = (
        1
        / 1000
        * pd.read_csv(
            f"./results/{scenario}/results/sequences.csv", sep=";", index_col=0, parse_dates=True
        )["b_biochar to biochar_market"].sum()
    )
    # Es wird ein Auslegungswert für den jährlichen Biochar output benötigt
    # -> ist der 59,9 Wert der stündlich angelegte output Wert?
    # aktuell wird dann nur Monatswert berechnet

    # zweite Möglcihkeit:
    yearly_biochar_output = (
        8.76 * converters.loc[converters["label"] == "pyrolysis", "nominal_capacity"].values[0]
    )
    # 8.76 da stündlcher Wert * 8760 Stunden im Jahr und /1000 von kg zu t

    return policies, converters, yearly_biochar_output
