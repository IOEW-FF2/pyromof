from pyromof.postprocessing_functions.postprocess_policies_functions import (
    receive_data,
)
from pyromof.preprocessing_functions import preprocessing_input_data


def postprocess_feed_in_tariff(scenario, data):

    electricity_price, pyrolysis_electricity_output, policies = receive_data(scenario, data)

    feed_in_tarrif = (
        -1 / 100 * policies.loc[policies["policy"] == "feed in tariff", "value 1"].values[0]
    )
    government_payment_share = feed_in_tarrif - electricity_price

    feed_in_revenue = feed_in_tarrif * pyrolysis_electricity_output
    governemt_payment = government_payment_share * pyrolysis_electricity_output
    market_payment = electricity_price * pyrolysis_electricity_output

    sum_feed_in_revenue = feed_in_revenue.sum().round(1)
    sum_government_payment = governemt_payment.sum().round(1)
    sum_market_payment = market_payment.sum().round(1)
    return {
        "feed_in_revenue": sum_feed_in_revenue,
        "government_payment": sum_government_payment,
        "market_payment": sum_market_payment,
    }


if __name__ == "__main__":
    data, time, scenario = preprocessing_input_data.preprocess("input_data.xlsx")
    postprocess_feed_in_tariff(scenario, data)
