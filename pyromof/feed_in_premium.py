import pandas as pd

# define function to find cell value in excel file based on column name and row name


def find_cell_value_excel(
    file_path: str,
    excel_sheet: str,
    target_column: str,
    column_for_target_row: str,
    target_row: str,
):
    data = pd.read_excel(file_path, sheet_name=excel_sheet)
    row_index = data[data[column_for_target_row] == target_row].index[0]
    cell_value = data.loc[row_index, target_column]
    return float(cell_value)


# define function to get electricity price data


def get_data_csv(
    file_path: str,
    separator: str,
    parse_dates: bool,
    target_column: str,
):

    data = pd.read_csv(file_path, sep=separator, parse_dates=parse_dates)
    return data[target_column]


# define function to refine received electricity price data


def refine_received_electricity_price_data(raw_data: any):
    data_replace_comma = raw_data.copy().str.replace(",", ".")
    data_float = data_replace_comma.astype(float)
    data_cent_per_kWh = data_float.copy() / 10
    return data_cent_per_kWh


# define function to calculate feed-in feed_in_payment


def feed_in_payment(electricity_price, base_value, lower_treshold):

    feed_in_payments = []
    for i in range(len(electricity_price)):
        if (
            electricity_price.iloc[i] > lower_treshold
            and electricity_price.iloc[i] <= base_value
        ):
            feed_in_payments.append(base_value)
        elif (
            electricity_price.iloc[i] > base_value
            or electricity_price.iloc[i] <= lower_treshold
        ):
            feed_in_payments.append(electricity_price.iloc[i])
    return pd.Series(feed_in_payments, index=electricity_price.index)


# define function to calulate government payment share for feed-in premium


def government_payment(electricity_price, feed_in_payment, base_value):
    payments = []
    for i in range(len(feed_in_payment)):
        if feed_in_payment.iloc[i] == base_value:
            payments.append(feed_in_payment.iloc[i] - electricity_price.iloc[i])
        elif feed_in_payment.iloc[i] != base_value:
            payments.append(0)
    return pd.Series(payments, index=feed_in_payment.index)


# define multiplying function


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


# receive and refine data


# get values for feed-in premium from excel file

base_value = find_cell_value_excel(
    file_path="results/stromflex_h2/meta_info/input_data.xlsx",
    excel_sheet="policies",
    target_column="value 1",
    column_for_target_row="policy",
    target_row="Sliding premium",
)

lower_treshold = find_cell_value_excel(
    file_path="results/stromflex_h2/meta_info/input_data.xlsx",
    excel_sheet="policies",
    target_column="value 2",
    column_for_target_row="policy",
    target_row="Sliding premium",
)

print(f"base_value = {base_value}, lower_treshold = {lower_treshold}")


# receive and refinde data for electricity price

electricity_price_data_germany_euro_per_MWh = get_data_csv(
    file_path="preprocessing/Gro_handelspreise_202501010000_202601010000_Stunde.csv",
    separator=";",
    parse_dates=True,
    target_column="Deutschland/Luxemburg [€/MWh] Berechnete Auflösungen",
)

electricity_price_data_germany_cent_per_kWh = refine_received_electricity_price_data(
    electricity_price_data_germany_euro_per_MWh.copy()
)


# receive data for electricity_to_grid from pyrolysis plant

pyrolysis_electricity_to_grid = get_data_csv(
    file_path="results/stromflex_h2/results/sequences.csv",
    separator=";",
    parse_dates=True,
    target_column="b_electricity to electricity_grid",
)

print(
    f"first 10 columns of the pyrolysis electricity to grid data: \n{pyrolysis_electricity_to_grid.head(10)}"
)


# create new data


# create data for received feed_in_payment (cent/kWh)

feed_in_payment_series = feed_in_payment(
    electricity_price_data_germany_cent_per_kWh.copy(), base_value, lower_treshold
)


# create data for government payment to renewable energy producers (cent/kWh)

government_payment_share = government_payment(
    electricity_price_data_germany_cent_per_kWh.copy(),
    feed_in_payment_series.copy(),
    base_value,
)


# calculate received payment for electricity fed into the grid (euro)

received_payment_series = (
    1
    / 100
    * multiply(feed_in_payment_series.copy(), pyrolysis_electricity_to_grid.copy())
)


# calculate payment share of government for electricity from the pyrolysis plant (euro)

government_payment_for_pyrolysis_plant = (
    1
    / 100
    * multiply(government_payment_share.copy(), pyrolysis_electricity_to_grid.copy())
)


# calculate payment share of electricity market for electricity from the pyrolysis plant

electricity_market_payment_for_pyrolysis_plant = (
    received_payment_series.copy() - government_payment_for_pyrolysis_plant.copy()
)


# calculate sums
sum_received_payment = received_payment_series.sum()
sum_government_payment = government_payment_for_pyrolysis_plant.sum()
sum_electricity_market_payment = electricity_market_payment_for_pyrolysis_plant.sum()


# create csv file for feed_in_premium_data

df = pd.DataFrame(
    {
        "electricity_price (cent/kWh)": electricity_price_data_germany_cent_per_kWh,
        "feed_in_payment (cent/kWh)": feed_in_payment_series,
        "government_payment_share (cent/kWh)": government_payment_share,
        "pyrolysis_electricity_to_grid (kWh)": pyrolysis_electricity_to_grid,
        "received_payment (euro)": received_payment_series,
        "government_payment_share (euro)": government_payment_for_pyrolysis_plant,
        "electricity_market_payment_share (euro)": electricity_market_payment_for_pyrolysis_plant,
    }
)

df = df.round(1)
df.to_csv("preprocessing/feed_in_premium_data.csv", index=False, sep=";")
print(f"first 20 columns of the data sheet: \n{df.head(20)}")


# create csv file for electricity_revenue_data

df2 = pd.DataFrame(
    {
        "government_payment_share (euro)": government_payment_for_pyrolysis_plant,
        "electricity_market_payment_share (euro)": electricity_market_payment_for_pyrolysis_plant,
        "received_payment (euro)": received_payment_series,
    }
)
df2 = df2.round(1)


# create dict with sums for payments

sum_dict = {
    "government_payment_share (euro)": sum_government_payment,
    "electricity_market_payment_share (euro)": sum_electricity_market_payment,
    "received_payment (euro)": sum_received_payment,
}

# add sums to df2
df2_with_sum = add_items_to_scalar_results(sum_dict, "sum", df2.copy())
df2_with_sum.to_csv("preprocessing/electricity_revenue_data.csv", index=False, sep=";")


# check if sums are correct
print("check if sum is correct:")
print(f"total sum: {sum_received_payment.round(1)} euro")
print(
    f"government payment + electricity market payment: \n"
    f"{sum_government_payment.round(1) + sum_electricity_market_payment.round(1)} euro"
)

exit()
