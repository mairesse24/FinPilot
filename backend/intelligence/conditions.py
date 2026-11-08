"""Observed economic/market regime rules, not a prediction or recession declaration."""
from datetime import date
from .validation import number

POLICY_VERSION = 'conditions-v1'


def classify_conditions(snapshot, as_of=None):
    if not snapshot:
        return {'policy_version': POLICY_VERSION, 'economy': {'label': 'unknown'}, 'market': {'label': 'unknown'}}
    today = date.fromisoformat(as_of or snapshot['as_of'])
    dates = snapshot.get('observation_dates', {})

    def observation(key, max_age=100, minimum=-100, maximum=100):
        value = snapshot.get(key)
        stamp = dates.get(key)
        if value is None or not stamp:
            return None
        number(value, key, minimum, maximum)
        age = (today-date.fromisoformat(stamp)).days
        return float(value) if 0 <= age <= max_age else None

    inflation = observation('inflation_yoy_pct')
    labor = observation('unemployment_change_3m_pp')
    rate = observation('policy_rate_pct')
    inflation_label = 'unknown' if inflation is None else 'pressured' if inflation >= 4 else 'watch' if inflation >= 3 else 'steady'
    labor_label = 'unknown' if labor is None else 'pressured' if labor >= .5 else 'watch' if labor >= .3 else 'steady'
    rate_label = 'unknown' if rate is None else 'pressured' if rate >= 5 else 'watch' if rate >= 3.5 else 'steady'
    factors = {'living_costs': inflation_label, 'labor_trend': labor_label, 'borrowing_costs': rate_label}
    known = [v for v in factors.values() if v != 'unknown']
    economy_label = 'unknown' if not known else 'pressured' if 'pressured' in known else 'watch' if 'watch' in known else 'steady'
    ret = observation('market_return_3m_pct', 10, -100, 10000)
    drawdown = observation('market_drawdown_252d_pct', 10, -100, 0)
    if ret is None or drawdown is None:
        market_label = 'unknown'
    elif drawdown <= -10 or ret <= -10:
        market_label = 'stressed'
    elif drawdown <= -5 or ret < 0:
        market_label = 'watch'
    else:
        market_label = 'steady'
    return {'policy_version': POLICY_VERSION, 'as_of': today.isoformat(),
            'method': 'transparent observed-condition rules; no trained-classifier accuracy claim',
            'economy': {'label': economy_label, 'factors': factors, 'data_complete': len(known) == 3,
                        'evidence': {'inflation_yoy_pct': inflation, 'unemployment_change_3m_pp': labor, 'policy_rate_pct': rate}},
            'market': {'label': market_label, 'evidence': {'return_3m_pct': ret, 'drawdown_252d_pct': drawdown}},
            'thresholds': {'inflation_watch_pct': 3, 'inflation_pressure_pct': 4,
                'unemployment_3m_watch_pp': .3, 'unemployment_3m_pressure_pp': .5,
                'policy_rate_watch_pct': 3.5, 'policy_rate_pressure_pct': 5,
                'market_drawdown_watch_pct': -5, 'market_drawdown_stress_pct': -10,
                'market_return_3m_stress_pct': -10},
            'note': 'Prototype thresholds, not validated regime labels. Steady means no configured stress flag, not a healthy economy or future gains.'}


