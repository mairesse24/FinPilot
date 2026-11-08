"""Create API-ready synthetic output and Detect -> Simulate -> Recommend example."""
import json
from backend.intelligence.data import ROOT, load_customer, load_daily
from backend.intelligence.service import analyze, analyze_with_spending
from backend.intelligence.simulator import simulate
from backend.intelligence.copilot import chat


def main():
    customer = load_customer('C002')
    # Explicit fictional stress fixture, not a claim about PNC customer C002.
    customer['checking_balance'] = 2400.
    customer['savings_balance'] = 100.
    customer['monthly_income'] = 3000.
    customer['monthly_debt_payments'] = 600.
    customer['bills'] = [{'name': 'rent', 'amount': 2000., 'day': 3},
                         {'name': 'debt_payments', 'amount': 600., 'day': 10}]
    customer['paydays'] = [15, 28]
    customer['customer_id'] = 'DEMO-GUARDIAN'
    customer['assumptions'].append('Fictional demo overrides checking, savings, income and bills to illustrate liquidity risk; spending history is from C002.')
    daily = load_daily()
    history = daily[daily.customer_id == 'C002'].copy()
    history['customer_id'] = customer['customer_id']
    analysis = analyze(customer, history, 30)
    spending = {k: analysis['forecast'][k] for k in ('model', 'days', 'daily', 'uncertainty', 'synthetic')}
    scenario = simulate(customer, spending, {'monthly_spending_cut': 200})
    reserve_customer = {**customer, 'savings_floor': 50., 'fund_shortfalls_from_savings': True}
    reserve_analysis = analyze_with_spending(reserve_customer, spending)
    report = {'customer': customer, 'analysis': analysis, 'simulation': scenario,
              'reserve_alert_example': {'customer': reserve_customer, 'analysis': reserve_analysis},
              'copilot': chat('Explain my risks', customer, spending, analysis, provider='offline')}
    folder = ROOT / 'data/synthetic'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'demo.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps({'output': str(folder / 'demo.json'), 'health_score': analysis['health']['score'],
                      'minimum_balance': analysis['forecast']['minimum_balance'],
                      'alerts': [a['id'] for a in analysis['guardian']],
                      'reserve_alerts': [a['id'] for a in reserve_analysis['guardian']],
                      'scenario_ending_balance_change': scenario['ending_balance_change']}, indent=2))


if __name__ == '__main__':
    main()
