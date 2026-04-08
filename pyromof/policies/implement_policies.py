from pathlib import Path

import pandas as pd


def receive_and_refine_electricity_price_data():

    data_file = pd.read_csv(
        "preprocessing/Gro_handelspreise_202501010000_202601010000_Stunde.csv",
        sep=";",
        parse_dates=True,
    )

    timestamps = pd.to_datetime(data_file["Datum von"], format="%d.%m.%Y %H:%M")

    raw_data = data_file["Deutschland/Luxemburg [€/MWh] Berechnete Auflösungen"]

    data_replace_comma = raw_data.copy().str.replace(",", ".")

    data_float = data_replace_comma.astype(float)

    electricity_price_euro_per_kwh = data_float.copy() / -1000
    electricity_price_euro_per_kwh.index = timestamps

    return electricity_price_euro_per_kwh


def lump_sum_premium_policy(
    sink: pd.DataFrame,
    policies: pd.DataFrame,
) -> pd.DataFrame:

    feed_in_premium = (
        -1
        / 100
        * policies.loc[policies["policy"] == "Fixed feed-in remuneration", "value 1"].values[0]
    )

    sink.loc[
        (sink["label"] == "electricity_grid"),
        "variable_costs",
    ] = feed_in_premium

    return sink


def feed_in_payment_sliding_premium(
    policies: pd.DataFrame,
    electricity_price_data: pd.Series,
) -> pd.Series:
    """
    This function calculates the feed-in payment for each hour in euro per kwh.
    Based on the electricity price data, base value, and lower threshold from policies.
    The monthly sliding premium is calculated from the difference between base value
    and monthly average electricity price.
    The premium is only added if the current electricity price is above the lower threshold.
    Otherwise the feed-in payment is the electricity price.
    """

    base_revenue = (
        -1 / 100 * policies.loc[policies["policy"] == "Sliding premium", "value 1"].values[0]
    )

    lower_threshold_basis = (
        -1 / 100 * policies.loc[policies["policy"] == "Sliding premium", "value 2"].values[0]
    )

    monthly_average_price = electricity_price_data.groupby(
        electricity_price_data.index.to_period("M")
    ).transform("mean")

    lower_threshold_monthly = lower_threshold_basis - monthly_average_price

    sliding_premium = (base_revenue - monthly_average_price).where(
        electricity_price_data < lower_threshold_monthly,
        0,
    )

    feed_in_payment_euro_per_kwh = electricity_price_data + sliding_premium

    return feed_in_payment_euro_per_kwh, sliding_premium


def sliding_premium_policy(
    sink: pd.DataFrame,
    policies: pd.DataFrame,
    profiles: pd.DataFrame,
    electricity_price_data: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    feed_in_payment_euro_per_kwh, _ = feed_in_payment_sliding_premium(
        policies, electricity_price_data
    )

    profiles["sliding_premium_profile"] = feed_in_payment_euro_per_kwh.reset_index(drop=True)

    sink.loc[
        (sink["label"] == "electricity_grid"),
        "variable_costs",
    ] = "sliding_premium_profile"

    return sink, profiles


def lump_sum_investment_subsidy_policy(
    converters: pd.DataFrame, policies: pd.DataFrame
) -> pd.DataFrame:

    fix_subsidy = policies.loc[
        policies["policy"] == "Subsidy for pyrolysis investment costs", "value 1"
    ].values[0]

    converters.loc[(converters["label"] == "pyrolysis"), "capex"] = (
        converters.loc[(converters["label"] == "pyrolysis"), "capex"] - fix_subsidy
    )

    return converters


def percentage_investment_subsidy_policy(
    converters: pd.DataFrame, policies: pd.DataFrame
) -> pd.DataFrame:

    percentage_subsidy = policies.loc[
        policies["policy"] == "Percentage subsidy for pyrolysis investment costs", "value 1"
    ].values[0]

    converters.loc[(converters["label"] == "pyrolysis"), "capex"] = converters.loc[
        (converters["label"] == "pyrolysis"), "capex"
    ] * (1 - (1 / 100 * percentage_subsidy))

    return converters


def get_activated_policies(policies: pd.DataFrame) -> list[str]:

    return policies.loc[policies["activate"] == "x", "policy"].tolist()


def check_policy_choice_compatibility(policies):

    activated_policies = get_activated_policies(policies)

    if (
        "Fixed feed-in remuneration" in activated_policies
        and "Sliding premium" in activated_policies
    ) or (
        "Subsidy for pyrolysis investment costs" in activated_policies
        and "Percentage subsidy for pyrolysis investment costs" in activated_policies
    ):
        raise ValueError(
            "Only one of the policies in each policy type can be activated at the same time. \n"
            "Please check your input in the policies sheet."
        )

    else:
        return print("policies confirmed")


def redefine_input_data_for_policies(data):

    policies = data["policies"]
    sinks = data["sinks"]
    converters = data["converters"]
    profiles = data["profiles"]

    check_policy_choice_compatibility(policies)

    activated_policies = get_activated_policies(policies)
    electricity_price_euro_per_kwh = None

    for policy_name in activated_policies:
        if policy_name == "Fixed feed-in remuneration":
            sinks = lump_sum_premium_policy(sinks, policies)
            data["sinks"] = sinks

        elif policy_name == "Sliding premium":
            if electricity_price_euro_per_kwh is None:
                electricity_price_euro_per_kwh = receive_and_refine_electricity_price_data()

            sinks, profiles = sliding_premium_policy(
                sinks,
                policies,
                profiles,
                electricity_price_euro_per_kwh,
            )
            data["sinks"] = sinks
            data["profiles"] = profiles

        elif policy_name == "Subsidy for pyrolysis investment costs":
            converters = lump_sum_investment_subsidy_policy(converters, policies)
            data["converters"] = converters

        elif policy_name == "Percentage subsidy for pyrolysis investment costs":
            converters = percentage_investment_subsidy_policy(converters, policies)
            data["converters"] = converters

    return data["sinks"], data["converters"], data["profiles"]


def main() -> None:

    from pyromof.optimize import read_raw_data

    data = read_raw_data("input_data.xlsx")
    redefine_input_data_for_policies(data)
    scenario = data["general"].loc[data["general"]["label"] == "scenario", "value"].item()
    output_file = (
        Path("results")
        / scenario
        / "meta_info"
        / "input_preprocessed"
        / "input_data_with_applied_policies.xlsx"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_file) as writer:
        for table_name, table_data in data.items():
            if isinstance(table_data, pd.DataFrame):
                table_data.to_excel(writer, sheet_name=table_name, index=False)


if __name__ == "__main__":
    main()
