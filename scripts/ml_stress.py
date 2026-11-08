"""Controlled scenarios: financial invariants, NEVER synthetic accuracy labels."""
import json
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import date,timedelta
from decimal import Decimal as D

import pandas as pd

from backend.intelligence.data import ROOT
sys.path.insert(0,str(ROOT/'backend'))
from app.calc.models import Account,Bill,FinancialProfile,IncomeSource,Transaction,User
from app.calc import metrics as m
from app.services.forecast import get_forecast
from app.services.gateway import Gateway
from backend.intelligence.backend_adapter import _project,health_profile,guardian_profile

OUT=ROOT/'reports/ml_evaluation'
AS_OF=date(2026,11,7)


def profile():
    transactions=[]
    for i in range(120):
        for cat in ('groceries','dining'):
            transactions.append(Transaction(f'{cat}-{i}','checking',D('-10'),cat,AS_OF-timedelta(days=i)))
    return FinancialProfile(User('stress','Fictional stress profile',''),AS_OF,
        [Account('checking','stress','Checking','checking',D('2400')),
         Account('savings','stress','Savings','savings',D('600'))],transactions,
        [Bill('rent','stress','Rent',D('1500'),'rent','monthly',AS_OF+timedelta(days=4)),
         Bill('utilities','stress','Utilities',D('200'),'utilities','monthly',AS_OF+timedelta(days=6))],
        [IncomeSource('pay','stress','Pay',D('2100'),'biweekly',AS_OF+timedelta(days=11))])


def spending_path(forecast):
    return {'model':'controlled_scenario','days':30,'daily':[
        {'date':str(r.date),'spending':float(r.predicted_spend),
         'lower':float(r.predicted_spend),'upper':float(r.predicted_spend)} for r in forecast.series]}


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    original=profile();saved=deepcopy(original)
    base=get_forecast(original,Gateway('auto'),30)
    path=spending_path(base)
    cases=[('BASE','reference',original,deepcopy(path))]
    cases.append(('A_income_minus_30pct','deterministic',replace(original,income_sources=[replace(s,amount=s.amount*D('.7')) for s in original.income_sources]),deepcopy(path)))
    cases.append(('B_emergency_1500','deterministic',replace(original,accounts=[replace(a,balance=a.balance-D('1500')) if a.account_type=='checking' else a for a in original.accounts]),deepcopy(path)))
    inflated=deepcopy(path)
    for row in inflated['daily']:
        for k in ('spending','lower','upper'):row[k]*=1.1 # half of variable spend is essential
    cases.append(('C_essential_cost_plus_20pct','deterministic',replace(original,bills=[replace(b,amount=b.amount*D('1.2')) for b in original.bills]),inflated))
    surge=deepcopy(path)
    for row in surge['daily'][:7]:
        for k in ('spending','lower','upper'):row[k]+=100
    cases.append(('D_discretionary_surge_week','future stress assumption, not accuracy',original,surge))
    surged_history=[replace(t,amount=t.amount-D('50')) if t.category=='dining' and t.date>AS_OF-timedelta(days=7) else t for t in original.transactions]
    cases.append(('D2_observed_recent_surge','ML out-of-distribution / history shock',replace(original,transactions=surged_history),None))
    cases.append(('E_delayed_paycheck','deterministic',replace(original,income_sources=[replace(s,next_pay_date=s.next_pay_date+timedelta(days=35)) for s in original.income_sources]),deepcopy(path)))
    cases.append(('F_clustered_bills','deterministic',replace(original,bills=[replace(b,due_date=AS_OF+timedelta(days=i+1)) for i,b in enumerate(original.bills)]),deepcopy(path)))
    cases.append(('G_one_history_day','ML out-of-distribution / cold start',replace(original,transactions=original.transactions[:2]),None))
    # The contract represents regular recurrences, not uncertain irregular future income.
    cases.append(('H_irregular_income_assumption','deterministic known events; uncertainty unsupported',replace(original,income_sources=[IncomeSource('i1','stress','Assumed gig',D('500'),'monthly',AS_OF+timedelta(days=2)),IncomeSource('i2','stress','Assumed gig',D('2500'),'monthly',AS_OF+timedelta(days=27))]),deepcopy(path)))
    cases.append(('I_high_debt','deterministic',replace(original,bills=original.bills+[Bill('debt','stress','Debt',D('2500'),'debt_payment','monthly',AS_OF+timedelta(days=3))]),deepcopy(path)))
    zero_transactions=[replace(t,amount=D('0')) for t in original.transactions]
    zero_transactions += [Transaction('refund','checking',D('100'),'refund',AS_OF),Transaction('transfer','checking',D('-300'),'transfer',AS_OF)]
    cases.append(('J_zero_refund_transfer','ML distribution shift and accounting',replace(original,transactions=zero_transactions),None))
    records=[]
    base_result=None
    for name,kind,p,pth in cases:
        try:
            f=get_forecast(p,Gateway('auto'),30) if pth is None else _project(p,pth)
            h=health_profile(p);alerts=guardian_profile(p,f)
            income=sum((x for _,x in m.income_events(p,30)),D(0))
            bills=sum((b.amount for _,b in m.bill_occurrences(p,30)),D(0))
            spend=sum((r.predicted_spend for r in f.series),D(0))
            # The public API rounds daily amounts/point balances to cents.
            expected=m.cash_balance(p)+income-bills-spend
            residual=f.series[-1].projected_balance-expected
            row={'case':name,'type':kind,'source':f.meta.source,'warning':f.meta.warning,
                'spending_total':float(spend),'projected_min':float(min(m.cash_balance(p),*(r.projected_balance for r in f.series))),
                'ending_balance':float(f.series[-1].projected_balance),'health_score':h.score,
                'alerts':[a.rule for a in alerts],'reconciliation_residual':float(residual),'crashed':False,
                'finite_outputs':bool(all(r.low.is_finite() and r.high.is_finite() and r.projected_balance.is_finite() for r in f.series)),
                'score_bounded':0<=h.score<=100}
            if base_result is None:base_result=row
            row['ending_change']=round(row['ending_balance']-base_result['ending_balance'],2)
            row['health_change']=round(row['health_score']-base_result['health_score'],2)
            row['invariants_pass']=residual==0 and row['finite_outputs'] and row['score_bounded']
            records.append(row)
        except Exception as exc:
            records.append({'case':name,'type':kind,'crashed':True,'error':type(exc).__name__+': '+str(exc),'invariants_pass':False})
    assert original==saved,'Scenario altered original profile'
    (OUT/'stress_results.json').write_text(json.dumps(records,indent=2))
    pd.DataFrame(records).to_csv(OUT/'stress_results.csv',index=False)
    print(pd.DataFrame(records)[['case','ending_balance','projected_min','health_score','ending_change','invariants_pass']].to_string(index=False))
    return records


if __name__=='__main__':run()
