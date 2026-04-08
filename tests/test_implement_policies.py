import matplotlib

matplotlib.use("Agg")
import pandas as pd

from pyromof.policies.implement_policies import feed_in_payment_sliding_premium

path = "test_data_feed_in_electricity_sliding_premium.xlsm"

electricity_data_sheet = pd.read_excel(path, sheet_name="electricity_data")
threshold_data = pd.read_excel(path, sheet_name="threshold_data")

lower_threshold_basis = threshold_data.loc[
    threshold_data["threshold_data"] == "lower_treshold_basis", "value"
].values[0]
higher_threshold_basis = threshold_data.loc[
    threshold_data["threshold_data"] == "higher_treshold_basis", "value"
].values[0]

electricity_price_data = -electricity_data_sheet["electricity_price"]

feed_in_payment_euro_per_kwh, sliding_premium = feed_in_payment_sliding_premium(
    electricity_price_data, higher_threshold_basis, lower_threshold_basis
)

