"""Personal exposure and deterministic stress planning, separate from baseline health."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .personal_finance import FinancialFacts,assess


class EconomicScenario(BaseModel):
    model_config=ConfigDict(extra='forbid')
    type: Literal['essential_cost_increase','cash_expense_increase','income_reduction','income_interruption','missed_paycheck','emergency_expense',
                  'variable_rate_payment','delayed_paycheck','fixed_bill_increase','debt_repayment','savings_transfer']
    fraction: D=Field(default=D('.1'),ge=0,le=1,allow_inf_nan=False)
    amount: D=Field(default=D('1000'),ge=0,allow_inf_nan=False,max_digits=14,decimal_places=2)
    delay_days: int=Field(default=7,ge=1,le=90)
    liability_account_id: str|None=None

    @model_validator(mode='after')
    def explicit_assumption(self):
        needed=('fraction' if self.type in ('essential_cost_increase','cash_expense_increase','income_reduction') else
                'delay_days' if self.type=='delayed_paycheck' else 'amount' if self.type in ('emergency_expense','variable_rate_payment','fixed_bill_increase','debt_repayment','savings_transfer') else None)
        if needed and needed not in self.model_fields_set:raise ValueError(f'An explicit {needed} assumption is required')
        return self


def plan(profile,facts):
    from app.calc import metrics as m
    from app.calc.categories import ESSENTIAL,DISCRETIONARY
    income={};bills={}
    for day,value in m.income_events(profile,30):income[day]=income.get(day,D(0))+value
    for day,bill in m.bill_occurrences(profile,30):bills[day]=bills.get(day,D(0))+bill.amount
    fixed_essential=sum((m._per_30_days(b.amount,b.frequency) for b in profile.bills if b.category in ESSENTIAL and b.category!='debt_payment'),D(0))
    fixed_discretionary=sum((m._per_30_days(b.amount,b.frequency) for b in profile.bills if b.category in DISCRETIONARY),D(0))
    classified=all(b.category in ESSENTIAL|DISCRETIONARY for b in profile.bills)
    complete=facts.essential_cash_expenses is not None and facts.discretionary_cash_expenses is not None and facts.bills_complete and classified
    budget=(max(D(0),facts.essential_cash_expenses-fixed_essential)+max(D(0),facts.discretionary_cash_expenses-fixed_discretionary)) if complete else D(0)
    # Reconcile cents over the full horizon; do not accumulate 1/30 cent fractions.
    variable=[(budget*(i+1)/30).quantize(D('.01'))-(budget*i/30).quantize(D('.01')) for i in range(30)]
    balance=m.cash_balance(profile);rows=[]
    for i in range(30):
        day=profile.as_of+timedelta(days=i+1)
        balance+=income.get(day,D(0))-bills.get(day,D(0))-variable[i]
        rows.append({'date':str(day),'balance':float(balance),'income':float(income.get(day,D(0))),
                     'bills':float(bills.get(day,D(0))),'variable_budget':float(variable[i])})
    minimum=min([float(m.cash_balance(profile))]+[r['balance'] for r in rows])
    alerts=[]
    if minimum<float(profile.user.safety_buffer):
        alerts.append({'id':'scheduled_cash_pressure','severity':'high','cause':'Deterministic assumed cash path falls below the chosen safety buffer.',
                       'numbers':{'minimum':minimum,'buffer':float(profile.user.safety_buffer)},
                       'action':'Review confirmed bill dates, expected deposits and optional spending; this is a planning scenario, not a validated forecast.'})
    return {'status':'budget_and_schedules' if complete else 'known_schedules_only',
        'series':rows,'minimum_checking':minimum,'ending_checking':rows[-1]['balance'],'alerts':alerts,
        'note':'Deterministic 30-day planning arithmetic, not an ML prediction. Missing variable budgets are omitted and explicitly marked.'}


def financial_alerts(health,cash):
    alerts=list(cash['alerts'])
    metrics=health['metrics']
    if metrics['monthly_surplus'] is not None and metrics['monthly_surplus']<0:
        alerts.append({'id':'negative_confirmed_surplus','severity':'high',
            'cause':'Confirmed monthly cash outflows exceed confirmed take-home income.',
            'numbers':{'monthly_surplus':metrics['monthly_surplus']},'action':'Compare changes to optional spending, income timing and required obligations using explicit assumptions.'})
    if metrics['emergency_months'] is not None and metrics['emergency_months']<6:
        alerts.append({'id':'reserve_benchmark_gap','severity':'low',
            'cause':'Eligible emergency reserves are below the contextual six-month benchmark; actual needs differ by household.',
            'numbers':{'months':metrics['emergency_months']},'action':'Choose a household-specific reserve goal while preserving imminent payment coverage.'})
    return alerts


def simulate_economic(profile,facts,scenario):
    from app.calc import metrics as m
    from app.calc.categories import ESSENTIAL
    original=deepcopy(profile);p=deepcopy(profile);f=facts.model_copy(deep=True)
    s=scenario;updates={}
    if s.type=='income_reduction':
        p=replace(p,income_sources=[replace(x,amount=(x.amount*(1-s.fraction)).quantize(D('.01'))) for x in p.income_sources])
        if f.take_home_income is not None:updates['take_home_income']=(f.take_home_income*(1-s.fraction)).quantize(D('.01'))
    elif s.type=='income_interruption':
        p=replace(p,income_sources=[])
        if f.take_home_income is not None:updates['take_home_income']=D(0)
    elif s.type=='missed_paycheck':
        upcoming=[(days[0],source) for source in p.income_sources
                  if (days:=m._occurrences(source.next_pay_date,source.frequency,p.as_of,90))]
        if not upcoming:raise ValueError('No known upcoming paycheck to remove')
        when,source=min(upcoming,key=lambda pair:pair[0])
        following=m.add_months(when,1) if source.frequency=='monthly' else when+timedelta(days=14 if source.frequency=='biweekly' else 7)
        p=replace(p,income_sources=[replace(x,next_pay_date=following) if x.id==source.id else x for x in p.income_sources])
        if f.take_home_income is not None:updates['take_home_income']=max(D(0),f.take_home_income-source.amount)
    elif s.type=='delayed_paycheck':
        # The next paycheck on each source is delayed; subsequent recurrences
        # are shifted too, an explicit schedule assumption in this prototype.
        p=replace(p,income_sources=[replace(x,next_pay_date=x.next_pay_date+timedelta(days=s.delay_days)) for x in p.income_sources])
    elif s.type in ('essential_cost_increase','cash_expense_increase'):
        p=replace(p,bills=[replace(b,amount=(b.amount*(1+s.fraction)).quantize(D('.01'))) if (b.category in ESSENTIAL or s.type=='cash_expense_increase') and b.category!='debt_payment' else b for b in p.bills])
        if f.essential_cash_expenses is not None:updates['essential_cash_expenses']=(f.essential_cash_expenses*(1+s.fraction)).quantize(D('.01'))
        if s.type=='cash_expense_increase' and f.discretionary_cash_expenses is not None:updates['discretionary_cash_expenses']=(f.discretionary_cash_expenses*(1+s.fraction)).quantize(D('.01'))
    elif s.type in ('emergency_expense','debt_repayment','savings_transfer'):
        checking=[a for a in p.accounts if a.account_type=='checking']
        if not checking:raise ValueError('An imported checking account is required')
        first=checking[0]
        changes={first.id:replace(first,balance=first.balance-s.amount)}
        if s.type=='debt_repayment':
            loan=next((a for a in p.accounts if a.id==s.liability_account_id and a.account_type in ('loan','credit_card')),None)
            if loan is None or s.amount>loan.balance or s.amount>max(D(0),first.balance):raise ValueError('Repayment must use owned debt, available checking, and not exceed principal')
            changes[loan.id]=replace(loan,balance=loan.balance-s.amount)
        if s.type=='savings_transfer':
            savings=next((a for a in p.accounts if a.account_type=='savings'),None)
            if savings is None or s.amount>max(D(0),first.balance):raise ValueError('Transfer requires available checking and an imported savings account')
            changes[savings.id]=replace(savings,balance=savings.balance+s.amount)
            if f.accessible_emergency_savings is not None:updates['accessible_emergency_savings']=f.accessible_emergency_savings+s.amount
        p=replace(p,accounts=[changes.get(a.id,a) for a in p.accounts])
    elif s.type in ('variable_rate_payment','fixed_bill_increase'):
        from app.calc.models import Bill
        if s.type=='variable_rate_payment' and not (f.variable_rate_balance is not None and f.variable_rate_balance>0):
            raise ValueError('Variable-rate exposure must be explicitly confirmed; fixed debt does not automatically reprice')
        category='debt_payment' if s.type=='variable_rate_payment' else 'insurance'
        p=replace(p,bills=p.bills+[Bill('hypothetical-extra',p.user.id,'Hypothetical additional payment',s.amount,category,'monthly',p.as_of+timedelta(days=1))])
        if s.type=='variable_rate_payment' and f.required_debt_payments is not None:updates['required_debt_payments']=f.required_debt_payments+s.amount
        if s.type=='fixed_bill_increase' and f.essential_cash_expenses is not None:updates['essential_cash_expenses']=f.essential_cash_expenses+s.amount
    f=f.model_copy(update=updates)
    before={'health':assess(profile,facts),'cash_plan':plan(profile,facts)}
    after={'health':assess(p,f),'cash_plan':plan(p,f)}
    for output in (before,after):output['guardian_alerts']=financial_alerts(output['health'],output['cash_plan'])
    assert profile==original,'Simulation mutated original records'
    return {'scenario':s.model_dump(mode='json'),'before':before,'after':after,
        'ending_checking_change':round(after['cash_plan']['ending_checking']-before['cash_plan']['ending_checking'],2),
        'net_worth_change':float(m.net_worth(p)-m.net_worth(profile)),
        'score_changes':[{'component':a['name'],'before':b['score'],'after':a['score'],
            'difference':round(a['score']-b['score'],2) if a['score'] is not None and b['score'] is not None else None,
            'explanation':a['formula']} for b,a in zip(before['health']['components'],after['health']['components']) if b['score']!=a['score']],
        'note':'Hypothetical assumptions, not event probabilities. Principal repayment does not automatically reduce future minimums; no amortization inferred.'}


def resilience(profile,facts,economy):
    assessment=assess(profile,facts);metrics=assessment['metrics'];features=economy['features'];alerts=[]
    def add(code,cause,numbers,scenario):
        alerts.append({'id':code,'severity':'medium','cause':cause,'numbers':numbers,'scenario':scenario,
            'action':'Compare this adjustable stress assumption; it is not a forecast or an instruction to move money.'})
    pce=features.get('PCEPI_yoy_pct')
    vulnerable=(metrics['monthly_surplus'] is not None and facts.essential_cash_expenses is not None and metrics['monthly_surplus']<float(facts.essential_cash_expenses*D('.1'))) or (metrics['emergency_months'] is not None and metrics['emergency_months']<6)
    if pce is not None and pce>2 and vulnerable and facts.essential_cash_expenses is not None and facts.take_home_income is not None and facts.take_home_income>0:
        add('inflation_exposure','PCE inflation is above the longer-run objective. Your confirmed essential budget is exposed to cost changes; headline inflation is not applied uniformly.',
            {'pce_yoy_pct':pce,'essential_share':float(facts.essential_cash_expenses/facts.take_home_income)}, {'type':'essential_cost_increase','fraction':.1})
    sahm=features.get('sahm_official_pp') if features.get('sahm_official_pp') is not None else features.get('sahm_computed_pp')
    if sahm is not None and sahm>=.5 and profile.income_sources and metrics['emergency_months'] is not None and metrics['emergency_months']<6:
        add('labor_resilience','The Sahm indicator is triggered. Test an income interruption; this does not predict your employment outcome.',
            {'sahm_pp':sahm,'emergency_months':metrics['emergency_months']},{'type':'income_interruption'})
    if features.get('policy_rate_change_3m_pp') is not None and features['policy_rate_change_3m_pp']>0 and facts.variable_rate_balance is not None and facts.variable_rate_balance>0:
        add('variable_rate_exposure','Policy rates increased and variable-rate debt was explicitly reported. Contract reset terms determine actual payments.',
            {'confirmed_variable_balance':float(facts.variable_rate_balance)},{'type':'variable_rate_payment','amount':100})
    if any(d['name']=='market' and d['flagged'] for d in economy['dimensions']) and facts.risky_holdings_value is not None and facts.risky_holdings_value>0 and facts.near_term_investment_cash_need is not None and facts.near_term_investment_cash_need>0:
        add('investment_liquidity_exposure','Market stress coincides with your reported need to sell investments for near-term cash. Checking balances are not marked down by equity prices.',
            {'holdings':float(facts.risky_holdings_value),'near_term_need':float(facts.near_term_investment_cash_need)}, {'type':'emergency_expense','amount':1000})
    return {'baseline_health':assessment,'economic_conditions':economy,'alerts':alerts,
            'financial_alerts':financial_alerts(assessment,plan(profile,facts)),
            'note':'Economic conditions contextualize vulnerability and never rewrite the baseline personal score.'}
