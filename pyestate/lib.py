import pandas as pd

def fixed_rate_amortization(principal, interest, n_payments, payments_per_year=12):
	"""
	Returns an NX2 matrix where the Nth row has the principal and interest
	payments of a fixed rate loan.

	Equation is as follows:
	Total payment = principal * i*(1+i)^N / ((1+i)^N - 1)
	Interest payment = principal * i
	Principal Payment = principal - interest payment

	Interest value is annualized.
	Returns a dataframe.  Principal Remaining refers to the start of the month (or payment interval).
	"""
	# per interval interest that annualizes to the 'interest' variable.
	per_interval_interest = (1. + interest) ** (1. / payments_per_year) - 1.

	# note these formulas take per interval interest rate not annualized.
	mult = (1. + per_interval_interest) ** (n_payments)
	total = principal * per_interval_interest * mult / (mult - 1)

	# there may be a single-shot analytical way to compute these, but n_payments isnt a large number
	princ = principal
	data = []
	for n in range(n_payments):
		interest_payment = princ * per_interval_interest
		principal_payoff = total - interest_payment
		data.append([n, interest_payment, principal_payoff, princ])
		princ -= principal_payoff
	return pd.DataFrame(data, columns=['payment_n', 'interest_payment', 'principal_payment', 'principal_remaining'])
