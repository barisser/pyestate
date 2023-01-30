import numpy as np

import pyestate


def test_fixed_rate_schedule():
	schedule = pyestate.lib.fixed_rate_amortization(1e6, 0.05, 360)
	assert len(schedule) == 360

	# loan gets paid off
	assert abs(schedule.iloc[-1].principal_remaining - schedule.iloc[-1].principal_payment) < 0.01
	assert np.isclose(schedule.principal_payment.sum(), 1e6)

	assert len(schedule[schedule.principal_payment < 0]) == 0


	# semiannually now not monthly, numbers will slightly differ
	schedule2 = pyestate.lib.fixed_rate_amortization(1e6, 0.05, 60, payments_per_year=2)

	assert abs(schedule2.iloc[-1].principal_remaining - schedule2.iloc[-1].principal_payment) < 0.01
	assert np.isclose(schedule2.principal_payment.sum(), 1e6)
	assert len(schedule2) == 60
	assert len(schedule2[schedule2.principal_payment < 0]) == 0

	# first one pays slightly less interest than second
	assert schedule.interest_payment.sum() < schedule2.interest_payment.sum()

def test_payment_schedule():
	asset_price = 3e5
	LTV = 0.75
	interest = 0.05
	n_payments = 360
	property_tax_rate = 0.022
	property_growth_rate = 0.02
	payments = pyestate.lib.payment_schedule(asset_price, LTV, interest, n_payments, 
		property_tax_rate, property_growth_rate, payments_per_year=12)

	# TODO

def test_schedule():
	asset_price = 3e5
	LTV = 0.75
	interest = 0.06
	n_payments = 360
	property_tax_rate = 0.022
	property_growth_rate = 0.03
	rent_growth_rate = 0.02
	starting_rent = 1800
	schedule = pyestate.lib.financial_schedule(asset_price, LTV, interest, n_payments, property_tax_rate, property_growth_rate,
		rent_growth_rate, starting_rent)
	assert False