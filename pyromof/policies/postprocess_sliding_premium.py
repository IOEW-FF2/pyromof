from pyromof.policies.implement_policies import (
    feed_in_payment_sliding_premium,
    receive_higher_threshold_basis_and_lower_threshold_basis,
)
from pyromof.policies.postprocess_policies_functions import receive_data
from pyromof.preprocessing_functions import preprocessing_input_data


def postprocess_sliding_premium(scenario, data):

    # receive input data
    electricity_price, pyrolysis_electricity_output, policies = receive_data(scenario, data)
    base_value, lower_threshold = receive_higher_threshold_basis_and_lower_threshold_basis(policies)

    # calculate sliding premium and revenue per kwh
    feed_in_revenue_euro_per_kwh, sliding_premium, _ = feed_in_payment_sliding_premium(
        electricity_price,
        base_value,
        lower_threshold,
    )

    # calculate payments
    feed_in_revenue = feed_in_revenue_euro_per_kwh * pyrolysis_electricity_output

    government_payment = sliding_premium * pyrolysis_electricity_output

    market_payment = feed_in_revenue - government_payment

    # calculate payment sums
    sum_government_payment = government_payment.sum().round(1)
    sum_feed_in_revenue = feed_in_revenue.sum().round(1)
    sum_market_payment = market_payment.sum().round(1)
    print(sum_feed_in_revenue, sum_government_payment, sum_market_payment)
    return sum_feed_in_revenue, sum_government_payment, sum_market_payment


if __name__ == "__main__":
    data, time, scenario = preprocessing_input_data.preprocess("input_data.xlsx")
    postprocess_sliding_premium(scenario, data)
