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


def _inferred_facts(profile):
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
    return FinancialFacts(take_home_income=m.monthly_income(profile),
        essential_cash_expenses=fixed_essential+essential_variable,
        discretionary_cash_expenses=fixed_discretionary+nonessential_variable,
        required_debt_payments=m.monthly_debt_payments(profile),
        accessible_emergency_savings=sum((max(Decimal(0),a.balance) for a in profile.accounts if a.account_type=='savings'),Decimal(0)),
        bills_complete=schedule_complete,debt_complete=True)


def _normalized_score(result):
    supported=[c for c in result['components'] if c['score'] is not None]
    return round(sum(c['score']*c['weight'] for c in supported)/sum(c['weight'] for c in supported),2) if supported else None


def _with_observed(result,profile):
    inferred=_inferred_facts(profile)
    observed=assess(profile,inferred)
    observed_score=_normalized_score(observed)
    warnings=' '.join(profile.data_warnings).lower()
    schedule_complete=inferred.bills_complete
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
        'observed_components':observed['components'],'observed_metrics':observed['metrics'],
        'observed_withheld_reasons':observed['withheld_reasons']})
    return result


def _economic_impact(profile,economy):
    from decimal import Decimal
    inferred=_inferred_facts(profile)
    pce=economy.get('features',{}).get('PCEPI_yoy_pct')
    if pce is None or inferred.essential_cash_expenses is None:
        return {'available':False,'reason':'PCE inflation or an essential-spending estimate is unavailable.'}
    rate=max(Decimal(0),Decimal(str(pce))/Decimal(100))
    stressed=inferred.model_copy(update={'essential_cash_expenses':
        (inferred.essential_cash_expenses*(Decimal(1)+rate)).quantize(Decimal('.01'))})
    before=assess(profile,inferred);after=assess(profile,stressed)
    baseline=_normalized_score(before);stress=_normalized_score(after)
    extra30=(inferred.essential_cash_expenses*rate).quantize(Decimal('.01'))
    inflation_flagged=any(d.get('name')=='inflation' and d.get('flagged') for d in economy.get('dimensions',[]))
    return {'available':True,'indicator':'PCEPI','inflation_rate_pct':float(pce),
        'classification_active':inflation_flagged,'monthly_essential_baseline':float(inferred.essential_cash_expenses),
        'monthly_essential_stress':float(stressed.essential_cash_expenses),
        'additional_burn_30d':float(extra30),'additional_burn_90d':float(extra30*3),
        'baseline_score':baseline,'stress_score':stress,
        'score_change':round(stress-baseline,2) if baseline is not None and stress is not None else None,
        'method':'Sensitivity scenario: current PCE year-over-year rate is applied once to modeled essential monthly spending. This is not a prediction that every category rises equally.'}


def assessment(profile,facts=None):
    result=_with_observed(assess(profile,facts or FinancialFacts()),profile)
    return provenance(result,profile)


def contextual(profile,facts=None):
    economy=conditions(profile.as_of)
    result=resilience(profile,facts or FinancialFacts(),economy)
    result['baseline_health']=_with_observed(result['baseline_health'],profile)
    result['economic_impact']=_economic_impact(profile,economy)
    return provenance(result,profile)


def simulate(profile,facts,scenario):
    return provenance(simulate_economic(profile,facts,scenario),profile)
