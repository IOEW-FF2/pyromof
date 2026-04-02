import argparse

import pandas as pd

from pyromof.policies.implement_policies import receive_and_refine_electricity_price_data


def receive_policies_sheet():

    path = "input_data.xlsx"

    policies = pd.read_excel(path, sheet_name="policies")

    return policies


def receive_scenario_electricity_data(scenario: str) -> pd.Series:

    file_path = f"./results/{scenario}/results/sequences.csv"

    separator = ";"

    parse_dates = True

    target_column = "b_electricity to electricity_grid"

    data = pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)

    return data[target_column]


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


def government_payment_euro_per_kwh(
    electricity_price_euro_per_kwh, feed_in_payment_euro_per_kwh, policies
):
    """

    This function calculates the government payment share of the feed-in premium in euro per kwh.


    The goverment payment share is calculated as:


    feed_in_payment (cent/kwh) - electricity price (cent/kwh)


    As long as the electricity price ist between lower threshold and base value.


    Otherwise the government payment share is zero.


    This is further explained in the feed_in_payment function.


    """

    base_value = (
        -1 / 100 * policies.loc[policies["policy"] == "Sliding premium", "value 1"].values[0]
    )

    payments = []

    for i in range(len(feed_in_payment_euro_per_kwh)):
        if feed_in_payment_euro_per_kwh.iloc[i] == base_value:
            payments.append(
                feed_in_payment_euro_per_kwh.iloc[i] - electricity_price_euro_per_kwh.iloc[i]
            )

        elif feed_in_payment_euro_per_kwh.iloc[i] != base_value:
            payments.append(0)

    return pd.Series(payments, index=feed_in_payment_euro_per_kwh.index)


def multiply(a, b):

    return a * b


def add_items_to_scalar_results(dictionary: dict, type: str, scalar_results):
    """


    This functions adds given data to an existing dataframe with scalar results.


    The existing dataframe must have the columns "variable", "type" and "value".


    The input dict must contain the variable and value for each item. The type


    must be valid for all items in the dictionary.


    """

    new_df = pd.DataFrame(
        {
            "variable": list(dictionary.keys()),
            # Insert the given type for all new rows:
            "type": [type] * len(dictionary),
            "value": list(dictionary.values()),
        }
    )

    return pd.concat([scalar_results, new_df], ignore_index=True)


def receive_and_refine_all_data(scenario: str) -> None:
    """

    This function receives and refines all necessary input data based on the functions defined above


    The input data depend on the given scenario.


    """

    policies = receive_policies_sheet()

    electricity_price_euro_per_kwh = receive_and_refine_electricity_price_data()

    pyrolysis_electricity_to_grid_kwh = receive_scenario_electricity_data(scenario)

    return (
        policies,
        electricity_price_euro_per_kwh,
        pyrolysis_electricity_to_grid_kwh,
    )


def calculate_payments(electricity_price_euro_per_kwh, pyrolysis_electricity_to_grid_kwh, policies):
    """

    This function calculates the various payments and payment shares in cent/kWh and euro.


    The input data is the output of the receive_and_refine_all_data function.


    """

    feed_in_revenue_euro_per_kwh = feed_in_payment_sliding_premium(
        policies, electricity_price_euro_per_kwh
    )

    government_payment_share_euro_per_kwh = government_payment_euro_per_kwh(
        electricity_price_euro_per_kwh.copy(), feed_in_revenue_euro_per_kwh.copy(), policies
    )

    revenue_fed_in_electricity_euro = multiply(
        feed_in_revenue_euro_per_kwh.copy(), pyrolysis_electricity_to_grid_kwh.copy()
    )

    government_payment_for_fed_in_electricity_euro = multiply(
        government_payment_share_euro_per_kwh.copy(), pyrolysis_electricity_to_grid_kwh.copy()
    )

    electricity_market_payment_euro = (
        revenue_fed_in_electricity_euro.copy()
        - government_payment_for_fed_in_electricity_euro.copy()
    )

    return (
        feed_in_revenue_euro_per_kwh,
        government_payment_share_euro_per_kwh,
        revenue_fed_in_electricity_euro,
        government_payment_for_fed_in_electricity_euro,
        electricity_market_payment_euro,
    )


def calc_payment_sums(
    revenue_fed_in_electricity_euro,
    government_payment_for_fed_in_electricity_euro,
    electricity_market_payment_euro,
):
    """

    This function calculates the sums of the revenue and payment shares for fed-in electricity.


    """

    sum_revenue_fed_in_electricity_euro = revenue_fed_in_electricity_euro.sum()

    sum_government_payment_euro = government_payment_for_fed_in_electricity_euro.sum()

    sum_electricity_market_payment_euro = electricity_market_payment_euro.sum()

    return (
        sum_revenue_fed_in_electricity_euro,
        sum_government_payment_euro,
        sum_electricity_market_payment_euro,
    )


