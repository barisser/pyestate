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
