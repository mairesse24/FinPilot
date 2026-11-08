from copy import deepcopy
from dataclasses import replace
from datetime import date
from decimal import Decimal as D
import json
import numpy as np
import pandas as pd
import pytest
import httpx
from scripts.ml_stress import profile
from backend.intelligence.personal_finance import FinancialFacts,assess
from backend.intelligence.resilience import EconomicScenario,simulate_economic,resilience
from backend.intelligence.regimes import classify,sahm
from backend.intelligence.economic_data import FredClient


def facts(**kwargs):
    return FinancialFacts(take_home_income=D('4200'),essential_cash_expenses=D('1900'),
        discretionary_cash_expenses=D('400'),required_debt_payments=D('0'),accessible_emergency_savings=D('600'),
        bills_complete=True,debt_complete=True,**kwargs)


def series(identifier,values,dates,knowledge='2026-11-07',pit=True):
    return {'id':identifier,'knowledge_date':knowledge,'point_in_time':pit,'source_url':'https://fred.stlouisfed.org/series/'+identifier,
            'observations':[{'date':str(pd.Timestamp(d).date()),'value':v,'available_on':knowledge} for d,v in zip(dates,values)]}


def test_independently_worked_score_and_missing_inputs():
    r=assess(profile(),facts())
    assert r['score']==67.47 # mean(100*600/1900/6, 100*4200/6500, 100, 100)
    assert r['metrics']['monthly_surplus']==1900
    empty=assess(profile())
    assert empty['score'] is None and empty['completeness']['available_components']==0
    assert empty['metrics']['credit_utilization'] is None
    with pytest.raises(ValueError,match='Essential cash budget'):
        assess(profile(),facts().model_copy(update={'essential_cash_expenses':D('100')}))
    with pytest.raises(ValueError,match='exceed'):assess(profile(),facts().model_copy(update={'accessible_emergency_savings':D('10000')}))


def test_monotonicity_and_boundedness_properties():
    rng=np.random.default_rng(42)
    for _ in range(200):
        income=D(str(round(rng.uniform(500,15000),2)));essential=D(str(round(rng.uniform(1700,5000),2)))
        f=facts().model_copy(update={'take_home_income':income,'essential_cash_expenses':essential})
        base=assess(profile(),f)
        assert 0<=base['score']<=100
        debt=assess(profile(),f.model_copy(update={'required_debt_payments':D('500')}))
        assert debt['components'][2]['score']<=base['components'][2]['score']
        costs=assess(profile(),f.model_copy(update={'essential_cash_expenses':essential*D('1.2')}))
        assert costs['metrics']['emergency_months']<=base['metrics']['emergency_months']
        savings=replace(profile(),accounts=[replace(a,balance=a.balance+D('100')) if a.account_type=='savings' else a for a in profile().accounts])
        raised=assess(savings,f.model_copy(update={'accessible_emergency_savings':D('700')}))
        assert raised['metrics']['emergency_months']>=base['metrics']['emergency_months']
        nearby=assess(profile(),f.model_copy(update={'take_home_income':income+D('.01')}))
        assert abs(nearby['score']-base['score'])<=.02
        assert json.dumps(base,allow_nan=False)


def test_transfer_and_principal_payment_conserve_net_worth():
    from app.calc.models import Account
    p=profile();saved=deepcopy(p)
    r=simulate_economic(p,facts(),EconomicScenario(type='savings_transfer',amount=100))
    assert r['net_worth_change']==0 and r['ending_checking_change']==-100
    debt=replace(p,accounts=p.accounts+[Account('loan','stress','Loan','loan',D('500'))])
    r=simulate_economic(debt,facts(),EconomicScenario(type='debt_repayment',amount=100,liability_account_id='loan'))
    assert r['net_worth_change']==0 and r['ending_checking_change']==-100
    assert p==saved


