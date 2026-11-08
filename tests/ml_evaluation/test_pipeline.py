"""Independent financial expectations and leakage checks; known gaps stay visible."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal as D

import numpy as np
import pandas as pd
import pytest

from scripts.ml_stress import profile,run,AS_OF
from app.calc.models import Account,Bill,Transaction
from app.calc.projection import project_balance
from app.calc import metrics as m
from backend.intelligence.features import make_features,FEATURES
from backend.intelligence.forecasting import forecast_spending
from backend.intelligence.backend_adapter import _history


def test_future_and_current_target_cannot_change_earlier_features():
    dates=pd.date_range('2025-01-01',periods=150)
    daily=pd.DataFrame({'customer_id':'test','date':dates,'spending':np.arange(150,dtype=float)})
    original=make_features(daily)
    changed=daily.copy();changed.loc[changed.date>=dates[100],'spending']=999999
    result=make_features(changed)
    pd.testing.assert_frame_equal(original.loc[original.date<=dates[100],FEATURES].reset_index(drop=True),result.loc[result.date<=dates[100],FEATURES].reset_index(drop=True))


def test_customer_histories_do_not_mix():
    dates=pd.date_range('2025-01-01',periods=60)
    a=pd.DataFrame({'customer_id':'a','date':dates,'spending':10.})
    b=pd.DataFrame({'customer_id':'b','date':dates,'spending':1000.})
    f=make_features(pd.concat([a,b],ignore_index=True))
    assert (f[f.customer_id=='a'].mean_7==10).all()
    assert (f[f.customer_id=='b'].mean_7==1000).all()


def test_exact_cash_reconciliation_and_known_bill_once():
    p=profile()
    # 30 days: $2400 + two $2100 pays - $1500 rent - $200 utilities - $600 variable.
    rows=project_balance(p,30,lambda _:D('20'))
    assert rows[-1].balance==D('4300')
    assert rows[3].balance==D('820') # day 4: 2400 - 80 - 1500
    no_future_spend=project_balance(p,30,lambda _:D('0'))
    assert no_future_spend[-1].balance==D('4900')


def test_income_shock_and_emergency_exact_direction():
    p=profile();saved=deepcopy(p)
    base=project_balance(p,30,lambda _:D('20'))
    shock=replace(p,income_sources=[replace(s,amount=s.amount*D('.7')) for s in p.income_sources])
    assert project_balance(shock,30,lambda _:D('20'))[-1].balance==base[-1].balance-D('1260')
    emergency=replace(p,accounts=[replace(a,balance=a.balance-D('1500')) if a.account_type=='checking' else a for a in p.accounts])
    assert project_balance(emergency,30,lambda _:D('20'))[-1].balance==base[-1].balance-D('1500')
    assert p==saved


def test_history_excludes_fixed_bills_transfers_and_positive_refunds():
    p=profile()
    extras=[Transaction('rent','checking',D('-1500'),'rent',AS_OF),Transaction('transfer','checking',D('-1000'),'transfer',AS_OF),Transaction('refund','checking',D('100'),'refund',AS_OF)]
    assert _history(replace(p,transactions=p.transactions+extras)).spending.sum()==2400


def test_dashboard_internal_transfer_not_spending():
    p=replace(profile(),transactions=[Transaction('transfer','checking',D('-300'),'transfer',AS_OF)])
    assert m.window_outflow(p,30)==D('0')


def test_generic_card_purchase_does_not_also_reduce_checking():
    p=replace(profile(),accounts=profile().accounts+[Account('card','stress','Card','credit_card',D('100'))],
        transactions=[Transaction('purchase','card',D('-100'),'groceries',AS_OF)])
    assert _history(p).spending.sum()==0


def test_matching_card_minimum_and_scheduled_payment_count_once():
    p=replace(profile(),accounts=profile().accounts+[Account('card','stress','Card','credit_card',D('500'),min_payment=D('35'))],
              bills=[Bill('cardbill','stress','Card payment',D('35'),'debt_payment','monthly',AS_OF+timedelta(days=2))])
    assert m.monthly_debt_payments(p)==D('35')


def test_short_history_rejected_instead_of_mislabeled_as_ml():
    h=pd.DataFrame({'customer_id':'x','date':pd.date_range('2026-01-01',periods=3),'spending':0.})
    with pytest.raises(ValueError,match='29'):forecast_spending(h,7)


def test_baseline_rounds_daily_cents_before_cash_accumulation():
    from app.baseline.forecast import forecast
    f=forecast(replace(profile(),bills=[],income_sources=[]),2,lambda _:D('.006'))
    assert [r.predicted_spend for r in f.series]==[D('.01'),D('.01')]
    assert f.series[-1].projected_balance==D('2399.98')


def test_identical_inputs_produce_identical_projection():
    from app.baseline.forecast import forecast
    p=profile();saved=deepcopy(p)
    assert forecast(p,30).series==forecast(p,30).series
    assert p==saved


def test_controlled_stress_has_no_crashes_and_exact_shock_amounts():
    results=run();r={x['case']:x for x in results}
    assert all(not x['crashed'] for x in results)
    assert all(x['invariants_pass'] for x in results)
    assert r['B_emergency_1500']['ending_change']==-1500
    assert r['A_income_minus_30pct']['ending_change']==-1260
    assert r['D_discretionary_surge_week']['ending_change']==-700
    assert r['E_delayed_paycheck']['ending_change']==-4200
