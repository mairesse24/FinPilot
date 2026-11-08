"""Pure in-memory scenario evaluation; never writes accounts or moves money."""
from copy import deepcopy
import calendar
from datetime import date
from .service import analyze_with_spending
from .validation import number

FIELDS = {'income_reduction_pct', 'emergency_expense', 'monthly_spending_cut',
          'monthly_savings_transfer', 'extra_debt_payment', 'cost_of_living_pct', 'additional_monthly_expense'}


def simulate(customer, spending, scenario, indicators=None):
    if set(scenario) - FIELDS:
        raise ValueError('Unknown scenario fields')
    for key, value in scenario.items():
        number(value, key, maximum=1 if key.endswith('_pct') else None)
    c, path = deepcopy(customer), deepcopy(spending)
    c['monthly_income'] *= 1-scenario.get('income_reduction_pct', 0)
    c['checking_balance'] -= scenario.get('emergency_expense', 0)
    cut = min(c['monthly_variable_spending'], scenario.get('monthly_spending_cut', 0))
    inflation = 1+scenario.get('cost_of_living_pct', 0)
    c['monthly_variable_spending'] = (c['monthly_variable_spending']-cut)*inflation
    months = {}
    for row in path['daily']:
        months.setdefault(row['date'][:7], []).append(row)
    factors, target_cents = {}, {}
    for month, rows in months.items():
        d = date.fromisoformat(rows[0]['date'])
        total = sum(r['spending'] for r in rows)
        prorated_cut = cut*len(rows)/calendar.monthrange(d.year, d.month)[1]
        factors[month] = max(0, 1-prorated_cut/total)*inflation if total else inflation
        target_cents[month] = int(round(max(0, total-prorated_cut)*inflation*100))
    for row in path['daily']:
        for key in ('spending', 'lower', 'upper'):
            row[key] = round(row[key]*factors[row['date'][:7]], 2)
    # Reconcile cent rounding so a full-month $200 cut does not become $200.10.
    for month, rows in months.items():
        residual = target_cents[month]-sum(int(round(r['spending']*100)) for r in rows)
        for row in rows:
            if residual == 0:
                break
            cents = int(round(row['spending']*100))
            adjustment = residual if residual > 0 else max(residual, -cents)
            row['spending'] = (cents+adjustment)/100
            row['lower'] = min(row['lower'], row['spending'])
            row['upper'] = max(row['upper'], row['spending'])
            residual -= adjustment
    extra = scenario.get('extra_debt_payment', 0)
    if extra:
        c['bills'].append({'name': 'extra_debt_payment', 'amount': extra, 'day': 10})
        c['monthly_debt_payments'] += extra
    transfer = scenario.get('monthly_savings_transfer', 0)
    if scenario.get('additional_monthly_expense', 0):
        c['bills'].append({'name': 'illustrative_additional_expense', 'amount': scenario['additional_monthly_expense'], 'day': 10})
    c['monthly_savings_transfer'] = c.get('monthly_savings_transfer', 0) + transfer
    before = analyze_with_spending(customer, spending, indicators)
    after = analyze_with_spending(c, path, indicators)
    savings_path = [{'date': r['date'], 'savings_balance': r['savings_balance']} for r in after['forecast']['daily']]
    fc = after['forecast']
    fc['minimum_balance'] = min([c['checking_balance']] + [r['balance'] for r in fc['daily']])
    fc['ending_balance'] = fc['daily'][-1]['balance']
    from .guardian import detect_risks
    after['guardian'] = detect_risks(c, fc, after['health'], after['economy'])
    return {'scenario': scenario, 'before': before, 'after': after, 'savings_path': savings_path,
            'ending_balance_change': round(fc['ending_balance']-before['forecast']['ending_balance'], 2),
            'note': 'Scores reflect changed starting circumstances and monthly assumptions. Savings transfers preserve combined liquid cash. Extra debt payments do not model amortization or future interest savings.'}
