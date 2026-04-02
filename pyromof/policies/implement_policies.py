import pandas as pd


def receive_and_refine_electricity_price_data():

    data_file = pd.read_csv(
        "preprocessing/Gro_handelspreise_202501010000_202601010000_Stunde.csv",
        sep=";",
        parse_dates=True,
    )

    raw_data = data_file["Deutschland/Luxemburg [€/MWh] Berechnete Auflösungen"]

    data_replace_comma = raw_data.copy().str.replace(",", ".")

    data_float = data_replace_comma.astype(float)

    electricity_price_euro_per_kwh = data_float.copy() / -1000

    return electricity_price_euro_per_kwh


def fixed_premium_policy(sink: pd.DataFrame, policies: pd.DataFrame) -> pd.DataFrame:

    feed_in_premium = (
        -1
        / 100
        * policies.loc[policies["policy"] == "Fixed feed-in remuneration", "value 1"].values[0]
    )

    activate_status = policies.loc[
        policies["policy"] == "Fixed feed-in remuneration", "activate"
    ].values[0]

    if activate_status == "x":
        sink.loc[
            (sink["label"] == "electricity_grid"),
            "variable_costs",
        ] = feed_in_premium

    return sink


def feed_in_payment_sliding_premium(
    policies: pd.DataFrame,
    electricity_price_data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    This function calculates the feed-in payment for each hour in euro per kwh.
    Based on the electricity price data, base value, and lower threshold from policies.
    The feed-in payment is the base_value if:
    The electricity price is above the lower threshold and below the base value.
    Otherwise the feed_in payment is the electricity price.
    """

    base_value = (
        -1 / 100 * policies.loc[policies["policy"] == "Sliding premium", "value 1"].values[0]
    )

    lower_threshold = (
        -1 / 100 * policies.loc[policies["policy"] == "Sliding premium", "value 2"].values[0]
    )

    electricity_price = electricity_price_data

    feed_in_payment_euro_per_kwh = []

    for i in range(len(electricity_price)):
        if electricity_price.iloc[i] >= base_value and electricity_price.iloc[i] <= lower_threshold:
            feed_in_payment_euro_per_kwh.append(base_value)

        elif (
            electricity_price.iloc[i] >= lower_threshold or electricity_price.iloc[i] <= base_value
        ):
            feed_in_payment_euro_per_kwh.append(electricity_price.iloc[i])

    return pd.Series(feed_in_payment_euro_per_kwh, index=electricity_price.index)


def sliding_premium_policy(
    sink: pd.DataFrame,
    policies: pd.DataFrame,
    profiles: pd.DataFrame,
    electricity_price_data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    feed_in_payment_euro_per_kwh = feed_in_payment_sliding_premium(policies, electricity_price_data)
    activate_status = policies.loc[policies["policy"] == "Sliding premium", "activate"].values[0]

    if activate_status == "x":
        profiles["sliding_premium_profile"] = feed_in_payment_euro_per_kwh

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

    activate_status = policies.loc[
        policies["policy"] == "Subsidy for pyrolysis investment costs", "activate"
    ].values[0]

    if activate_status == "x":
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

    activate_status = policies.loc[
        policies["policy"] == "Percentage subsidy for pyrolysis investment costs", "activate"
    ].values[0]

    if activate_status == "x":
        converters.loc[(converters["label"] == "pyrolysis"), "capex"] = converters.loc[
            (converters["label"] == "pyrolysis"), "capex"
        ] * (1 - (1 / 100 * percentage_subsidy))

    return converters


def check_policy_choice_compatibility(policies):

    activated_policies = policies.loc[policies["activate"] == "x", "policy"].tolist()

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

    electricity_price_euro_per_kwh = receive_and_refine_electricity_price_data()

    data["sinks"] = fixed_premium_policy(sinks, policies)

    data["sinks"], data["profiles"] = sliding_premium_policy(
        sinks, policies, profiles, electricity_price_euro_per_kwh
    )

    data["converters"] = lump_sum_investment_subsidy_policy(converters, policies)

    data["converters"] = percentage_investment_subsidy_policy(converters, policies)

    return data["sinks"], data["converters"], data["profiles"]


# test if the functions work as expected for scenario "stromflex_h2"


def verify_redefine_input_data_for_policies(relative_file_path):

    profiles = pd.read_excel(relative_file_path, sheet_name="profiles")

    sinks = pd.read_excel(relative_file_path, sheet_name="sink")

    converters = pd.read_excel(relative_file_path, sheet_name="converter")

    policies = pd.read_excel(relative_file_path, sheet_name="policies")

    sink, converters, profiles = redefine_input_data_for_policies(
        sinks, converters, policies, profiles
    )

    print("\n=== pyrolysis converters: label, capex, investment ===")

    print(
        converters.loc[
            converters["label"] == "pyrolysis", ["label", "scenario", "capex", "investment"]
        ].to_string(index=False)
    )

    print("\n=== electricity_grid variable_costs for scenario stromflex_h2 ===")

    print(
        sink.loc[
            (sink["label"] == "electricity_grid") & (sink["scenario"] == "stromflex_h2"),
            "variable_costs",
        ].to_string(index=False)
    )


if __name__ == "__main__":
    verify_redefine_input_data_for_policies("input_data.xlsx")
