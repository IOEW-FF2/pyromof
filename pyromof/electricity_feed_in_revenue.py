import argparse

import pandas as pd


def receive_base_value_and_lower_treshold(scenario: str, target_column: str):
    """
    Read base value and lower treshold from input data Excel file."""
    file_path = f"results/{scenario}/meta_info/input_data.xlsx"
    excel_sheet = "policies"
    target_column = target_column
    column_for_target_row = "policy"
    target_row = "Sliding premium"

    data = pd.read_excel(file_path, excel_sheet)

    row_index = data[data[column_for_target_row] == target_row].index[0]

    cell_value = data.loc[row_index, target_column]

    return float(cell_value)


def get_data_csv(
    file_path: str,
    separator: str,
    parse_dates: bool,
    target_column: str,
):
    data = pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)

    return data[target_column]


def get_scenario_electricity_data(scenario: str) -> pd.Series:

    file_path = f"./results/{scenario}/results/sequences.csv"
    separator = ";"
    parse_dates = True
    target_column = "b_electricity to electricity_grid"

    data = pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)
    return data[target_column]


def receive_and_refine_electricity_price_data():
    """Function to receive and refine electricity price data for Germany"""

    raw_data = get_data_csv(
        file_path="preprocessing/Gro_handelspreise_202501010000_202601010000_Stunde.csv",
        separator=";",
        parse_dates=True,
        target_column="Deutschland/Luxemburg [€/MWh] Berechnete Auflösungen",
    )
    data_replace_comma = raw_data.copy().str.replace(",", ".")

    data_float = data_replace_comma.astype(float)

    data_cent_per_kWh = data_float.copy() / 10

    return data_cent_per_kWh


def feed_in_payment(electricity_price, base_value, lower_treshold):
    """

    This function calculates the feed-in payment for each hour.

    Based on the electricity price, base value, and lower treshold of the sliding premium.

    """

    feed_in_payments = []

    for i in range(len(electricity_price)):
        if electricity_price.iloc[i] > lower_treshold and electricity_price.iloc[i] <= base_value:
            feed_in_payments.append(base_value)

        elif electricity_price.iloc[i] > base_value or electricity_price.iloc[i] <= lower_treshold:
            feed_in_payments.append(electricity_price.iloc[i])

    return pd.Series(feed_in_payments, index=electricity_price.index)


def government_payment(electricity_price, feed_in_payment, base_value):
    """
    This function calculates the government payment share of the feed-in premium.

    """
    payments = []

    for i in range(len(feed_in_payment)):
        if feed_in_payment.iloc[i] == base_value:
            payments.append(feed_in_payment.iloc[i] - electricity_price.iloc[i])

        elif feed_in_payment.iloc[i] != base_value:
            payments.append(0)

    return pd.Series(payments, index=feed_in_payment.index)


def calc_payments_in_euro(a, b):

    return 1 / 100 * a * b


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
    base_value = receive_base_value_and_lower_treshold(scenario, target_column="value 1")
    lower_treshold = receive_base_value_and_lower_treshold(scenario, target_column="value 2")

    electricity_price_data_germany_cent_per_kWh = receive_and_refine_electricity_price_data()
    pyrolysis_electricity_to_grid = get_scenario_electricity_data(scenario)

    return (
        base_value,
        lower_treshold,
        electricity_price_data_germany_cent_per_kWh,
        pyrolysis_electricity_to_grid,
    )


def calculate_payments(
    electricity_price_data_germany_cent_per_kWh,
    base_value,
    lower_treshold,
    pyrolysis_electricity_to_grid,
):

    feed_in_revenue = feed_in_payment(
        electricity_price_data_germany_cent_per_kWh.copy(), base_value, lower_treshold
    )

    government_payment_share = government_payment(
        electricity_price_data_germany_cent_per_kWh.copy(),
        feed_in_revenue.copy(),
        base_value,
    )

    received_payment = calc_payments_in_euro(
        feed_in_revenue.copy(), pyrolysis_electricity_to_grid.copy()
    )

    government_payment_for_pyrolysis_plant = calc_payments_in_euro(
        government_payment_share.copy(), pyrolysis_electricity_to_grid.copy()
    )

    electricity_market_payment_euro = (
        received_payment.copy() - government_payment_for_pyrolysis_plant.copy()
    )

    return (
        feed_in_revenue,
        government_payment_share,
        received_payment,
        government_payment_for_pyrolysis_plant,
        electricity_market_payment_euro,
    )


