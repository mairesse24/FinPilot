from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
from datetime import timedelta
import numpy as np
import pandas as pd
import pytest
from scripts.ml_stress import profile,AS_OF
from app.calc.models import Account,Bill,Transaction
from app.calc import metrics as m
from app.baseline.forecast import forecast
from backend.intelligence.ledger_projection import ledger_assumptions
from backend.intelligence.forecasting import project_cash
from backend.intelligence.backend_adapter import guardian_profile
from backend.intelligence.intervals import positive_upper


def test_linked_debts_count_distinct_obligations_without_duplicate_minima():
    p=replace(profile(),accounts=profile().accounts+[
        Account('card','stress','Card','credit_card',D('500'),min_payment=D('35')),
        Account('loan','stress','Loan','loan',D('1000'),min_payment=D('100'))],
        bills=[Bill('b','stress','Card due',D('35'),'debt_payment','monthly',AS_OF+timedelta(days=1),'card')])
    assert m.monthly_debt_payments(p)==135
    with pytest.raises(ValueError,match='liability'):
        m.monthly_debt_payments(replace(p,bills=[replace(p.bills[0],liability_account_id='foreign')]))


def test_card_consumption_once_dashboard_but_only_repayment_hits_checking():
    tx=[Transaction('purchase','card',D('-100'),'groceries',AS_OF),
        Transaction('payment','checking',D('-100'),'debt_payment',AS_OF),
        Transaction('receipt','card',D('100'),'debt_payment',AS_OF)]
    p=replace(profile(),accounts=profile().accounts+[Account('card','stress','Card','credit_card',D('100'))],transactions=tx)
    assert m.window_outflow(p,30)==100
    assert m.window_inflow(p,30)==0
    assert m.checking_variable_transactions(p)==[]


def test_cold_start_does_not_zero_pad_and_exposes_uncertainty():
    p=replace(profile(),transactions=profile().transactions[:2])
    f=forecast(p,30)
    assert sum(r.predicted_spend for r in f.series)==600
    assert f.status=='limited_history' and f.meta.warning
    assert any(a.rule=='forecast_uncertain' for a in guardian_profile(p,f))
    assert f.series[-1].high-f.series[-1].low>=1800
    empty=forecast(replace(p,transactions=[]),30)
    assert empty.status=='abstained' and empty.series==[] and empty.projected_low is None


def test_ledger_assumptions_are_unchanged_by_future_rows():
    rows=[]
    for month in (1,2,3):
        for day,amount in ((1,1000),(15,1500)):
            rows.append(dict(posted_date=pd.Timestamp(2026,month,day),account_type='checking',flow_class='income',category='payroll',balance_change=amount,amount=amount))
    frame=pd.DataFrame(rows)
    expected=ledger_assumptions(frame,'2026-03-31')
    assert expected['monthly_income']==2500
    future=pd.DataFrame([{**rows[0],'posted_date':pd.Timestamp('2026-04-01'),'amount':999999,'balance_change':999999}])
    assert ledger_assumptions(pd.concat([frame,future]),'2026-03-31')==expected


def test_explicit_cash_movement_is_not_income_and_card_consumption_not_cash_twice():
    c={'customer_id':'x','as_of':'2026-01-31','checking_balance':1000.,'savings_balance':0.,'monthly_income':0.,
       'monthly_variable_spending':100.,'monthly_debt_payments':0.,'safety_buffer':500.,'paydays':[1],
       'income_schedule':[],'cash_variable_fraction':.5,
       'bills':[{'name':'card payment','amount':100.,'day':1}],
       'cash_movement_schedule':[{'day':1,'amount':-50.}]}
    path={'daily':[{'date':'2026-02-01','spending':100.,'lower':80.,'upper':120.}]}
    original=deepcopy(c)
    result=project_cash(c,path)['daily'][0]
    assert result['balance']==800 # 1000 - 50 checking consumption - 100 repayment - 50 transfer
    assert result['income']==0 and result['cash_movement']==-50
    assert c==original


def test_empirical_band_is_nonnegative_and_brackets_point():
    assert positive_upper(10,20,-100,100)==20
    assert positive_upper(10,20,1,100)==110


def test_abstention_does_not_hide_existing_observed_low_balance():
    from app.baseline.guardian import evaluate
    p=replace(profile(),transactions=[],accounts=[replace(profile().accounts[0],balance=D('-50'))])
    f=forecast(p,30)
    assert f.status=='abstained'
    assert any(a.rule=='current_low_balance' for a in evaluate(p,f))


def test_residual_calibration_does_not_extrapolate_beyond_validated_horizon(tmp_path,monkeypatch):
    import backend.intelligence.intervals as intervals
    from backend.intelligence.forecasting import forecast_spending
    h=pd.DataFrame({'customer_id':'h','date':pd.date_range('2026-01-01',periods=120),'spending':np.tile([0.,10.],60)})
    raw=forecast_spending(h,40,model_dir=tmp_path,use_calibration=False)
    monkeypatch.setattr(intervals,'policy_for',lambda *args:(1.,10.,'frequent'))
    adjusted=forecast_spending(h,40,model_dir=tmp_path)
    assert adjusted['daily'][0]['upper']>raw['daily'][0]['upper']
    assert adjusted['daily'][30:]==raw['daily'][30:]
    assert any('day 30' in w for w in adjusted['warnings'])


def test_missing_intelligence_package_preserves_cold_start_warning():
    from app.services.forecast import get_forecast
    from app.services.gateway import Gateway
    p=replace(profile(),transactions=profile().transactions[:2])
    f=get_forecast(p,Gateway('auto',package='absent_reliability_module'),30)
    assert f.status=='limited_history' and f.meta.warning
