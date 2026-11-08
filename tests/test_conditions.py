from copy import deepcopy
import pytest
from backend.intelligence.conditions import classify_conditions, personalized_condition_alerts
from backend.intelligence.health_score import health_score
from backend.intelligence.service import analyze_with_spending
from backend.intelligence.simulator import simulate


@pytest.fixture
def snapshot():
    values = {'inflation_yoy_pct': 5., 'policy_rate_pct': 5.5, 'unemployment_pct': 6.,
              'unemployment_change_3m_pp': .7, 'market_return_3m_pct': -12., 'market_drawdown_252d_pct': -15.}
    return {'as_of': '2026-11-07', **values, 'observation_dates': {key: '2026-11-07' for key in values}}


@pytest.fixture
def customer():
    return {'customer_id': 'test', 'as_of': '2026-11-07', 'checking_balance': 250., 'savings_balance': 500.,
            'monthly_income': 3000., 'monthly_variable_spending': 900., 'monthly_debt_payments': 600.,
            'bills': [{'name': 'housing', 'amount': 1500., 'day': 10}, {'name': 'debt', 'amount': 600., 'day': 12}],
            'paydays': [15, 28], 'safety_buffer': 500.}


def test_condition_labels_are_observed_and_explainable(snapshot):
    result = classify_conditions(snapshot)
    assert result['economy']['label'] == 'pressured'
    assert result['market']['label'] == 'stressed'
    assert result['economy']['data_complete'] is True
    assert result['economy']['evidence']['unemployment_change_3m_pp'] == .7


def test_missing_stale_or_future_data_is_unknown(snapshot):
    assert classify_conditions(None)['market']['label'] == 'unknown'
    assert classify_conditions(snapshot, '2026-11-06')['economy']['label'] == 'unknown'
    assert classify_conditions(snapshot, '2027-05-01')['market']['label'] == 'unknown'
    del snapshot['observation_dates']['market_return_3m_pct']
    assert classify_conditions(snapshot)['market']['label'] == 'unknown'


def test_invalid_numbers_not_classified_as_safe(snapshot):
    snapshot['inflation_yoy_pct'] = float('nan')
    with pytest.raises(ValueError):
        classify_conditions(snapshot)


def test_same_conditions_different_user_needs(snapshot, customer):
    conditions = classify_conditions(snapshot)
    forecast = {'minimum_balance': 100., 'minimum_savings': 500.}
    alerts = personalized_condition_alerts(customer, forecast, health_score(customer), conditions)
    codes = {a['id'] for a in alerts}
    assert {'cost_pressure_exposure', 'income_resilience_exposure'} <= codes
    assert 'variable_rate_exposure' not in codes  # debt rate type not supplied
    strong = deepcopy(customer)
    strong.update(checking_balance=10000., savings_balance=30000., monthly_income=7000.)
    assert personalized_condition_alerts(strong, {'minimum_balance': 8000., 'minimum_savings': 30000.},
                                        health_score(strong), conditions) == []


def test_rate_and_market_alerts_require_reported_exposure(snapshot, customer):
    customer.update(variable_rate_debt_balance=12000., equity_exposure=5000., planned_equity_withdrawal_90d=1000.)
    result = personalized_condition_alerts(customer, {'minimum_balance': 100.}, health_score(customer), classify_conditions(snapshot))
    rate = next(a for a in result if a['id'] == 'variable_rate_exposure')
    assert rate['evidence']['approx_monthly_interest_increase'] == 10.
    assert rate['suggested_simulation'] == {'additional_monthly_expense': 10.}
    assert any(a['id'] == 'near_term_equity_exposure' for a in result)
    customer['planned_equity_withdrawal_90d'] = 0
    assert not any(a['id'] == 'near_term_equity_exposure' for a in personalized_condition_alerts(
        customer, {'minimum_balance': 100.}, health_score(customer), classify_conditions(snapshot)))


def test_extra_debt_payment_not_suggested_with_tight_cash(snapshot, customer):
    customer['high_interest_debt_balance'] = 4000.
    result = personalized_condition_alerts(customer, {'minimum_balance': 100.}, health_score(customer), classify_conditions(snapshot))
    debt = next(a for a in result if a['id'] == 'debt_liquidity_tradeoff')
    assert debt['suggested_simulation'] == {}


def test_additional_expense_simulates_cash_effect_and_alerts(snapshot, customer):
    customer['variable_rate_debt_balance'] = 12000.
    path = {'daily': [{'date': f'2026-11-{day:02d}', 'spending': 0., 'lower': 0., 'upper': 0.} for day in (8, 9, 10)]}
    result = simulate(customer, path, {'additional_monthly_expense': 10.}, snapshot)
    assert result['ending_balance_change'] == -10
    alert = next(a for a in result['after']['guardian'] if a['id'] == 'variable_rate_exposure')
    assert alert['delivery'] == 'in_app_candidate'
    assert 'tradeoff' in alert


def test_original_debt_rule_preserves_liquidity(customer):
    customer['monthly_debt_payments'] = 1500.
    path = {'daily': [{'date': '2026-11-08', 'spending': 30., 'lower': 30., 'upper': 30.}]}
    result = analyze_with_spending(customer, path)
    assert next(a for a in result['guardian'] if a['id'] == 'debt_burden')['suggested_simulation'] == {}
    assert next(a for a in result['guardian'] if a['id'] == 'emergency_savings')['suggested_simulation'] == {}


def test_forecast_budget_alert_uses_complete_month_and_crossing_date(customer):
    import pandas as pd
    customer.update(as_of='2026-10-31', checking_balance=10000., savings_balance=30000.,
                    monthly_income=6000., monthly_variable_spending=900., budget=1000.)
    path = {'days': 30, 'daily': [{'date': d.date().isoformat(), 'spending': 100., 'lower': 100., 'upper': 100.}
                                 for d in pd.date_range('2026-11-01', periods=30)]}
    result = analyze_with_spending(customer, path)
    alert = next(a for a in result['guardian'] if a['id'] == 'projected_spending_above_budget')
    assert alert['evidence']['projected_month_spending'] == 3000.
    assert alert['evidence']['first_breach_date'] == '2026-11-13'
    assert not any(a['id'] == 'spending_above_budget' for a in result['guardian'])
    path['daily'] = path['daily'][:7]
    partial = analyze_with_spending(customer, path)
    assert not any(a['id'] == 'projected_spending_above_budget' for a in partial['guardian'])


def test_monthly_cut_rounding_preserves_requested_total(customer):
    import pandas as pd
    customer.update(as_of='2026-10-31')
    path = {'daily': [{'date': d.date().isoformat(), 'spending': 100., 'lower': 100., 'upper': 100.}
                      for d in pd.date_range('2026-11-01', periods=30)]}
    assert simulate(customer, path, {'monthly_spending_cut': 200})['ending_balance_change'] == 200.
