"""Shared boundary validation for normalized backend inputs."""
import math
from datetime import date


def number(value, name, minimum=0, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be finite numeric data')
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f'{name} is out of range')
    return value


def validate_customer(c):
    date.fromisoformat(c['as_of'])
    for key in ('checking_balance', 'savings_balance', 'monthly_income', 'monthly_variable_spending',
                'monthly_debt_payments', 'safety_buffer'):
        number(c[key], key, minimum=-1e12 if key == 'checking_balance' else 0)
    if not c['paydays'] or any(type(d) is not int or not 1 <= d <= 31 for d in c['paydays']):
        raise ValueError('paydays must contain calendar days 1..31')
    for bill in c['bills']:
        number(bill['amount'], 'bill amount')
        if type(bill['day']) is not int or not 1 <= bill['day'] <= 31:
            raise ValueError('bill day must be 1..31')
    if c.get('budget') is not None:
        number(c['budget'], 'budget', minimum=.01)
    if 'savings_floor' in c:
        number(c['savings_floor'], 'savings_floor')
    if 'monthly_savings_transfer' in c:
        number(c['monthly_savings_transfer'], 'monthly_savings_transfer')
    if type(c.get('fund_shortfalls_from_savings', False)) is not bool:
        raise ValueError('fund_shortfalls_from_savings must be a boolean')
    for key in ('variable_rate_debt_balance', 'high_interest_debt_balance', 'equity_exposure', 'planned_equity_withdrawal_90d'):
        if key in c:
            number(c[key], key)
