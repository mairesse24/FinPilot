"""Offline illustration: identical hypothetical conditions, different user exposures."""
from copy import deepcopy
import json
import pandas as pd
from backend.intelligence.data import ROOT
from backend.intelligence.service import analyze_with_spending


def main():
    as_of = '2026-11-07'
    values = {'inflation_yoy_pct': 5., 'policy_rate_pct': 5.5, 'unemployment_pct': 6.,
              'unemployment_change_3m_pp': .7, 'market_return_3m_pct': -12., 'market_drawdown_252d_pct': -15.}
    snapshot = {'as_of': as_of, **values, 'observation_dates': {key: as_of for key in values},
                'source': 'HYPOTHETICAL STRESS DEMO; NOT OBSERVED FRED DATA'}
    customer = {'customer_id': 'DEMO-TIGHT-CASH', 'as_of': as_of,
                'checking_balance': 250., 'savings_balance': 500., 'monthly_income': 3000.,
                'monthly_variable_spending': 900., 'monthly_debt_payments': 600.,
                'bills': [{'name': 'housing', 'amount': 1500., 'day': 10}, {'name': 'debt', 'amount': 600., 'day': 12}],
                'paydays': [15, 28], 'safety_buffer': 500., 'savings_floor': 450.,
                'variable_rate_debt_balance': 12000., 'high_interest_debt_balance': 4000.,
                'equity_exposure': 5000., 'planned_equity_withdrawal_90d': 1000.}
    spending = {'model': 'hypothetical_constant_spending_scenario', 'days': 30, 'synthetic': True,
                'daily': [{'date': day.date().isoformat(), 'spending': 30., 'lower': 30., 'upper': 30.}
                          for day in pd.date_range('2026-11-08', periods=30)]}
    strong = deepcopy(customer)
    strong.update(customer_id='DEMO-AMPLE-CASH', checking_balance=12000., savings_balance=30000.,
                  monthly_income=7000., variable_rate_debt_balance=0., high_interest_debt_balance=0.,
                  equity_exposure=5000., planned_equity_withdrawal_90d=0.)
    results = {c['customer_id']: analyze_with_spending(c, spending, snapshot) for c in (customer, strong)}
    destination = ROOT / 'data/synthetic/conditions-demo.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({'label': snapshot['source'], 'customers': results}, indent=2, allow_nan=False), encoding='utf-8')
    for key, result in results.items():
        conditions = result['economy']['conditions']
        print(f"{key}: economy={conditions['economy']['label']}, market={conditions['market']['label']}")
        for alert in result['guardian']:
            print(f"  {alert['id']}: {alert.get('guidance', alert['explanation'])}")
    print(f'Hypothetical demo only; JSON: {destination}')


if __name__ == '__main__':
    main()
