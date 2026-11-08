"""Write editable synthetic edge cases with independently declared alert expectations."""
import csv
from backend.intelligence.data import ROOT

DESTINATION = ROOT / 'data/synthetic/stress-cases.csv'


def cases():
    base = dict(case_id='', group='policy', description='', engine='controlled', pattern='pnc', days=30,
        checking_balance=10000, savings_balance=30000, monthly_income=6000,
        monthly_variable_spending=900, monthly_debt_payments=300, bill_amount=1500, bill_day=10,
        budget=1000, savings_floor=1000, fund_shortfalls_from_savings=0,
        variable_rate_debt_balance=0, high_interest_debt_balance=0, equity_exposure=0,
        planned_equity_withdrawal_90d=0, daily_spending=30, inflation_yoy_pct=2.5,
        unemployment_pct=4, unemployment_change_3m_pp=0, policy_rate_pct=2,
        market_return_3m_pct=3, market_drawdown_252d_pct=-1, indicator_age_days=0,
        include_indicators=1, expected_economy='steady', expected_market='steady',
        required_alerts='', forbidden_alerts='', expect_error=0)
    rows = []
    def add(name, description, **changes):
        rows.append({**base, 'case_id': name, 'description': description, **changes})
    tight = dict(checking_balance=250, savings_balance=500, monthly_income=3000, bill_amount=2100)
    weak = dict(market_return_3m_pct=-20, market_drawdown_252d_pct=-30, expected_market='stressed')
    add('healthy_control', 'Ample reserves; steady observed conditions', forbidden_alerts='low_balance|spending_above_budget|variable_rate_exposure|near_term_equity_exposure')
    add('overspending', 'Historical variable spending well above supplied budget', monthly_variable_spending=2400, daily_spending=80, required_alerts='spending_above_budget')
    add('budget_exact_120pct', 'At exactly 120 percent of budget; strict threshold does not fire', monthly_variable_spending=1200, daily_spending=40, forbidden_alerts='spending_above_budget|projected_spending_above_budget')
    add('future_overspending', 'Historical budget adherence but complete future month exceeds budget', monthly_variable_spending=900, daily_spending=100, required_alerts='projected_spending_above_budget', forbidden_alerts='spending_above_budget')
    add('short_horizon_budget', 'Seven days cannot establish full-month overspending', days=7, daily_spending=100, forbidden_alerts='projected_spending_above_budget')
    add('low_cash', 'Checking cannot cover scheduled bills', checking_balance=100, savings_balance=0, monthly_income=0, required_alerts='low_balance|payment_pressure')
    add('savings_crossing', 'Future checking shortfall draws savings below its floor', checking_balance=100, savings_balance=500, monthly_income=0, daily_spending=200, savings_floor=450, fund_shortfalls_from_savings=1, required_alerts='savings_below_floor')
    add('no_implicit_savings', 'Same shortfall without permission to model reserve withdrawals', checking_balance=100, savings_balance=500, monthly_income=0, daily_spending=200, savings_floor=450, required_alerts='low_balance', forbidden_alerts='savings_below_floor')
    add('inflation_tight', 'High inflation with low reserves', **tight, inflation_yoy_pct=5, expected_economy='pressured', required_alerts='cost_pressure_exposure')
    add('inflation_ample', 'Same inflation with ample reserves needs no pressure action', inflation_yoy_pct=5, expected_economy='pressured', forbidden_alerts='cost_pressure_exposure')
    add('unemployment_rising', 'Labor trend plus low reserves warrants income stress test', **tight, unemployment_change_3m_pp=.7, expected_economy='pressured', required_alerts='income_resilience_exposure')
    add('unemployment_stable', 'High unemployment level alone is not personal job-loss prediction', **tight, unemployment_pct=8, forbidden_alerts='income_resilience_exposure')
    add('high_rates_variable', 'High rates with variable-rate debt; verify 1 pp shock', policy_rate_pct=5.5, variable_rate_debt_balance=12000, expected_economy='pressured', required_alerts='variable_rate_exposure')
    add('high_rates_fixed', 'Do not assume fixed debt reprices', policy_rate_pct=5.5, expected_economy='pressured', forbidden_alerts='variable_rate_exposure')
    add('low_rates_not_loan_signal', 'Low rates alone do not recommend taking a loan', variable_rate_debt_balance=12000, forbidden_alerts='variable_rate_exposure')
    add('market_near_term', 'Falling index with reported near-term equity cash need', **weak, equity_exposure=10000, planned_equity_withdrawal_90d=2000, required_alerts='near_term_equity_exposure')
    add('market_long_term', 'Falling index but no near-term withdrawal; no blanket sell/spend alert', **weak, equity_exposure=10000, forbidden_alerts='near_term_equity_exposure|cost_pressure_exposure')
    add('market_no_equity', 'Falling index with no equity exposure', **weak, planned_equity_withdrawal_90d=2000, forbidden_alerts='near_term_equity_exposure')
    add('stale_market', 'Market observations older than ten days are unknown', **{**weak, 'expected_market': 'unknown'}, indicator_age_days=11, equity_exposure=10000, planned_equity_withdrawal_90d=2000, forbidden_alerts='near_term_equity_exposure')
    add('stale_all', 'Old indicators must not produce condition recommendations', indicator_age_days=101, expected_economy='unknown', expected_market='unknown', forbidden_alerts='variable_rate_exposure|near_term_equity_exposure')
    add('future_observations', 'Future-dated observations cannot be treated as known', indicator_age_days=-1, expected_economy='unknown', expected_market='unknown')
    add('missing_economy', 'No indicator snapshot means unknown conditions', include_indicators=0, expected_economy='unknown', expected_market='unknown')
    add('debt_tight', 'Preserve liquidity instead of blindly recommending extra repayment', **tight, policy_rate_pct=5.5, high_interest_debt_balance=4000, expected_economy='pressured', required_alerts='debt_liquidity_tradeoff', forbidden_alerts='debt_paydown_option')
    add('debt_surplus', 'Ample reserves and surplus permit optional repayment comparison', policy_rate_pct=5.5, high_interest_debt_balance=4000, expected_economy='pressured', required_alerts='debt_paydown_option')
    add('inflation_boundary', 'Four percent inflation starts pressure class', inflation_yoy_pct=4, expected_economy='pressured')
    add('rate_boundary', 'Five percent policy rate starts pressure class', policy_rate_pct=5, expected_economy='pressured')
    add('drawdown_boundary', 'Ten percent drawdown starts stressed class', market_drawdown_252d_pct=-10, expected_market='stressed')
    add('negative_savings', 'Invalid savings balance is rejected', group='validation', savings_balance=-1, expect_error=1)
    add('nan_income', 'Nonfinite income must be rejected', group='validation', monthly_income='nan', expect_error=1)
    add('invalid_bill_day', 'Invalid scheduled date must be rejected', group='validation', bill_day=32, expect_error=1)
    add('zero_income', 'Undefined income ratios return missing values; no crash', monthly_income=0, checking_balance=100, savings_balance=0, required_alerts='low_balance')
    for days in (7, 30, 90):
        add(f'ml_pnc_{days}', 'Actual saved LightGBM on original held-out-customer C026 history', group='ml_response', engine='ml', pattern='pnc', days=days)
    for pattern in ('zero', 'irregular', 'surge', 'one_off_spike'):
        add(f'ml_{pattern}', f'Out-of-distribution {pattern} history; observe saved model response, not accuracy', group='ml_response', engine='ml', pattern=pattern, days=90)
    for pattern in ('short', 'gap', 'duplicate', 'nan', 'negative'):
        add(f'ml_invalid_{pattern}', 'Malformed history must be rejected before inference', group='validation', engine='ml', pattern=pattern, expect_error=1)
    for days in (0, 91):
        add(f'ml_invalid_horizon_{days}', 'Unsupported forecast horizon must be rejected', group='validation', engine='ml', days=days, expect_error=1)
    for pattern in ('base', 'inflation_spike', 'labor_shock', 'rate_hike', 'market_crash', 'missing_month', 'short_history'):
        add(f'research_{pattern}', 'Research-model sensitivity on modified cached FRED history; not new accuracy evidence',
            group='research_response', engine='research', pattern=pattern, expect_error=int(pattern == 'short_history'))
    return rows


def main():
    rows = cases()
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with DESTINATION.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f'Created {len(rows)} editable cases: {DESTINATION}')


if __name__ == '__main__':
    main()
