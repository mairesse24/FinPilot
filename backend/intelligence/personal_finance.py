"""FinPilot-defined v2 assessment. No validated CFPB score or invented missing values.

All required facts are explicitly supplied/confirmed. Legacy v1 is preserved.
"""
from datetime import timedelta
from decimal import Decimal
from statistics import pstdev,mean
from pydantic import BaseModel,ConfigDict,Field

ZERO=Decimal(0)


class FinancialFacts(BaseModel):
    model_config=ConfigDict(extra='forbid')
    take_home_income: Decimal|None=Field(default=None,ge=0,allow_inf_nan=False,max_digits=14,decimal_places=2)
    essential_cash_expenses: Decimal|None=Field(default=None,ge=0,allow_inf_nan=False,max_digits=14,decimal_places=2)
    discretionary_cash_expenses: Decimal|None=Field(default=None,ge=0,allow_inf_nan=False,max_digits=14,decimal_places=2)
    required_debt_payments: Decimal|None=Field(default=None,ge=0,allow_inf_nan=False,max_digits=14,decimal_places=2)
    accessible_emergency_savings: Decimal|None=Field(default=None,ge=0,allow_inf_nan=False,max_digits=14,decimal_places=2)
    bills_complete: bool=False
    debt_complete: bool=False
    income_history_complete: bool=False
    gross_income: Decimal|None=Field(default=None,gt=0,allow_inf_nan=False,max_digits=14,decimal_places=2)
    variable_rate_balance: Decimal|None=Field(default=None,ge=0,allow_inf_nan=False,max_digits=14,decimal_places=2)
    risky_holdings_value: Decimal|None=Field(default=None,ge=0,allow_inf_nan=False,max_digits=14,decimal_places=2)
    near_term_investment_cash_need: Decimal|None=Field(default=None,ge=0,allow_inf_nan=False,max_digits=14,decimal_places=2)


