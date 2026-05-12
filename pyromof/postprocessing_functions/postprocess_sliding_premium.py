from pyromof.postprocessing_functions.postprocess_policies_functions import receive_data
from pyromof.preprocessing_functions import implement_preprocessing_input_data_functions
from pyromof.preprocessing_functions.preprocess_implement_policies import (
    feed_in_payment_sliding_premium,
)


def postprocess_sliding_premium(scenario, data):

    # receive input data
    _, pyrolysis_electricity_output, _ = receive_data(scenario, data)
    feed_in_revenue_euro_per_kwh, sliding_premium, _ = feed_in_payment_sliding_premium(data)

    # calculate payments
    feed_in_revenue = feed_in_revenue_euro_per_kwh * pyrolysis_electricity_output

    government_payment = sliding_premium * pyrolysis_electricity_output

    market_payment = feed_in_revenue - government_payment

    # calculate payment sums
    sum_government_payment = government_payment.sum().round(1)
    sum_feed_in_revenue = feed_in_revenue.sum().round(1)
    sum_market_payment = market_payment.sum().round(1)
    return {
        "feed_in_revenue": sum_feed_in_revenue,
        "government_payment": sum_government_payment,
        "market_payment": sum_market_payment,
    }


if __name__ == "__main__":
    data, time, scenario = implement_preprocessing_input_data_functions.preprocess(
        "input_data.xlsx"
    )
    postprocess_sliding_premium(scenario, data)
