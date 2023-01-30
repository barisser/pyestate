import numpy as np
import pandas as pd


def fixed_rate_amortization(principal, interest, n_payments, payments_per_year=12):
	"""
	Returns a pandas dataframe with payment and principal balance data for a fixed
	rate interest amortization schedule.

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


def payment_schedule(asset_price, LTV, interest, n_payments, property_tax_rate,
	property_growth_rate, payments_per_year=12):
	"""
	Computes payments including mortgage + property taxes.  Assumes fixed rate interest.
	Assumes that the assessed value == asset price.
	LTV is loan to value == loan value / asset_price
	
	We assume fixed interest and property tax rate and property growth rates.  In the future
	we will modify these to accept timeseries arrays.  As scalars these are assumed to be annual figures.
	"""
	debt = LTV * asset_price
	payments = fixed_rate_amortization(debt, interest, n_payments, payments_per_year=payments_per_year)

	per_interval_growth = (1. + property_growth_rate) ** (1. / 12.)
	payments['property_value'] = asset_price * np.logspace(0, n_payments-1, n_payments, base=per_interval_growth)
	payments['property_tax_payment'] = payments['property_value'] * property_tax_rate / 12. # this is never geometric
	payments['total_payment'] = payments['property_tax_payment'] + payments['interest_payment']  + payments['principal_payment']

	return payments

def income_schedule(starting_rent, expected_rent_growth_rate, n):
	# TODO add vacancy rate.  Maybe these should be stochastic events and not smooth!
	per_interval_rent_growth = (1. + expected_rent_growth_rate) ** (1. / 12.)
	return starting_rent * np.logspace(0, n-1, n, base=per_interval_rent_growth)

def financial_schedule(asset_price, LTV, interest, n_payments, property_tax_rate, property_growth_rate,
	rent_growth_rate, starting_rent, building_assessed_fraction=0.5, depreciation_schedule=27.5,
	personal_tax_rate=0.3):
	"""
	Building assessed fraction is for calculating tax depreciation.  It is the fraction of the asset value
	that can be depreciated.
	"""
	data = payment_schedule(asset_price, LTV, interest, n_payments, property_tax_rate,
		property_growth_rate)
	data['revenue'] = income_schedule(starting_rent, rent_growth_rate, n_payments)

	data['cashflow'] = data['revenue'] - data['total_payment']

	# TAXES
	data['depreciable_value'] = data['property_value'] * building_assessed_fraction
	data['depreciated_loss'] = data['depreciable_value'] / (depreciation_schedule * 12)

	data['net_income'] = data['cashflow'] + data['principal_payment']
	# not sure if losses can carry forward, probably yes, but ignore that for now.
	data['tax_payment'] = np.maximum((data['net_income'] - data['depreciated_loss']) * personal_tax_rate, 0)
	data['after_tax_cashflow'] = data['cashflow'] - data['tax_payment']

	# balance sheet stuff
	data['LTV'] = data['principal_remaining'] / data['property_value'] 
	# note we arent counting where we get money if we're cashflow negative, or what we do with it
	# if we're cashflow positive, this should be addressed.
	data['equity'] = data['property_value'] - data['principal_remaining']

	return data