def personalized_condition_alerts(customer, forecast, health, conditions):
    """Match observed conditions with supplied exposure; suggest scenarios, not mandates."""
    components = {v['name']: v['metric'] for v in health['components']}
    months = components['emergency_savings']
    tight = (forecast['minimum_balance'] < customer['safety_buffer'] or
             forecast.get('minimum_savings', customer['savings_balance']) < customer.get('savings_floor', 0) or
             (months is not None and months < 3))
    surplus = customer['monthly_income'] - customer['monthly_variable_spending'] - sum(b['amount'] for b in customer['bills'])
    economy = conditions.get('economy', {}).get('factors', {})
    market = conditions.get('market', {}).get('label', 'unknown')
    alerts = []

    def add(code, text, evidence, scenario, guidance, tradeoff, severity='medium'):
        alerts.append({'id': code, 'severity': severity, 'explanation': text, 'evidence': evidence,
                       'suggested_simulation': scenario, 'guidance': guidance, 'tradeoff': tradeoff})

    if tight and economy.get('living_costs') in ('watch', 'pressured'):
        add('cost_pressure_exposure', 'Elevated observed inflation coincides with limited household cash resilience.',
            {'emergency_months': months, 'projected_checking_low': forecast['minimum_balance'],
             **conditions['economy']['evidence']}, {'cost_of_living_pct': .05},
            'Test a 5% variable-cost increase, then identify optional purchases you could postpone. Preserve essential bills.',
            'The 5% shock is illustrative, not an inflation forecast. Cutting essential spending may be harmful.')
    if tight and economy.get('labor_trend') in ('watch', 'pressured'):
        add('income_resilience_exposure', 'A rising national unemployment trend coincides with limited liquid reserves.',
            {'emergency_months': months, 'unemployment_change_3m_pp': conditions['economy']['evidence']['unemployment_change_3m_pp']},
            {'income_reduction_pct': .10}, 'Test a temporary 10% income reduction and check whether essential payments remain covered.',
            'National unemployment changes do not predict this person losing income.')
    variable_debt = customer.get('variable_rate_debt_balance', 0.)
    if variable_debt > 0 and economy.get('borrowing_costs') in ('watch', 'pressured'):
        interest_shock = round(variable_debt*.01/12, 2)
        add('variable_rate_exposure', 'Reported variable-rate debt is exposed to borrowing-cost changes.',
            {'variable_rate_debt_balance': variable_debt, 'hypothetical_rate_rise_pp': 1,
             'approx_monthly_interest_increase': interest_shock}, {'additional_monthly_expense': interest_shock},
            'Review the loan reset terms and test an illustrative one-percentage-point rate increase before adding debt.',
            'Balance times rate/12 approximates interest exposure, not a lender payment quote. Existing fixed-rate payments are not changed.')
    equity = customer.get('equity_exposure', 0.)
    planned = customer.get('planned_equity_withdrawal_90d', 0.)
    if market in ('watch', 'stressed') and equity > 0 and planned > 0:
        add('near_term_equity_exposure', 'Recent market weakness overlaps a reported near-term need for invested money.',
            {'equity_exposure': equity, 'planned_equity_withdrawal_90d': planned, **conditions['market']['evidence']}, {},
            'Review whether near-term essential payments depend on selling investments. Compare the goal timing with available cash.',
            'This is not a sell signal or portfolio-loss forecast. Market weakness alone does not justify changing all spending.')
    high_interest_debt = customer.get('high_interest_debt_balance', 0.)
    if conditions.get('economy', {}).get('label') in ('watch', 'pressured') and high_interest_debt > 0:
        if tight or surplus <= 0:
            add('debt_liquidity_tradeoff', 'High-interest debt is reported, but cash resilience is constrained.',
                {'high_interest_debt_balance': high_interest_debt, 'monthly_surplus': round(surplus, 2), 'emergency_months': months}, {},
                'Review required payments and preserve essential cash before testing extra repayment.',
                'Extra debt payments reduce liquidity; they are not automatically helpful during economic stress.')
        else:
            extra = round(min(100., surplus*.1, high_interest_debt), 2)
            add('debt_paydown_option', 'Positive modeled surplus and reserves allow an extra-payment scenario to be explored.',
                {'high_interest_debt_balance': high_interest_debt, 'monthly_surplus': round(surplus, 2), 'emergency_months': months},
                {'extra_debt_payment': extra}, 'Compare an optional extra debt payment with keeping the same amount liquid.',
                'Check the simulated balance before acting; this model does not calculate future interest savings.', 'info')
    return alerts