def create_csv_file_for_created_data(
    electricity_price_euro_per_kwh,
    feed_in_revenue_euro_per_kwh,
    government_payment_share_euro_per_kwh,
    pyrolysis_electricity_to_grid_kwh,
    revenue_fed_in_electricity_euro,
    government_payment_for_fed_in_electricity_euro,
    electricity_market_payment_euro,
    sum_government_payment_euro,
    sum_electricity_market_payment_euro,
    sum_revenue_fed_in_electricity_euro,
):
    """

    This function summarizes the calculated payments and payment sums in two csv files.


    The second csv file contains the actual revenue and payment shares for fed-in electricity,


    as well as the sums the above.


    The file is called "electricity_revenue_data.csv" and is stored in the "preprocessing" folder.


    The first csv file contains all data necessary for the calculations.


    This file ist called "feed_in_premium_data.csv" and is stored in the "preprocessing" folder.


    The input for this function is the output of the functions called in the main function.




    """

    df = pd.DataFrame(
        {
            "electricity_price (euro/kWh)": electricity_price_euro_per_kwh.round(4),
            "feed_in_payment (euro/kWh)": feed_in_revenue_euro_per_kwh.round(4),
            "government_payment_share (euro/kWh)": government_payment_share_euro_per_kwh.round(4),
            "pyrolysis_electricity_to_grid (kWh)": pyrolysis_electricity_to_grid_kwh.round(2),
            "revenue_fed_in_electricity (euro)": revenue_fed_in_electricity_euro.round(1),
            "government_payment_share (euro)": government_payment_for_fed_in_electricity_euro.round(
                1
            ),
            "electricity_market_payment_share (euro)": electricity_market_payment_euro.round(1),
        }
    )

    # df = df.round(2)

    df.to_csv("preprocessing/feed_in_premium_data.csv", index=False, sep=";")

    df2 = pd.DataFrame(
        {
            "government_payment_share (euro)": government_payment_for_fed_in_electricity_euro,
            "electricity_market_payment_share (euro)": electricity_market_payment_euro,
            "revenue_fed_in_electricity (euro)": revenue_fed_in_electricity_euro,
        }
    )

    df2 = df2.round(1)

    sum_dict = {
        "government_payment_share (euro)": sum_government_payment_euro,
        "electricity_market_payment_share (euro)": sum_electricity_market_payment_euro,
        "revenue_fed_in_electricity (euro)": sum_revenue_fed_in_electricity_euro,
    }

    df2_with_sum = add_items_to_scalar_results(sum_dict, "sum", df2.copy())

    df2_with_sum.to_csv("preprocessing/electricity_revenue_data.csv", index=False, sep=";")

    print("check if sum is correct:")

    print(f"total sum: {sum_revenue_fed_in_electricity_euro.round(1)} euro")

    print(
        f"government payment + electricity market payment: \n"
        f"{sum_government_payment_euro.round(1) + sum_electricity_market_payment_euro.round(1)}euro"
    )


def main(scenario: str) -> None:
    """

    The main function executes all functions in a logical order.




    """

    (
        policies,
        electricity_price_euro_per_kwh,
        pyrolysis_electricity_to_grid_kwh,
    ) = receive_and_refine_all_data(scenario)

    (
        feed_in_revenue_euro_per_kwh,
        government_payment_share_euro_per_kwh,
        revenue_fed_in_electricity_euro,
        government_payment_for_fed_in_electricity_euro,
        electricity_market_payment_euro,
    ) = calculate_payments(
        electricity_price_euro_per_kwh, pyrolysis_electricity_to_grid_kwh, policies
    )

    (
        sum_revenue_fed_in_electricity_euro,
        sum_government_payment_euro,
        sum_electricity_market_payment_euro,
    ) = calc_payment_sums(
        revenue_fed_in_electricity_euro,
        government_payment_for_fed_in_electricity_euro,
        electricity_market_payment_euro,
    )

    create_csv_file_for_created_data(
        electricity_price_euro_per_kwh,
        feed_in_revenue_euro_per_kwh,
        government_payment_share_euro_per_kwh,
        pyrolysis_electricity_to_grid_kwh,
        revenue_fed_in_electricity_euro,
        government_payment_for_fed_in_electricity_euro,
        electricity_market_payment_euro,
        sum_government_payment_euro,
        sum_electricity_market_payment_euro,
        sum_revenue_fed_in_electricity_euro,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        required=True,
        help="Name of the scenario, e.g. stromflex_h2",
    )

    args = parser.parse_args()

    main(args.scenario)
