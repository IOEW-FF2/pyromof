from pathlib import Path

import pandas as pd

from pyromof.preprocessing_functions import preprocessing_input_data


def receive_and_refine_electricity_price_data(profiles):

    timestamps = pd.to_datetime(profiles.index)

    raw_data = profiles["electricity market price"]

    data_float = raw_data.astype(float)

    data_float.index = timestamps

    return data_float


def receive_higher_threshold_basis_and_lower_threshold_basis(policies):

    base_value = (
        -1 / 100 * policies.loc[policies["policy"] == "Sliding premium", "value 1"].values[0]
    )

    lower_threshold = (
        -1 / 100 * policies.loc[policies["policy"] == "Sliding premium", "value 2"].values[0]
    )

    return base_value, lower_threshold


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
    electricity_price_data: pd.Series,
    base_value,
    lower_threshold,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    This function calculates the feed-in payment for each hour in euro per kwh.
    Based on the electricity price data, base value, and lower threshold from policies.
    The monthly sliding premium is calculated from the difference between base value
    and monthly average electricity price.
    The premium is only added if the current electricity price is above the lower threshold.
    Otherwise the feed-in payment is the electricity price.
    """

    monthly_average_price = electricity_price_data.groupby(
        electricity_price_data.index.to_period("M")
    ).transform("mean")

    sliding_premium = (base_value - monthly_average_price).where(
        electricity_price_data < lower_threshold, -0
    )

    feed_in_payment_euro_per_kwh = electricity_price_data + sliding_premium

    return feed_in_payment_euro_per_kwh, sliding_premium, monthly_average_price


def sliding_premium_policy(
    sink: pd.DataFrame,
    profiles: pd.DataFrame,
    base_value,
    lower_threshold,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    electricity_price_euro_per_kwh = receive_and_refine_electricity_price_data(profiles)
    feed_in_payment_euro_per_kwh, _, _ = feed_in_payment_sliding_premium(
        electricity_price_euro_per_kwh, base_value, lower_threshold
    )

    profiles["sliding_premium_profile"] = feed_in_payment_euro_per_kwh
    profiles["timeindex"] = profiles.index

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

    check_policy_choice_compatibility(data["policies"])

    activated_policies = get_activated_policies(data["policies"])

    base_value = None
    lower_threshold = None

    for policy_name in activated_policies:
        if policy_name == "Fixed feed-in remuneration":
            data["sinks"] = lump_sum_premium_policy(data["sinks"], data["policies"])

        elif policy_name == "Sliding premium":
            if base_value is None or lower_threshold is None:
                base_value, lower_threshold = (
                    receive_higher_threshold_basis_and_lower_threshold_basis(data["policies"])
                )

            data["sinks"], data["profiles"] = sliding_premium_policy(
                data["sinks"],
                data["profiles"],
                base_value,
                lower_threshold,
            )

        elif policy_name == "Subsidy for pyrolysis investment costs":
            data["converters"] = lump_sum_investment_subsidy_policy(
                data["converters"], data["policies"]
            )

        elif policy_name == "Percentage subsidy for pyrolysis investment costs":
            data["converters"] = percentage_investment_subsidy_policy(
                data["converters"], data["policies"]
            )

    return data


def implement_policies(data, scenario) -> None:

    # drop column "scenario" from all tables where it exists
    for key in data:
        if "scenario" in data[key].columns:
            data[key].drop(columns=["scenario"], inplace=True)
    data = redefine_input_data_for_policies(data)

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
            table_data = table_data.replace({True: "True", False: "False"})
            if isinstance(table_data, pd.DataFrame):
                table_data.to_excel(writer, sheet_name=table_name, index=False)
    return data


if __name__ == "__main__":
    data, time, scenario = preprocessing_input_data.preprocess("input_data.xlsx")
    implement_policies(data, scenario)