def calc_payment_sums(
    received_payment,
    government_payment_for_pyrolysis_plant,
    electricity_market_payment_euro,
):

    sum_received_payment = received_payment.sum()

    sum_government_payment = government_payment_for_pyrolysis_plant.sum()

    sum_electricity_market_payment = electricity_market_payment_euro.sum()

    return sum_received_payment, sum_government_payment, sum_electricity_market_payment


def create_csv_file_for_created_data(
    electricity_price_data_germany_cent_per_kWh,
    feed_in_revenue,
    government_payment_share,
    pyrolysis_electricity_to_grid,
    received_payment,
    government_payment_for_pyrolysis_plant,
    electricity_market_payment_euro,
    sum_government_payment,
    sum_electricity_market_payment,
    sum_received_payment,
):

    df = pd.DataFrame(
        {
            "electricity_price (cent/kWh)": electricity_price_data_germany_cent_per_kWh,
            "feed_in_payment (cent/kWh)": feed_in_revenue,
            "government_payment_share (cent/kWh)": government_payment_share,
            "pyrolysis_electricity_to_grid (kWh)": pyrolysis_electricity_to_grid,
            "received_payment (euro)": received_payment,
            "government_payment_share (euro)": government_payment_for_pyrolysis_plant,
            "electricity_market_payment_share (euro)": electricity_market_payment_euro,
        }
    )

    df = df.round(1)

    df.to_csv("preprocessing/feed_in_premium_data.csv", index=False, sep=";")

    df2 = pd.DataFrame(
        {
            "government_payment_share (euro)": government_payment_for_pyrolysis_plant,
            "electricity_market_payment_share (euro)": electricity_market_payment_euro,
            "received_payment (euro)": received_payment,
        }
    )

    df2 = df2.round(1)

    sum_dict = {
        "government_payment_share (euro)": sum_government_payment,
        "electricity_market_payment_share (euro)": sum_electricity_market_payment,
        "received_payment (euro)": sum_received_payment,
    }

    df2_with_sum = add_items_to_scalar_results(sum_dict, "sum", df2.copy())

    df2_with_sum.to_csv("preprocessing/electricity_revenue_data.csv", index=False, sep=";")

    print("check if sum is correct:")

    print(f"total sum: {sum_received_payment.round(1)} euro")

    print(
        f"government payment + electricity market payment: \n"
        f"{sum_government_payment.round(1) + sum_electricity_market_payment.round(1)} euro"
    )


def main(scenario: str) -> None:
    (
        base_value,
        lower_treshold,
        electricity_price_data_germany_cent_per_kWh,
        pyrolysis_electricity_to_grid,
    ) = receive_and_refine_all_data(scenario)

    (
        feed_in_revenue,
        government_payment_share,
        received_payment,
        government_payment_for_pyrolysis_plant,
        electricity_market_payment_euro,
    ) = calculate_payments(
        electricity_price_data_germany_cent_per_kWh,
        base_value,
        lower_treshold,
        pyrolysis_electricity_to_grid,
    )

    (
        sum_received_payment,
        sum_government_payment,
        sum_electricity_market_payment,
    ) = calc_payment_sums(
        received_payment,
        government_payment_for_pyrolysis_plant,
        electricity_market_payment_euro,
    )

    create_csv_file_for_created_data(
        electricity_price_data_germany_cent_per_kWh,
        feed_in_revenue,
        government_payment_share,
        pyrolysis_electricity_to_grid,
        received_payment,
        government_payment_for_pyrolysis_plant,
        electricity_market_payment_euro,
        sum_government_payment,
        sum_electricity_market_payment,
        sum_received_payment,
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
