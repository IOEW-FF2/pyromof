import pandas as pd

from pyromof.electricity_feed_in_revenue import (
	calculate_payments,
	calc_payments_in_euro,
	feed_in_payment_cent_per_kWh,
	government_payment_cent_per_kWh,
)


def test_feed_in_payment_boundaries_lower_threshold_and_base_value():
	lower_threshold = 4.0
	base_value = 8.0
	prices = pd.Series([3.9, 4.0, 4.1, 8.0, 8.1])

	result = feed_in_payment_cent_per_kWh(prices, base_value, lower_threshold)

	expected = pd.Series([3.9, 4.0, 8.0, 8.0, 8.1], index=prices.index)
	pd.testing.assert_series_equal(result, expected)


def test_government_payment_only_when_feed_in_equals_base_value():
	base_value = 8.0
	electricity_price = pd.Series([3.5, 4.2, 7.5, 8.1])
	feed_in_payment = pd.Series([8.0, 8.0, 7.5, 8.1])

	result = government_payment_cent_per_kWh(
		electricity_price,
		feed_in_payment,
		base_value,
	)

	expected = pd.Series([4.5, 3.8, 0.0, 0.0], index=electricity_price.index)
	pd.testing.assert_series_equal(result, expected)


def test_calc_payments_in_euro_with_known_numbers():
	# 10 cent/kWh * 5 kWh = 50 cent = 0.5 euro
	a = pd.Series([10.0, 20.0, 0.0])
	b = pd.Series([5.0, 2.0, 7.0])

	result = calc_payments_in_euro(a, b)

	expected = pd.Series([0.5, 0.4, 0.0])
	pd.testing.assert_series_equal(result, expected)


def test_calculate_payments_revenue_equals_government_plus_market_per_timestep():
	electricity_price_cent_per_kWh = pd.Series([3.0, 6.0, 10.0])
	base_value = 8.0
	lower_treshold = 4.0
	pyrolysis_electricity_to_grid_kWh = pd.Series([10.0, 20.0, 30.0])

	(
		_,
		_,
		revenue_fed_in_electricity_euro,
		government_payment_for_fed_in_electricity_euro,
		electricity_market_payment_euro,
	) = calculate_payments(
		electricity_price_cent_per_kWh,
		base_value,
		lower_treshold,
		pyrolysis_electricity_to_grid_kWh,
	)

	pd.testing.assert_series_equal(
		revenue_fed_in_electricity_euro,
		government_payment_for_fed_in_electricity_euro + electricity_market_payment_euro,
	)
