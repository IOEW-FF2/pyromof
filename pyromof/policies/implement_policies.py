import pandas as pd
from pyromof.policies.sliding_premium import (
    feed_in_payment_cent_per_kWh,
    receive_and_refine_electricity_price_data,
    receive_base_value_and_lower_threshold,
)


def fixed_premium_policy(sink: pd.DataFrame, policies: pd.DataFrame, scenario: str) -> pd.DataFrame:
    feed_in_premium = policies.loc[
        policies["policy"] == "Fixes feed_in remuneration", "value 1"
    ].values[0]
    activate_status = policies.loc[
        policies["policy"] == "Fixed feed-in remuneration", "activate"
    ].values[0]
    if activate_status == "x":
        sink.loc[
            sink["label"] == "electricity_grid" and sink["scenario"] == scenario, "variable_costs"
        ] = feed_in_premium
    return sink


def sliding_premium_policy(
    sink: pd.DataFrame, policies: pd.DataFrame, scenario: str
) -> pd.DataFrame:
    base_value, lower_threshold = receive_base_value_and_lower_threshold(scenario)
    electricity_price_cent_per_kWh = receive_and_refine_electricity_price_data()
    sliding_feed_in_premium = feed_in_payment_cent_per_kWh(
        electricity_price_cent_per_kWh, base_value, lower_threshold
    )
    activate_status = policies.loc[policies["policy"] == "Sliding premium", "activate"].values[0]

    if activate_status == "x":
        sink.loc[
            sink["label"] == "electricity_grid" and sink["scenario"] == scenario, "variable_costs"
        ] = sliding_feed_in_premium

    return sink


def fix_investment_subsidy_policy(converter: pd.DataFrame, policies: pd.DataFrame) -> pd.DataFrame:
    fix_subsidy = policies.loc[
        policies["policy"] == "Subsidy for pyrolysis investment costs", "value 1"
    ].values[0]
    activate_status = policies.loc[
        policies["policy"] == "Fixed feed-in remuneration", "activate"
    ].values[0]
    base_investment_cost = converter.loc[converter["label"] == "pyrolysis", "capex"].values[0]

    if activate_status == "x":
        converter.loc[converter["label"] == "pyrolysis", "capex"] = (
            base_investment_cost - fix_subsidy
        )
    return converter


def percentage_investment_subsidy_policy(
    converter: pd.DataFrame, policies: pd.DataFrame
) -> pd.DataFrame:
    percentage_subsidy = policies.loc[policies["policy"] == "percentage subsidy", "value 1"].values[
        0
    ]
    activate_status = policies.loc[policies["policy"] == "percentage subsidy", "activate"].values[0]
    # Name für Zeile ("percentage subsidy") ggf. noch anpassen, da stand jezt nichts drin
    base_investment_cost = converter.loc[converter["label"] == "pyrolysis", "capex"].values[0]

    if activate_status == "x":
        converter.loc[converter["label"] == "pyrolysis", "capex"] = base_investment_cost * (
            1 - percentage_subsidy
        )
    return converter


def redefine_sinks_for_policies(
    sink: pd.DataFrame, converter: pd.DataFrame, policies: pd.DataFrame, scenario: str
) -> pd.DataFrame:

    if (
        policies.loc[policies["policy"] == "Fixed feed-in remuneration", "activate"].values[0]
        == "x"
        and policies.loc[policies["policy"] == "Sliding premium", "activate"].values[0] == "x"
        or policies.loc[
            policies["policy"] == "Subsidy for pyrolysis investment costs", "activate"
        ].values[0]
        == "x"
        and policies.loc[policies["policy"] == "percentage subsidy", "activate"].values[0] == "x"
    ):
        raise ValueError(
            "Only one of the policies in each policy type can be activated at the same time. \n"
            "Please check your input in the policies sheet."
        )
    else:
        sink = fixed_premium_policy(sink, policies, scenario)
        sink = sliding_premium_policy(sink, policies, scenario)
        converter = fix_investment_subsidy_policy(converter, policies)
        converter = percentage_investment_subsidy_policy(converter, policies)

    return sink, converter
