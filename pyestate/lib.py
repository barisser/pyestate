import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

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
		data.append([n, interest_payment, principal_payoff, princ, total])
		princ -= principal_payoff
	return pd.DataFrame(data, columns=['payment_n', 'interest', 'principal_payment', 'principal_remaining', 'total'])


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


def note_yield(price, unpaid, rate, payments):
	"""
	Given a mortgage note with unpaid balance and rate and number of remaining payments,
	at a certain tradeable price, what is the equivalent yield?
	This means, if this were a freshly issued note at the traded price, what would the interest
	rate have to be to supply the exact same payment schedule?

	Start with this equation:
	Total payment = principal * i*(1+i)^N / ((1+i)^N - 1) = price * i2 * (1+i2)^N / ((1+i2)^N-1)
	Total payment is conserved so take the expression
	price * i*(1+i)^N / ((1+i)^N - 1), use binary search to select i such that this
	equals the original total payment.  I dont know of a clean analytical way
	to find this value.
	"""
	def _iterate(i, n):
		i2 = (1.+i)**(1/12.)-1.
		return i2*(1.+i2)**n / ((1.+i2)**n - 1.)
	# target is value of i such that iterate(i, n) == total_payment / price within some tolerance
	tol = 1e-5
	df = fixed_rate_amortization(unpaid, rate, payments)
	total_payment = (df['interest_payment'] + df['principal_payment']).iloc[0]
	target = total_payment / price
	left, right = -1, 10.
	while right - left > tol:
		mid = right / 2. + left / 2.
		val = _iterate(mid, payments)
		if val > target:
			right = mid
		else:
			left = mid

	effective_rate = mid
	return effective_rate

def note_price(unpaid, rate, market_rate, payments):
	"""
	Imagine a mortgage with an unpaid balance, rate, and number of remaining payments.
	What is this 'worth' under a new market rate?

	principal * i*(1+i)^N / ((1+i)^N - 1) = principal2 * i2 * (1+i2)^N / ((1+i2)^N-1)
	principal2 = principal * (i*(1+i)^N / ((1+i)^N - 1)) / (i2 * (1+i2)^N / ((1+i2)^N-1))

	Basically if I created a new mortgage note today at the prevailing rates with the
	exact same payment schedule, what would the balance be?

	note yield and note price have a parity with one another
	pyestate.note_price(1e6, 0.05, 0.04,60) = 1.023e6
	pyestate.note_yield(1.023e6, 1e6, 0.05, 60) == 0.04

	Basically a 5% note for 1e6 in a 4% yield regime would go for 1.023e6, and correspondingly
	the yield for a 1.023e6-price and 1e6 unpaid balance note with 5% coupon is 4%.
	"""
	def _func(i, n):
			i2 = (1.+i)**(1/12.)-1.
			return i2*(1.+i2)**n / ((1.+i2)**n - 1.)
	return unpaid * _func(rate, payments) / _func(market_rate, payments)

def iterate_sim_once(rent_lambda, price_lambda, rate_lambda, cash, last_price, debt, last_rate, last_rent):
	"""
	dat is [next price, next rent, next rate]
	"""
	next_rate = rate_lambda(last_rate)
	next_rent = rent_lambda(last_rent)
	next_price = price_lambda(last_price, next_rent, next_rate)
	dat = [next_price, next_rent, next_rate]

	return dat

def simulate_property(price, ltv, rate, payments, rent, rent_lambda, price_lambda, rate_lambda, cash,
	vacancy_rate, property_tax_rate):
	"""
	"""
	debt = ltv * price
	asset_price = price
	current_rate = rate
	data = []

	schedule = payment_schedule(asset_price, ltv, rate, payments, 0, 0., payments_per_year=12)

	for t in range(payments):
		asset_price, rent, rate = iterate_sim_once(rent_lambda, price_lambda, rate_lambda, cash, asset_price, debt, rate, rent)
		events = []
		schedule_row = schedule.iloc[t]
		payments = schedule_row.total_payment # todo add property tax back in
		payments += asset_price * property_tax_rate / 12.
		cashflow = - payments

		vacant = np.random.rand() < vacancy_rate
		if not vacant:
			cashflow += rent
		else:
			events.append('vacant')

		cash += cashflow
		if cash > 0:
			cash *= (1. + max(rate - 0.03, 0.))**(1/12.) # safe treasuries
		if cash < 0:
			events.append('bankrupt')

		debt -= schedule_row.principal_payment
		events_str = ",".join(events)

		dat = [asset_price, rent, rate, cash, debt, events_str, payments]
		data.append(dat)

	df = pd.DataFrame(data, columns=['price', 'rent', 'rate', 'cash', 'debt', 'events', 'payments'])
	df['equity']= df['price'] - df['debt']
	df['net_worth'] = df['equity'] + df['cash']

	return df

def simulate_many(n, price, ltv, rate, payments, rent, rent_lambda, price_lambda, rate_lambda, cash,
	vacancy_rate, property_tax_rate):
	agg_data = []
	dfs = []
	for i in range(n):
		print("Simulating: {}".format(i))
		tdf = simulate_property(price, ltv, rate, payments, rent, rent_lambda, price_lambda, rate_lambda, cash, vacancy_rate, property_tax_rate)
		tdf['id'] = i
		dfs.append(tdf)

		bankrupt = len(tdf) < payments
		IRR = (tdf.iloc[60].net_worth / tdf.iloc[0].net_worth) ** (12. / len(tdf)) - 1.
		agg = [i, bankrupt, IRR]
		agg_data.append(agg)

	detailed = pd.concat(dfs)
	aggs = pd.DataFrame(agg_data, columns=['id', 'bankrupt', 'irr'])
	return aggs, detailed

def rent_slow_increase(rent):
	return rent * 1.08**(1./12.)

def price_walk(price, rent, rate):
	spread = 0.02
	eff_rate = max(rate + 0.03, 0.04)
	price = rent * 12. * (1. / eff_rate)
	return price

def rate_walk(last_rate):
	max_rates = 0.045
	min_rates = -0.005
	delta = np.random.logistic(scale=0.0025)
	rate = last_rate + delta
	rate = min(max_rates, rate)
	rate = max(min_rates, rate)

	return rate


#df1, df2 = simulate_many(30, 3e5, 0.75, 0.065, 360, 1800, rent_slow_increase, price_walk, rate_walk, 1e4, 0.01, 0.02)
import pdb;pdb.set_trace()