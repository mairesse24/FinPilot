"""Representative profiles and one-factor sensitivity; no invented score labels."""
import json
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D
from pathlib import Path
import sys
import pandas as pd
from backend.intelligence.economic_data import ROOT
sys.path.insert(0,str(ROOT/'backend'))
from app.calc.models import Account,Transaction,Bill
from scripts.ml_stress import profile
from backend.intelligence.personal_finance import assess,FinancialFacts

OUT=ROOT/'reports/economic_intelligence'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=profile()
    f=FinancialFacts(take_home_income=4200,essential_cash_expenses=1900,discretionary_cash_expenses=400,
        required_debt_payments=0,accessible_emergency_savings=600,bills_complete=True,debt_complete=True)
    def savings(amount):return replace(p,accounts=[replace(a,balance=D(str(amount))) if a.account_type=='savings' else a for a in p.accounts])
    def debt_profile(amount,base=None):
        base=base or p
        return replace(base,bills=base.bills+[Bill('confirmed-debt','stress','Confirmed required debt',D(str(amount)),'debt_payment','monthly',base.as_of+timedelta(days=3))])
    low_cost=replace(p,bills=[replace(b,amount=b.amount*D('.5')) for b in p.bills])
    irregular=[]
    for i,amount in enumerate([0,7000,1000,6000,1200,8000]):
        irregular.append(Transaction(f'irregular-{i}','checking',D(amount),'income',p.as_of-timedelta(days=30*(i+1))))
    irregular.append(Transaction('coverage-start','checking',D(0),'income',p.as_of-timedelta(days=220)))
    cases=[('base',p,f),('high_income_high_debt',debt_profile(6000),f.model_copy(update={'take_home_income':D(12000),'required_debt_payments':D(6000)})),
        ('low_income_strong_savings',replace(savings(12000),bills=low_cost.bills),f.model_copy(update={'take_home_income':D(2000),'accessible_emergency_savings':D(12000),'essential_cash_expenses':D(1000),'discretionary_cash_expenses':D(100)})),
        ('high_income_no_emergency_savings',savings(0),f.model_copy(update={'take_home_income':D(12000),'accessible_emergency_savings':D(0)})),
        ('low_income_manageable',low_cost,f.model_copy(update={'take_home_income':D(2000),'essential_cash_expenses':D(1000),'discretionary_cash_expenses':D(100)})),
        ('irregular_income_large_reserves',replace(savings(12000),transactions=p.transactions+irregular),f.model_copy(update={'accessible_emergency_savings':D(12000),'income_history_complete':True})),
        ('high_card_utilization',debt_profile(100,replace(p,accounts=p.accounts+[Account('card','stress','Revolving card','credit_card',D(900),credit_limit=D(1000))])),f.model_copy(update={'required_debt_payments':D(100)})),
        ('strong_savings_poor_payment_timing',replace(savings(12000),accounts=[replace(a,balance=D(50)) if a.account_type=='checking' else a for a in savings(12000).accounts]),f.model_copy(update={'accessible_emergency_savings':D(12000)})),
        ('negative_cash_flow',p,f.model_copy(update={'take_home_income':D(1500)})),
        ('missing_financial_inputs',p,FinancialFacts()),
        ('confirmed_zero_income',p,f.model_copy(update={'take_home_income':D(0)}))]
    rows=[]
    for name,case,facts in cases:
        result=assess(case,facts)
        rows.append({'profile':name,'score':result['score'],'completeness':result['completeness']['fraction'],
            **{c['name']:c['score'] for c in result['components']},
            'emergency_months':result['metrics']['emergency_months'],'monthly_surplus':result['metrics']['monthly_surplus'],
            'credit_utilization':result['metrics']['credit_utilization'],'income_monthly_cv':result['metrics']['income_monthly_cv']})
    pd.DataFrame(rows).to_csv(OUT/'financial_profiles.csv',index=False)
    sensitivity=[]
    changes=[('savings',x) for x in (1.1,1.25,1.5)]+[('income',x) for x in (.9,.8,.7)]+[('essential',x) for x in (1.1,1.2)]+[('debt',x) for x in (1.1,1.25)]+[('checking',x) for x in (.1,.5,1.5)]
    for field,factor in changes:
        factor=D(str(factor));q=p;g=f
        if field=='savings':q=savings(600*factor);g=f.model_copy(update={'accessible_emergency_savings':D(600)*factor})
        if field=='income':g=f.model_copy(update={'take_home_income':D(4200)*factor})
        if field=='essential':g=f.model_copy(update={'essential_cash_expenses':D(1900)*factor})
        if field=='debt':g=f.model_copy(update={'required_debt_payments':D(200)*factor});q=debt_profile(D(200)*factor)
        if field=='checking':q=replace(p,accounts=[replace(a,balance=a.balance*factor) if a.account_type=='checking' else a for a in p.accounts])
        result=assess(q,g)
        # Debt sensitivity baseline is $200 debt, not the debt-free base.
        base=assess(debt_profile(200),f.model_copy(update={'required_debt_payments':D(200)})) if field=='debt' else assess(p,f)
        sensitivity.append({'input':field,'factor':float(factor),'score':result['score'],'change':round(result['score']-base['score'],4),
                            **{c['name']:c['score'] for c in result['components']}})
    pd.DataFrame(sensitivity).to_csv(OUT/'score_sensitivity.csv',index=False)
    weights=[]
    for row in rows:
        if row['score'] is None:continue
        scores=[row[c['name']] for c in assess(p,f)['components']]
        for i,name in enumerate([c['name'] for c in assess(p,f)['components']]):
            for weight in (.20,.30):
                weighted=scores[i]*weight+sum(s for j,s in enumerate(scores) if j!=i)*(1-weight)/3
                weights.append({'profile':row['profile'],'component':name,'varied_weight':weight,'score':weighted,'difference':weighted-row['score']})
    pd.DataFrame(weights).to_csv(OUT/'weight_sensitivity.csv',index=False)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__=='__main__':main()
