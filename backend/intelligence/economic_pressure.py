"""Accept Member 2's economic snapshot. No network access or invented live data."""
from datetime import date
from .validation import number
from .conditions import classify_conditions


def economic_pressure(c, indicators=None):
    if indicators is None:
        return {'available': False, 'index': None, 'conditions': classify_conditions(None), 'reason': 'Awaiting dated FRED snapshot from backend'}
    date.fromisoformat(indicators['as_of'])
    for key in ('inflation_yoy_pct', 'policy_rate_pct', 'unemployment_pct'):
        number(indicators[key], key, minimum=-20, maximum=100)
    inflation = max(0, indicators['inflation_yoy_pct'])
    rate = max(0, indicators['policy_rate_pct'])
    unemployment = max(0, indicators['unemployment_pct'])
    # Transparent stress heuristic, not a probability or macroeconomic forecast.
    index = min(100, .5*min(100, inflation/8*100) + .25*min(100, rate/8*100)
                + .25*min(100, unemployment/10*100))
    return {'available': True, 'index': round(index, 2), 'snapshot': indicators,
            'conditions': classify_conditions(indicators),
            'personalization_missing_fields': [key for key in ('variable_rate_debt_balance', 'high_interest_debt_balance',
                'equity_exposure', 'planned_equity_withdrawal_90d') if key not in c],
            'illustrative_monthly_variable_cost_increase': round(c['monthly_variable_spending']*inflation/100, 2),
            'formula': '50% inflation/8 + 25% policy rate/8 + 25% unemployment/10; each capped at 1, times 100',
            'note': 'Design-assumption pressure index, not personal job-loss probability. Cost impact is a hypothetical year-over-year stress, not a monthly forecast.'}
