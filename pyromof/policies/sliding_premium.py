import argparse

import pandas as pd


def receive_base_value_and_lower_threshold(scenario: str) -> float:
    path = f"results/{scenario}/meta_info/input_data.xlsx"
    policies = pd.read_excel(path, sheet_name="policies")
    base_value = policies.loc[policies["policy"] == "Sliding premium", "value 1"].values[0]
    lower_threshold = policies.loc[policies["policy"] == "Sliding premium", "value 2"].values[0]
    return float(base_value), float(lower_threshold)


def receive_scenario_electricity_data(scenario: str) -> pd.Series:
    file_path = f"./results/{scenario}/results/sequences.csv"
    separator = ";"
    parse_dates = True
    target_column = "b_electricity to electricity_grid"

    data = pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)
    return data[target_column]


def receive_and_refine_electricity_price_data():
    data_file = pd.read_csv(
        "preprocessing/Gro_handelspreise_202501010000_202601010000_Stunde.csv",
        sep=";",
        parse_dates=True,
    )
    raw_data = data_file["Deutschland/Luxemburg [€/MWh] Berechnete Auflösungen"]

    data_replace_comma = raw_data.copy().str.replace(",", ".")

    data_float = data_replace_comma.astype(float)

    electricity_price_cent_per_kWh = data_float.copy() / -10
    electricity_price_euro_per_kWh = data_float.copy() / -1000

    result_df = pd.DataFrame({
        "cent_per_kWh": electricity_price_cent_per_kWh,
        "euro_per_kWh": electricity_price_euro_per_kWh
    })
    return result_df


def feed_in_payment_cent_per_kWh(electricity_price_cent_per_kWh, base_value, lower_threshold):
    """

    This function calculates the feed-in payment for each hour in cent per kWh.

    Based on the electricity price data, base value, and lower threshold.

    The feed-in payment is the base_value if:

    The electricity price is above the lower threshold and below the base value.

    Otherwise the feed_in payment is the electricity price.
    """

    feed_in_payment_cent_per_kWh = []

    for i in range(len(electricity_price_cent_per_kWh)):
        if (
            electricity_price_cent_per_kWh.iloc[i] > lower_threshold
            and electricity_price_cent_per_kWh.iloc[i] <= base_value
        ):
            feed_in_payment_cent_per_kWh.append(base_value)

        elif (
            electricity_price_cent_per_kWh.iloc[i] > base_value
            or electricity_price_cent_per_kWh.iloc[i] <= lower_threshold
        ):
            feed_in_payment_cent_per_kWh.append(electricity_price_cent_per_kWh.iloc[i])

    return pd.Series(feed_in_payment_cent_per_kWh, index=electricity_price_cent_per_kWh.index)


def government_payment_cent_per_kWh(
    electricity_price_cent_per_kWh, feed_in_payment_cent_per_kWh, base_value
):
    """
    This function calculates the government payment share of the feed-in premium in cent per kWh.

    The goverment payment share is calculated as:

    feed_in_payment (cent/kWh) - electricity price (cent/kWh)

    As long as the electricity price ist between lower threshold and base value.

    Otherwise the government payment share is zero.

    This is further explained in the feed_in_payment function.

    """

    payments = []

    for i in range(len(feed_in_payment_cent_per_kWh)):
        if feed_in_payment_cent_per_kWh.iloc[i] == base_value:
            payments.append(
                feed_in_payment_cent_per_kWh.iloc[i] - electricity_price_cent_per_kWh.iloc[i]
            )

        elif feed_in_payment_cent_per_kWh.iloc[i] != base_value:
            payments.append(0)

    return pd.Series(payments, index=feed_in_payment_cent_per_kWh.index)


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
    """
    This function receives and refines all necessary input data based on the functions defined above

    The input data depend on the given scenario.

    """
    base_value, lower_threshold = receive_base_value_and_lower_threshold(scenario)

    electricity_price_data = receive_and_refine_electricity_price_data()
    electricity_price_cent_per_kWh = electricity_price_data["cent_per_kWh"]
    electricity_price_euro_per_kWh = electricity_price_data["euro_per_kWh"]


    pyrolysis_electricity_to_grid_kWh = receive_scenario_electricity_data(scenario)

    return (
        base_value,
        lower_threshold,
        electricity_price_cent_per_kWh,
        electricity_price_euro_per_kWh,
        pyrolysis_electricity_to_grid_kWh,
    )


def calculate_payments(
    electricity_price_cent_per_kWh,
    base_value,
    lower_treshold,
    pyrolysis_electricity_to_grid_kWh,
):
    """
    This function calculates the various payments and payment shares in cent/kWh and euro.

    The input data is the output of the receive_and_refine_all_data function.

    """
    feed_in_revenue_cent_per_kWh = feed_in_payment_cent_per_kWh(
        electricity_price_cent_per_kWh.copy(), base_value, lower_treshold
    )

    government_payment_share_cent_per_kWh = government_payment_cent_per_kWh(
        electricity_price_cent_per_kWh.copy(),
        feed_in_revenue_cent_per_kWh.copy(),
        base_value,
    )

    revenue_fed_in_electricity_euro = calc_payments_in_euro(
        feed_in_revenue_cent_per_kWh.copy(), pyrolysis_electricity_to_grid_kWh.copy()
    )

    government_payment_for_fed_in_electricity_euro = calc_payments_in_euro(
        government_payment_share_cent_per_kWh.copy(), pyrolysis_electricity_to_grid_kWh.copy()
    )

    electricity_market_payment_euro = (
        revenue_fed_in_electricity_euro.copy()
        - government_payment_for_fed_in_electricity_euro.copy()
    )

    return (
        feed_in_revenue_cent_per_kWh,
        government_payment_share_cent_per_kWh,
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
    electricity_price_cent_per_kWh,
    electricity_price_euro_per_kWh,
    feed_in_revenue_cent_per_kWh,
    government_payment_share_cent_per_kWh,
    pyrolysis_electricity_to_grid_kWh,
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
            "electricity_price (cent/kWh)": electricity_price_cent_per_kWh.round(2),
            "electricity_price (euro/kWh)": electricity_price_euro_per_kWh.round(4),
            "feed_in_payment (cent/kWh)": feed_in_revenue_cent_per_kWh.round(2),
            "government_payment_share (cent/kWh)": government_payment_share_cent_per_kWh.round(2),
            "pyrolysis_electricity_to_grid (kWh)": pyrolysis_electricity_to_grid_kWh.round(2),
            "revenue_fed_in_electricity (euro)": revenue_fed_in_electricity_euro.round(),
            "government_payment_share (euro)": government_payment_for_fed_in_electricity_euro.round(),
            "electricity_market_payment_share (euro)": electricity_market_payment_euro.round(),
        }
    )

    #df = df.round(2)

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
        base_value,
        lower_treshold,
        electricity_price_cent_per_kWh,
        electricity_price_euro_per_kWh,
        pyrolysis_electricity_to_grid_kWh,
    ) = receive_and_refine_all_data(scenario)

    (
        feed_in_revenue_cent_per_kWh,
        government_payment_share_cent_per_kWh,
        revenue_fed_in_electricity_euro,
        government_payment_for_fed_in_electricity_euro,
        electricity_market_payment_euro,
    ) = calculate_payments(
        electricity_price_cent_per_kWh,
        base_value,
        lower_treshold,
        pyrolysis_electricity_to_grid_kWh,
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
        electricity_price_cent_per_kWh,
        electricity_price_euro_per_kWh,
        feed_in_revenue_cent_per_kWh,
        government_payment_share_cent_per_kWh,
        pyrolysis_electricity_to_grid_kWh,
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
