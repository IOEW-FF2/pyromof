import argparse

import pandas as pd

from pyromof.policies.implement_policies import (
    feed_in_payment_sliding_premium,
    receive_and_refine_electricity_price_data,
)


def receive_policies_sheet():

    path = "input_data.xlsx"

    policies = pd.read_excel(path, sheet_name="policies")

    return policies


def receive_scenario_electricity_data(scenario: str) -> pd.Series:

    file_path = f"./results/{scenario}/results/sequences.csv"

    separator = ";"

    target_column = "b_electricity to electricity_grid"

    data = pd.read_csv(file_path, sep=separator, index_col=0, parse_dates=[0])

    return data[target_column]


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

    feed_in_revenue_euro_per_kwh, government_payment_share_euro_per_kwh = (
        feed_in_payment_sliding_premium(policies, electricity_price_euro_per_kwh)
    )

    common_index = electricity_price_euro_per_kwh.index.intersection(
        pyrolysis_electricity_to_grid_kwh.index
    )

    if common_index.empty:
        raise ValueError("No overlapping timestamps found for sliding premium calculation.")

    electricity_price_euro_per_kwh = electricity_price_euro_per_kwh.loc[common_index].copy()
    pyrolysis_electricity_to_grid_kwh = pyrolysis_electricity_to_grid_kwh.loc[common_index].copy()
    feed_in_revenue_euro_per_kwh = feed_in_revenue_euro_per_kwh.loc[common_index].copy()
    government_payment_share_euro_per_kwh = government_payment_share_euro_per_kwh.loc[
        common_index
    ].copy()

    revenue_fed_in_electricity_euro = (
        feed_in_revenue_euro_per_kwh * pyrolysis_electricity_to_grid_kwh.copy()
    )

    government_payment_for_fed_in_electricity_euro = (
        government_payment_share_euro_per_kwh * pyrolysis_electricity_to_grid_kwh.copy()
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
