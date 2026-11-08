"""Rule-based alerts with supporting numbers and simulator action hints."""
from datetime import date
import calendar


def detect_risks(c, forecast, health, economy=None):
    alerts = []
    def add(code, severity, explanation, evidence, action):
        breach = evidence.get('first_breach_date') or evidence.get('date') or c['as_of']
        alerts.append({'id': code, 'severity': severity, 'explanation': explanation,
                       'evidence': evidence, 'suggested_simulation': action,
                       'event_key': f"{c['customer_id']}:{code}:{breach}",
                       'days_until_breach': max(0, (date.fromisoformat(breach)-date.fromisoformat(c['as_of'])).days),
                       'delivery': 'in_app_candidate'})
    low = forecast['minimum_balance']
    for row in [{'date': c['as_of'], 'savings_balance': c['savings_balance']}] + forecast['daily']:
        if row.get('savings_balance', c['savings_balance']) < c.get('savings_floor', 0):
            explanation = 'Savings is already below your chosen reserve floor.' if row['date'] == c['as_of'] else 'Projected savings falls below your chosen reserve floor.'
            add('savings_below_floor', 'high', explanation,
                {'first_breach_date': row['date'], 'projected_savings': row['savings_balance'],
                 'savings_floor': c['savings_floor'], 'minimum_savings': forecast['minimum_savings'],
                 'reserve_policy': forecast['reserve_policy']}, {'monthly_spending_cut': 200})
            break
    if low < c['safety_buffer']:
        add('low_balance', 'critical' if low < 0 else 'high', 'Projected checking falls below your chosen buffer.',
            {'projected_low': low, 'buffer': c['safety_buffer'],
             'first_breach_date': c['as_of'] if c['checking_balance'] < c['safety_buffer'] else next((r['date'] for r in forecast['daily'] if r['balance'] < c['safety_buffer']), c['as_of'])}, {'monthly_spending_cut': 200})
    metrics = {x['name']: x['metric'] for x in health['components']}
    if metrics['emergency_savings'] is not None and metrics['emergency_savings'] < 3:
        add('emergency_savings', 'medium', 'Liquid reserves cover fewer than three months of modeled outflows.',
            {'months_covered': round(metrics['emergency_savings'], 2)}, {})
        alerts[-1]['guidance'] = 'Review essential cash needs and optional spending before scheduling savings transfers; a transfer alone does not increase combined liquid reserves.'
    if metrics['debt_management'] is not None and metrics['debt_management'] > .36:
        surplus = c['monthly_income']-c['monthly_variable_spending']-sum(b['amount'] for b in c['bills'])
        can_test_extra = low >= c['safety_buffer'] and surplus >= 100 and metrics['emergency_savings'] is not None and metrics['emergency_savings'] >= 3
        add('debt_burden', 'high', 'Scheduled debt payments exceed 36% of modeled income.',
            {'debt_to_income': round(metrics['debt_management'], 4)}, {'extra_debt_payment': 100} if can_test_extra else {})
        alerts[-1]['guidance'] = 'Compare any extra payment with keeping enough cash for essential bills; high debt burden alone is not a reason to accelerate repayment.'
    pressure = [r for r in forecast['daily'] if r['bills'] > max(0, r['balance'] + r['bills'])]
    if pressure:
        add('payment_pressure', 'high', 'A scheduled bill exceeds available modeled cash on its due date.',
            {'date': pressure[0]['date'], 'bills': pressure[0]['bills']}, {'monthly_spending_cut': 200})
    if c.get('budget') and c['monthly_variable_spending'] > c['budget']*1.2:
        add('spending_above_budget', 'medium', 'Variable spending exceeds the supplied budget by more than 20%.',
            {'spending': c['monthly_variable_spending'], 'budget': c['budget']}, {'monthly_spending_cut': 200})
        alerts[-1]['guidance'] = 'Review optional spending categories and compare a spending-cut scenario while preserving essential bills.'
    if c.get('budget'):
        months = {}
        for row in forecast['daily']:
            months.setdefault(row['date'][:7], []).append(row)
        for month, rows in sorted(months.items()):
            year, mo = map(int, month.split('-'))
            if len(rows) != calendar.monthrange(year, mo)[1]:
                continue
            total = round(sum(row['spending'] for row in rows), 2)
            if total <= c['budget']*1.2:
                continue
            accumulated, crossing = 0., rows[-1]['date']
            for row in rows:
                accumulated += row['spending']
                if accumulated > c['budget']*1.2:
                    crossing = row['date']
                    break
            add('projected_spending_above_budget', 'medium', 'A complete forecast month exceeds the variable-spending budget by more than 20%.',
                {'month': month, 'projected_month_spending': total, 'budget': c['budget'],
                 'over_budget_usd': round(total-c['budget'], 2), 'first_breach_date': crossing},
                {'monthly_spending_cut': min(200., c['monthly_variable_spending'])})
            alerts[-1]['guidance'] = 'Compare optional spending changes against the forecast; this planning total is uncertain and is not a bill.'
            break
    if economy and economy.get('available'):
        from .conditions import personalized_condition_alerts
        for candidate in personalized_condition_alerts(c, forecast, health, economy.get('conditions', {})):
            add(candidate['id'], candidate['severity'], candidate['explanation'], candidate['evidence'], candidate['suggested_simulation'])
            alerts[-1]['guidance'] = candidate['guidance']
            alerts[-1]['tradeoff'] = candidate['tradeoff']
    return alerts


def evaluate(profile, forecast):
    """backend-mvp typed gateway entry; preserves detect_risks dictionaries."""
    from .backend_adapter import guardian_profile
    return guardian_profile(profile, forecast)
