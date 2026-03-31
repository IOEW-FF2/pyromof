import pandas as pd
from sliding_premium import receive_and_refine_electricity_price_data


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


def sliding_premium_policy(
    sink: pd.DataFrame,
    policies: pd.DataFrame,
    profiles: pd.DataFrame,
    electricity_price_data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    base_value = (
        -1 / 100 * policies.loc[policies["policy"] == "Sliding premium", "value 1"].values[0]
    )
    lower_threshold = (
        -1 / 100 * policies.loc[policies["policy"] == "Sliding premium", "value 2"].values[0]
    )
    electricity_price = electricity_price_data
    activate_status = policies.loc[policies["policy"] == "Sliding premium", "activate"].values[0]

    feed_in_payment_euro_per_kWh = []

    for i in range(len(electricity_price)):
        if electricity_price.iloc[i] >= base_value and electricity_price.iloc[i] <= lower_threshold:
            feed_in_payment_euro_per_kWh.append(base_value)

        elif (
            electricity_price.iloc[i] >= lower_threshold or electricity_price.iloc[i] <= base_value
        ):
            feed_in_payment_euro_per_kWh.append(electricity_price.iloc[i])

    if activate_status == "x":
        profiles["sliding_premium_profile"] = feed_in_payment_euro_per_kWh
        sink.loc[
            (sink["label"] == "electricity_grid"),
            "variable_costs",
        ] = "sliding_premium_profile"

    return sink, profiles


def fix_investment_subsidy_policy(converters: pd.DataFrame, policies: pd.DataFrame) -> pd.DataFrame:
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


def confirm_policies(policies):
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


def redefine_sink_and_converter_for_policies(
    sink: pd.DataFrame,
    converters: pd.DataFrame,
    policies: pd.DataFrame,
    profiles: pd.DataFrame,
) -> pd.DataFrame:

    confirm_policies(policies)
    electricity_price_data = receive_and_refine_electricity_price_data()
    electricity_price_euro_per_mwh = electricity_price_data["euro_per_kWh"]

    sink = fixed_premium_policy(sink, policies)
    sink, profiles = sliding_premium_policy(
        sink, policies, profiles, electricity_price_euro_per_mwh
    )
    converters = fix_investment_subsidy_policy(converters, policies)
    converters = percentage_investment_subsidy_policy(converters, policies)

    return sink, converters, profiles


# test if the functions work as expected for scenario "stromflex_h2"


def verify_redefine_sink_and_converter_for_policies(relative_file_path):
    profiles = pd.read_excel(relative_file_path, sheet_name="profiles")
    sinks = pd.read_excel(relative_file_path, sheet_name="sink")
    converters = pd.read_excel(relative_file_path, sheet_name="converter")
    policies = pd.read_excel(relative_file_path, sheet_name="policies")

    sink, converters, profiles = redefine_sink_and_converter_for_policies(
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
    verify_redefine_sink_and_converter_for_policies("input_data.xlsx")