def assess(profile,facts=None):
    from app.calc import metrics as m
    from .backend_adapter import _validate_profile
    _validate_profile(profile)
    amounts=[a.balance for a in profile.accounts]+[t.amount for t in profile.transactions]+[b.amount for b in profile.bills]+[s.amount for s in profile.income_sources]
    amounts += [v for a in profile.accounts for v in (a.min_payment,a.credit_limit,a.apr) if v is not None]
    if any(not v.is_finite() for v in amounts):
        raise ValueError('Financial observations must be finite')
    f=facts or FinancialFacts()
    cash=m.cash_balance(profile)
    savings=sum((a.balance for a in profile.accounts if a.account_type=='savings'),ZERO)
    income=f.take_home_income;essential=f.essential_cash_expenses;discretion=f.discretionary_cash_expenses
    from app.calc.categories import ESSENTIAL,DISCRETIONARY
    fixed_essential=sum((m._per_30_days(b.amount,b.frequency) for b in profile.bills if b.category in ESSENTIAL and b.category!='debt_payment'),ZERO)
    fixed_discretionary=sum((m._per_30_days(b.amount,b.frequency) for b in profile.bills if b.category in DISCRETIONARY),ZERO)
    if f.bills_complete and essential is not None and essential<fixed_essential:
        raise ValueError('Essential cash budget must include the known recurring non-debt essential bills')
    if f.bills_complete and discretion is not None and discretion<fixed_discretionary:
        raise ValueError('Discretionary cash budget must include known recurring discretionary bills')
    debt=f.required_debt_payments if f.debt_complete else None
    known_minimums=sum((a.min_payment or ZERO for a in profile.accounts if a.account_type in ('credit_card','loan')),ZERO)
    if debt is not None and debt<known_minimums:
        raise ValueError('Confirmed required debt payments cannot be below known contractual account minimums')
    if debt is None and f.debt_complete:
        ambiguous=any(b.category=='debt_payment' and not b.liability_account_id for b in profile.bills) and any(a.min_payment for a in profile.accounts)
        if not ambiguous:debt=m.monthly_debt_payments(profile)
    scheduled_debt=sum((m._per_30_days(b.amount,b.frequency) for b in profile.bills if b.category=='debt_payment'),ZERO)
    dated_obligations_complete=f.bills_complete and not (debt is not None and debt>scheduled_debt)
    incomes=m.income_events(profile,90)
    next_income=incomes[0][0] if incomes else None
    readiness_days=min(30,max(1,(next_income-profile.as_of).days)) if next_income else 30
    upcoming=sum((b.amount for _,b in m.bill_occurrences(profile,readiness_days)),ZERO)
    committed=max(ZERO,upcoming-max(ZERO,cash))
    eligible=None
    warnings=[]
    if f.accessible_emergency_savings is not None:
        if f.accessible_emergency_savings>max(ZERO,savings):
            raise ValueError('Confirmed accessible savings cannot exceed imported savings balances')
        eligible=max(ZERO,f.accessible_emergency_savings-committed) if dated_obligations_complete else None
    if not f.bills_complete:warnings.append('Upcoming obligations are not confirmed complete; payment readiness and uncommitted reserves are withheld.')
    if f.bills_complete and not dated_obligations_complete:warnings.append('Confirmed required debt payments exceed dated debt schedules; readiness and uncommitted reserves are withheld until missing payment dates are supplied.')
    extra_scheduled=max(ZERO,scheduled_debt-debt) if debt is not None else None
    outflows=essential+discretion+debt+extra_scheduled if all(v is not None for v in (essential,discretion,debt,extra_scheduled)) else None
    surplus=income-outflows if income is not None and outflows is not None else None
    essential_obligations=essential+debt if essential is not None and debt is not None else None
    emergency=eligible/essential_obligations if eligible is not None and essential_obligations is not None and essential_obligations>0 else None
    debt_ratio=debt/income if debt is not None and income is not None and income>0 else None
    components=[]
    def add(name,value,formula,reason):
        score=None if value is None else float(max(ZERO,min(Decimal(100),value)))
        components.append({'name':name,'score':round(score,2) if score is not None else None,'weight':.25,
                           'formula':formula,'reason':reason,'available':score is not None})
    add('Emergency preparedness',100*min(Decimal(1),emergency/6) if emergency is not None else None,
        '100 × clip(eligible savings / (essential non-debt expenses + required debt payments) / 6, 0, 1)',
        'Six months is contextual FDIC guidance; linear mapping is an explicit product assumption. Checking funds and committed reserves are excluded.')
    sustain=100*income/(income+outflows) if income is not None and outflows is not None and income+outflows>0 else None
    add('Cash-flow sustainability',sustain,'100 × income / (income + cash outflows)',
        'Smooth bounded resource-to-obligation balance: 50 at break-even. This mapping is a FinPilot assumption, not a validated welfare threshold.')
    affordable=(100*max(ZERO,income-debt)/income if income is not None and income>0 and debt is not None else ZERO if income==0 and debt is not None and debt>0 else None)
    add('Debt-payment affordability',affordable,'100 × max(0, income − required debt payments) / income',
        'Remaining take-home-income share after required payments; not standard gross-income DTI. Missing debt information is not zero debt.')
    readiness=(100*min(Decimal(1),max(ZERO,cash)/upcoming) if upcoming>0 else Decimal(100)) if dated_obligations_complete and any(a.account_type=='checking' for a in profile.accounts) else None
    add('Payment readiness',readiness,'100 × min(1, available checking / bills through next expected deposit, capped at 30 days)',
        'Deterministic current liquidity versus known obligations; no unreliable ML balance is authoritative. Bills on payday are conservatively due before deposit.')
    observed=sum(c['available'] for c in components)
    total=round(sum(c['score']*.25 for c in components),2) if observed==4 else None
    limits=[a.credit_limit for a in profile.accounts if a.account_type=='credit_card']
    revolving=sum((max(ZERO,a.balance) for a in profile.accounts if a.account_type=='credit_card'),ZERO)
    utilization=float(revolving/sum(limits,ZERO)) if limits and all(v is not None and v>0 for v in limits) else None
    # Monthly inflow variability is diagnostic only: not a second liquidity score.
    months={}
    for t in profile.transactions:
        if t.amount>0 and t.category in {'income','payroll'} and t.date<profile.as_of.replace(day=1):
            key=t.date.strftime('%Y-%m');months[key]=months.get(key,ZERO)+t.amount
    import pandas as pd
    month_keys=pd.date_range(pd.Timestamp(profile.as_of).replace(day=1)-pd.DateOffset(months=6),periods=6,freq='MS')
    covered=bool(profile.transactions and min(t.date for t in profile.transactions)<=month_keys[0].date())
    amounts=[float(months.get(stamp.strftime('%Y-%m'),ZERO)) for stamp in month_keys]
    cv=pstdev(amounts)/mean(amounts) if covered and f.income_history_complete and mean(amounts)>0 else None
    if cv is None:warnings.append('Six complete months of classified income are unavailable; income variability is withheld.')
    warnings.append('Account-based FinPilot v2 index; provisional equal weights. Not the CFPB questionnaire, a credit score, or scientifically validated weights.')
    return {'version':'finpilot-financial-health-v2','score':total,'components':components,
        'completeness':{'available_components':observed,'required_components':4,'fraction':observed/4},
        'withheld_reasons':[c['name']+': required confirmed inputs missing or denominator undefined' for c in components if not c['available']],
        'metrics':{'checking':float(cash),'savings':float(savings),'eligible_emergency_savings':float(eligible) if eligible is not None else None,
            'emergency_months':float(emergency) if emergency is not None else None,
            'take_home_income':float(income) if income is not None else None,'monthly_cash_outflows':float(outflows) if outflows is not None else None,
            'monthly_essential_obligations':float(essential_obligations) if essential_obligations is not None else None,
            'monthly_surplus':float(surplus) if surplus is not None else None,'required_debt_payments':float(debt) if debt is not None else None,
            'scheduled_extra_debt_cash':float(extra_scheduled) if extra_scheduled is not None else None,
            'cash_surplus_rate':float(surplus/income) if surplus is not None and income is not None and income>0 else None,
            'debt_payment_to_takehome_ratio':float(debt_ratio) if debt_ratio is not None else None,
            'gross_income_dti':float(debt/f.gross_income) if debt is not None and f.gross_income is not None else None,
            'credit_utilization':utilization,'recorded_debt_balance':float(m.liabilities(profile)),'net_worth':float(m.net_worth(profile)),
            'bills_before_income':float(upcoming),'readiness_horizon_days':readiness_days,
            'next_income_date':str(next_income) if next_income else None,'income_monthly_cv':cv,
            'net_savings_rate':None,'net_savings_rate_reason':'Balance changes do not identify income-attributable net saving; transfers are not new wealth.'},
        'strengths':[c['name'] for c in components if c['score'] is not None and c['score']>=75],
        'improvement_opportunities':[c['name'] for c in components if c['score'] is not None and c['score']<50],
        'warnings':warnings,'assumptions':f.model_dump(mode='json'),'as_of':str(profile.as_of)}
