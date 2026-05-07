from pathlib import Path

import pandas as pd

# from pyromof.preprocessing_functions import preprocessing_input_data
from pyromof.policies.preprocess_implement_storage_subsidies import implement_storage_subsidies


def receive_and_refine_electricity_price_data(profiles):

    timestamps = pd.to_datetime(profiles.index)

    raw_data = profiles["electricity market price"]

    data_float = raw_data.astype(float)

    data_float.index = timestamps

    return data_float


def feed_in_tariff_policy(
    sink: pd.DataFrame,
    policies: pd.DataFrame,
) -> pd.DataFrame:

    feed_in_premium = (
        -1 / 100 * policies.loc[policies["policy"] == "feed in tariff", "value 1"].values[0]
    )

    sink.loc[
        (sink["label"] == "electricity_grid"),
        "variable_costs",
    ] = feed_in_premium

    return sink


def feed_in_payment_sliding_premium(data) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    This function calculates the feed-in payment for each hour in euro per kwh.
    Based on the electricity price data, base value, and lower threshold from policies.
    The monthly sliding premium is calculated from the difference between base value
    and monthly average electricity price.
    The premium is only added if the current electricity price is above the lower threshold.
    Otherwise the feed-in payment is the electricity price.
    """

    electricity_price = receive_and_refine_electricity_price_data(data["profiles"])

    base_value = (
        -1
        / 100
        * data["policies"].loc[data["policies"]["policy"] == "Sliding premium", "value 1"].values[0]
    )

    lower_threshold = (
        -1
        / 100
        * data["policies"].loc[data["policies"]["policy"] == "Sliding premium", "value 2"].values[0]
    )

    monthly_average_price = electricity_price.groupby(
        electricity_price.index.to_period("M")
    ).transform("mean")

    sliding_premium = (base_value - monthly_average_price).where(
        electricity_price < lower_threshold, -0
    )

    feed_in_revenue = electricity_price + sliding_premium

    return feed_in_revenue, sliding_premium, monthly_average_price


def sliding_premium_policy(data) -> tuple[pd.DataFrame, pd.DataFrame]:

    feed_in_revenue, _, _ = feed_in_payment_sliding_premium(data)

    data["profiles"]["sliding_premium_profile"] = feed_in_revenue
    data["profiles"]["timeindex"] = data["profiles"].index

    data["sink"].loc[
        (data["sink"]["label"] == "electricity_grid"),
        "variable_costs",
    ] = "sliding_premium_profile"

    return data["sink"], data["profiles"]


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


def check_policy_choice_compatibility(activated_policies):

    if (
        ("feed in tariff" in activated_policies and "Sliding premium" in activated_policies)
        or (
            "Subsidy for pyrolysis investment costs" in activated_policies
            and "Percentage subsidy for pyrolysis investment costs" in activated_policies
        )
        or (
            "electricity lump sum subsidy" in activated_policies
            and "electricity percentage subsidy" in activated_policies
        )
        or (
            "heat storage lump sum subsidy" in activated_policies
            and "heat storage percentage subsidy" in activated_policies
        )
        or (
            "hydrogen storage lump sum subsidy" in activated_policies
            and "hydrogen storage percentage subsidy" in activated_policies
        )
        or (
            "co2 storage lump sum subsidy" in activated_policies
            and "co2 storage percentage subsidy" in activated_policies
        )
    ):
        raise ValueError(
            "Only one of the policies in each policy type can be activated at the same time. \n"
            "Please check your input in the policies sheet."
        )

    else:
        return print("policies confirmed")


def redefine_input_data_for_policies(data, activated_policies):

    if "feed in tariff" in activated_policies:
        data["sinks"] = feed_in_tariff_policy(
            data["sinks"],
            data["policies"],
        )
    if "Sliding premium" in activated_policies:
        data["sinks"], data["profiles"] = sliding_premium_policy(
            data["sinks"],
            data["profiles"],
        )

    if "Subsidy for pyrolysis investment costs" in activated_policies:
        data["converters"] = lump_sum_investment_subsidy_policy(
            data["converters"],
            data["policies"],
        )

    if "Percentage subsidy for pyrolysis investment costs" in activated_policies:
        data["converters"] = percentage_investment_subsidy_policy(
            data["converters"],
            data["policies"],
        )

    return data


def implement_policies(data, scenario) -> None:

    active_policies = (
        data["policies"]
        .loc[data["policies"]["activate"] == "x", ["policy", "value 1"]]
        .set_index("policy")["value 1"]
        .to_dict()
    )

    check_policy_choice_compatibility(active_policies)

    # drop column "scenario" from all tables where it exists
    for key in data:
        if "scenario" in data[key].columns:
            data[key].drop(columns=["scenario"], inplace=True)
    data = redefine_input_data_for_policies(data, active_policies)
    data["storage"] = implement_storage_subsidies(data, active_policies)
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


"""
if __name__ == "__main__":
    data, time, scenario = preprocessing_input_data.preprocess("input_data.xlsx")
    implement_policies(data, scenario)
"""
