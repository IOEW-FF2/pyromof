import argparse

import pandas as pd

from pyromof.policies.implement_policies import (
    feed_in_payment_sliding_premium,
    receive_and_refine_electricity_price_data,
    receive_higher_threshold_basis_and_lower_threshold_basis,
)
from pyromof.postprocessing import add_items_to_scalar_results


def receive_data(scenario: str, electricity_prices_path: str, input_data_path) -> None:

    policies = pd.read_excel(input_data_path, sheet_name="policies")

    base_value, lower_threshold = receive_higher_threshold_basis_and_lower_threshold_basis(policies)

    pyrolysis_electricity_output = pd.read_csv(
        f"./results/{scenario}/results/sequences.csv", sep=";", index_col=0, parse_dates=True
    )["b_electricity to electricity_grid"]

    electricity_price = receive_and_refine_electricity_price_data(electricity_prices_path)

    return (electricity_price, pyrolysis_electricity_output, base_value, lower_threshold)


def calculate_payment_sums(
    electricity_price, pyrolysis_electricity_output, base_value, lower_threshold
):

    # calculate sliding premium and revenue per kwh
    feed_in_revenue_euro_per_kwh, sliding_premium, _ = feed_in_payment_sliding_premium(
        electricity_price,
        base_value,
        lower_threshold,
    )

    # calculate payments
    feed_in_revenue = feed_in_revenue_euro_per_kwh * pyrolysis_electricity_output

    government_payment_share = sliding_premium * pyrolysis_electricity_output

    electricity_market_payment_euro = feed_in_revenue - government_payment_share

    # calculate payment sums
    sum_government_payment_share = government_payment_share.sum()
    sum_feed_in_revenue = feed_in_revenue.sum()
    sum_electricity_market_payment_euro = electricity_market_payment_euro.sum()

    # create csv file with payment sums
    df2 = pd.DataFrame({})

    sum_dict = {
        "government_payment_share (euro)": sum_government_payment_share,
        "electricity_market_payment_share (euro)": sum_electricity_market_payment_euro,
        "revenue_fed_in_electricity (euro)": sum_feed_in_revenue,
    }
    revenue_sums = add_items_to_scalar_results(sum_dict, "sum", df2.copy())

    revenue_sums.to_csv("preprocessing/electricity_revenue_data.csv", index=False, sep=";")


def main(scenario: str, electricity_prices_path: str, input_data_path) -> None:
    (
        electricity_price_euro_per_kwh,
        pyrolysis_electricity_output,
        base_value,
        lower_threshold,
    ) = receive_data(scenario, electricity_prices_path, input_data_path)

    calculate_payment_sums(
        electricity_price_euro_per_kwh, pyrolysis_electricity_output, base_value, lower_threshold
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--scenario",
        required=True,
        help="Name of the scenario, e.g. --scenario stromflex_h2 ",
    )

    args = parser.parse_args()

    input_data_path = "input_data.xlsx"
    electricity_prices_path = "preprocessing/Gro_handelspreise_202501010000_202601010000_Stunde.csv"
    main(args.scenario, electricity_prices_path, input_data_path)
