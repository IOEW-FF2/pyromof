import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd

from pyromof.policies.implement_policies import feed_in_payment_sliding_premium


def receive_test_data(path):

    # receive data sheets
    electricity_data_sheet = pd.read_excel(path, sheet_name="electricity_data")
    timestamps = pd.to_datetime(electricity_data_sheet["Datum"], format="%d.%m.%Y %H:%M")
    monthly_premium_sheet = pd.read_excel(path, sheet_name="monthly_premium")
    threshold_data = pd.read_excel(path, sheet_name="threshold_data")

    # receive base value and lower threshold
    base_value_1 = (
        -1
        / 100
        * threshold_data.loc[threshold_data["threshold_data"] == "base_value_1", "value"].values[0]
    )

    lower_threshold = -0.02

    # receive and refine monthly average electricity price template
    monthly_average_electricity_price_template = (
        -1 / 100 * monthly_premium_sheet["electricity_price_mean_monthly"]
    )
    monthly_average_electricity_price_template = monthly_average_electricity_price_template.round(4)

    # receive and refine hourly electricity price
    electricity_price_data = -1 / 100 * electricity_data_sheet["electricity_price"]
    electricity_price_data.index = timestamps

    # receive and refine sliding premium template
    sliding_premium_1_template = -1 / 100 * electricity_data_sheet["sliding_premium_1"].round(4)
    sliding_premium_1_template = sliding_premium_1_template.reset_index(drop=True)

    # reveive and refine total revenue
    total_revenue_1_template = -1 / 100 * electricity_data_sheet["total_revenue_1"]
    total_revenue_1_template = total_revenue_1_template.round(4)
    total_revenue_1_template = total_revenue_1_template.reset_index(drop=True)

    return (
        base_value_1,
        lower_threshold,
        electricity_price_data,
        sliding_premium_1_template,
        monthly_average_electricity_price_template,
        total_revenue_1_template,
    )


(
    base_value_1,
    lower_threshold,
    electricity_price_data,
    sliding_premium_1_template,
    monthly_average_electricity_price_template,
    total_revenue_1_template,
) = receive_test_data("tests/files/test_data_feed_in_electricity_sliding_premium.xlsm")


total_revenue_1_test, sliding_premium_1_test, monthly_average_price_1 = (
    feed_in_payment_sliding_premium(electricity_price_data, base_value_1, lower_threshold)
)


# average monthly electricity price test

monthly_average_electricity_price_test = (
    monthly_average_price_1.groupby(monthly_average_price_1.index.to_period("M")).first().round(4)
)
if np.allclose(
    monthly_average_electricity_price_test.to_numpy(),
    monthly_average_electricity_price_template.to_numpy(),
):
    print("monthly average price test passed")
else:
    print(
        f"monthly average electricity price test not passed: \
        monthly average price tamplate:\
        {monthly_average_electricity_price_template}\
        monthly average price test: \
        {monthly_average_electricity_price_test}"
    )


# sliding premium test

sliding_premium_1_test = sliding_premium_1_test.round(4)
sliding_premium_1_test = sliding_premium_1_test.reset_index(drop=True)

if np.allclose(
    sliding_premium_1_template.to_numpy()[:1000], sliding_premium_1_test.to_numpy()[:1000]
):
    print("sliding premium test 1 passed!")

else:
    print("sliding premium test failed!")

# total revenue test
total_revenue_1_test = total_revenue_1_test.round(4)
total_revenue_1_test = total_revenue_1_test.reset_index(drop=True)

if np.allclose(
    total_revenue_1_template.to_numpy()[:1000], total_revenue_1_test.to_numpy()[:1000], atol=1e-4
):
    print("total revenue test passed!")

else:
    print("total revenue test failed!")