def test_shocks_reconcile_and_one_paycheck_is_not_a_month():
    p=profile();f=facts();saved=deepcopy(p)
    r=simulate_economic(p,f,EconomicScenario(type='emergency_expense',amount=1000))
    assert r['ending_checking_change']==-1000
    r=simulate_economic(p,f,EconomicScenario(type='missed_paycheck'))
    assert r['ending_checking_change']==-2100
    r=simulate_economic(p,f,EconomicScenario(type='income_interruption'))
    assert r['ending_checking_change']==-4200
    r=simulate_economic(p,f,EconomicScenario(type='income_reduction',fraction=D('.2')))
    assert r['ending_checking_change']==-840
    r=simulate_economic(p,f,EconomicScenario(type='essential_cost_increase',fraction=D('.1')))
    assert r['ending_checking_change']==-190 # 170 fixed + 20 variable, not rent twice
    r=simulate_economic(p,f,EconomicScenario(type='cash_expense_increase',fraction=D('.1')))
    assert r['ending_checking_change']==-230 # (1900 essential + 400 discretionary) * 10%
    assert p==saved
    with pytest.raises(ValueError,match='Variable-rate'):
        simulate_economic(p,f,EconomicScenario(type='variable_rate_payment',amount=100))


def test_scenarios_require_explicit_user_assumptions():
    for kind in ('income_reduction','cash_expense_increase','emergency_expense','delayed_paycheck'):
        with pytest.raises(ValueError,match='explicit'):
            EconomicScenario(type=kind)


def test_economy_cannot_rewrite_health_or_mark_down_checking():
    p=profile();f=facts();base=assess(p,f)
    unknown=classify({'series':{}},str(p.as_of))
    first=resilience(p,f,unknown)
    other=deepcopy(unknown);other['features']['PCEPI_yoy_pct']=10;other['features']['policy_rate_change_3m_pp']=5
    other['dimensions']=[{'name':'market','flagged':True}]
    second=resilience(p,f,other)
    assert first['baseline_health']==second['baseline_health']==base
    assert second['baseline_health']['metrics']['checking']==2400


def test_sahm_previous_twelve_month_window_and_missing_months():
    u=pd.Series([4.]*14+[4.3,4.6,4.9],index=pd.date_range('2025-01-01',periods=17,freq='MS'))
    assert sahm(u).iloc[-1]==pytest.approx(.6)
    falling=pd.Series([4.]*14+[3.7,3.4,3.1],index=u.index)
    assert sahm(falling).iloc[-1]<0 # previous-window minimum excludes current average
    u.iloc[-5]=np.nan
    assert pd.isna(sahm(u).iloc[-1])


def test_no_future_or_unverified_release_information_and_staleness():
    dates=pd.date_range('2025-01-01',periods=18,freq='MS')
    future=series('PCEPI',np.arange(18)+100,dates,knowledge='2026-12-01')
    r=classify({'series':{'PCEPI':future}},'2026-11-07',historical=True)
    assert r['features'].get('PCEPI_yoy_pct') is None and r['excluded']
    current=series('PCEPI',np.arange(18)+100,dates,knowledge='2026-11-07',pit=False)
    assert classify({'series':{'PCEPI':current}},'2026-11-07',historical=True)['indicators']==[]
    stale=series('UNRATE',[4],[date(2020,1,1)])
    r=classify({'series':{'UNRATE':stale}},'2026-11-07')
    assert r['indicators'][0]['stale'] and r['status']=='Insufficient Data'
    assert r['features']['policy_rate_pct'] is None
    future_release=series('UNRATE',[4],[date(2026,10,1)])
    future_release['initial_release_date']='2026-12-01'
    assert not classify({'series':{'UNRATE':future_release}},'2026-11-07')['indicators']


def test_fred_retry_redaction_and_vintage_request():
    calls=[];sleeps=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(429,headers={'Retry-After':'1'}) if len(calls)==1 else httpx.Response(200,json={'ok':True})
    client=FredClient('fake-private-key',httpx.Client(transport=httpx.MockTransport(handler)),sleep=sleeps.append)
    assert client.get('series',{'realtime_end':'2008-10-31'})=={'ok':True}
    assert sleeps==[1] and calls[-1].url.params['realtime_end']=='2008-10-31'
    bad=FredClient('fake-private-key',httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(403))),sleep=lambda _:None)
    with pytest.raises(ValueError) as exc:bad.get('series',{})
    assert 'fake-private-key' not in str(exc.value)


def test_weighted_score_is_deterministic_and_missing_is_not_zero():
    p=profile();f=facts();r=assess(p,f)
    assert r==assess(p,f)
    missing=f.model_copy(update={'debt_complete':False})
    assert assess(p,missing)['score'] is None
    confirmed=f.model_copy(update={'required_debt_payments':D(0)})
    assert assess(p,confirmed)['components'][2]['score']==100
    undated=f.model_copy(update={'required_debt_payments':D('100')})
    withheld=assess(p,undated)
    assert withheld['score'] is None and withheld['components'][3]['score'] is None
