"""Profile-scoped orchestration. HTTP handlers read cached data, never refresh it."""
from intelligence.economic_data import cached
from intelligence.regimes import classify
from intelligence.personal_finance import assess,FinancialFacts
from intelligence.resilience import resilience,simulate_economic,EconomicScenario
from app.services.notices import notices_for


def provenance(result,profile):
    # These calculations consume confirmed budgets and dated schedules, not the
    # ML cash forecast. Do not invent or borrow a forecast confidence label.
    return {**result,'forecast_dependency':'none; deterministic assessment or confirmed-assumption cash plan',
            'data_notices':[n.model_dump() for n in notices_for(profile.data_warnings,'bank_data')]}


def conditions(as_of):
    return classify(cached(),str(as_of))


def _with_observed(result,profile):
    from app.calc import metrics as m
    from app.calc.categories import ESSENTIAL,DISCRETIONARY
    from decimal import Decimal,ROUND_CEILING
    cents=lambda value:value.quantize(Decimal('.01'),rounding=ROUND_CEILING)
    fixed_essential=cents(sum((m._per_30_days(b.amount,b.frequency) for b in profile.bills if b.category in ESSENTIAL and b.category!='debt_payment'),Decimal(0)))
    fixed_discretionary=cents(sum((m._per_30_days(b.amount,b.frequency) for b in profile.bills if b.category in DISCRETIONARY),Decimal(0)))
    spend=m.spend_by_category(profile,90)
    essential_variable=cents(sum((v for k,v in spend.items() if k in ESSENTIAL and k not in {'rent','utilities','insurance','debt_payment'}),Decimal(0))/3)
    nonessential_variable=cents(sum((v for k,v in spend.items() if k not in ESSENTIAL),Decimal(0))/3)
    warnings=' '.join(profile.data_warnings).lower()
    schedule_complete=not any(x in warnings for x in ('payment dates must be supplied','upcoming bills are incomplete'))
    inferred=FinancialFacts(take_home_income=m.monthly_income(profile),
        essential_cash_expenses=fixed_essential+essential_variable,
        discretionary_cash_expenses=fixed_discretionary+nonessential_variable,
        required_debt_payments=m.monthly_debt_payments(profile),
        accessible_emergency_savings=sum((max(Decimal(0),a.balance) for a in profile.accounts if a.account_type=='savings'),Decimal(0)),
        bills_complete=schedule_complete,debt_complete=True)
    observed=assess(profile,inferred)
    supported=[c for c in observed['components'] if c['score'] is not None]
    observed_score=round(sum(c['score']*c['weight'] for c in supported)/sum(c['weight'] for c in supported),2) if supported else None
    limitations=[]
    if 'unmapped purchases' in warnings:limitations.append('Some purchases are uncategorized, so essential-versus-optional spending is uncertain.')
    if 'deposits are money received' in warnings:limitations.append('Recorded deposits are not verified take-home salary.')
    if not schedule_complete:limitations.append('The imported payment calendar may be incomplete.')
    if len(profile.transactions)<30:limitations.append('Transaction history is limited.')
    confidence='low' if limitations else 'medium'
    result.update({'observed_score':observed_score,
        'observed_score_basis':'imported_accounts_transactions_bills_and_income_schedules',
        'observed_score_explanation':'Automatic estimate from imported records using scheduled income, recurring bills, debt minimums, savings and 90-day spending. Missing components are omitted and remaining weights are normalized.',
        'observed_score_confidence':confidence,'observed_score_limitations':limitations,
        'observed_components':observed['components']})
    return result


def assessment(profile,facts=None):
    result=_with_observed(assess(profile,facts or FinancialFacts()),profile)
    return provenance(result,profile)


def contextual(profile,facts=None):
    result=resilience(profile,facts or FinancialFacts(),conditions(profile.as_of))
    result['baseline_health']=_with_observed(result['baseline_health'],profile)
    return provenance(result,profile)


def simulate(profile,facts,scenario):
    return provenance(simulate_economic(profile,facts,scenario),profile)
