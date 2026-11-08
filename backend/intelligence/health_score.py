"""Explainable design-assumption wellness score; not a credit score."""
from .validation import validate_customer


def health_score(c):
    validate_customer(c)
    income = c['monthly_income']
    bills = sum(b['amount'] for b in c['bills'])
    expenses = bills + c['monthly_variable_spending']
    liquid = max(0, c['checking_balance']) + c['savings_balance']
    surplus = (income-expenses)/income if income else None
    emergency = liquid/expenses if expenses else None
    dti = c['monthly_debt_payments']/income if income else None
    budget = c.get('budget')
    clamp = lambda x: round(max(0, min(100, x)), 2)
    components = [
        {'name': 'cash_flow_stability', 'weight': .25,
         'score': clamp(50+250*surplus) if surplus is not None else None,
         'metric': surplus, 'formula': 'clip(50 + 250 * (income - expenses) / income, 0, 100)'},
        {'name': 'emergency_savings', 'weight': .25,
         'score': clamp(emergency/6*100) if emergency is not None else None,
         'metric': emergency, 'formula': 'clip(liquid cash / total monthly outflow / 6 * 100, 0, 100)'},
        {'name': 'debt_management', 'weight': .20,
         'score': clamp(100*(1-dti/.5)) if dti is not None else None,
         'metric': dti, 'formula': 'clip(100 * (1 - debt payments / income / 0.5), 0, 100)'},
        {'name': 'spending_discipline', 'weight': .15,
         'score': clamp(100*min(1, budget/max(c['monthly_variable_spending'], .01))) if budget else None,
         'metric': c['monthly_variable_spending']/budget if budget else None,
         'formula': 'min(100, budget / variable spending * 100); unknown without explicit budget'},
        {'name': 'payment_readiness', 'weight': .15,
         'score': clamp(max(0, c['checking_balance'])/bills*100) if bills else 100.,
         'metric': bills, 'formula': 'clip(checking / next full month scheduled bills * 100, 0, 100)'},
    ]
    available = [x for x in components if x['score'] is not None]
    weight = sum(x['weight'] for x in available)
    return {'score': round(sum(x['score']*x['weight'] for x in available)/weight, 2) if weight else None,
            'components': components, 'observed_weight': round(weight, 2),
            'note': 'Prototype wellness heuristic, not a credit score. Missing components are excluded and weights renormalized. Stability currently measures surplus, not income volatility.'}


def compute_health_score(profile):
    """backend-mvp typed gateway entry; preserves health_score(customer)."""
    from .backend_adapter import health_profile
    return health_profile(profile)
