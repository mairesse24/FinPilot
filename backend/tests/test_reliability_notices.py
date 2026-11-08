from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from app.schemas.common import Meta
from app.services.notices import notices_for, merge_notices


SHIFT='Spending occurs much more frequently than in training data; using an unvalidated rolling-average fallback instead of the synthetic-calendar model.'


def test_duplicate_warnings_have_stable_codes_and_context():
    a=notices_for([SHIFT,SHIFT], 'forecast')
    b=notices_for([SHIFT], 'forecast')
    combined=merge_notices(a,b)
    assert len(combined)==1
    assert combined[0].code=='forecast_pattern_shift'
    assert combined[0].category=='data_limitation'
    assert 'LightGBM' not in combined[0].message
    assert SHIFT in combined[0].technical_detail
    assert len(merge_notices(a,notices_for([SHIFT],'another-customer')))==2


def test_missing_loan_and_deposits_are_not_silenced():
    notices=notices_for(['An approved loan has no confirmed outstanding balance and is omitted from net worth; supply loan_balances in the schedule file.',
                         'Checking deposits are shown as inflows, not verified salary.'], 'bank_data')
    assert {n.code for n in notices}=={'loan_balance_missing','deposits_unverified'}
    assert next(n for n in notices if n.code=='loan_balance_missing').category=='critical'


def test_reliability_reaches_dashboard_guardian_simulation_and_tools(client):
    forecast=client.get('/api/forecast?days=30').json()
    assert forecast['meta']['forecast_reliability']['validation']=='unvalidated'
    assert client.get('/api/dashboard').json()['meta']['forecast_reliability']==forecast['meta']['forecast_reliability']
    assert client.get('/api/guardian').json()['meta']['forecast_reliability']==forecast['meta']['forecast_reliability']
    sim=client.post('/api/simulate',json={'scenario':{'reduction_amount':100}}).json()
    assert sim['baseline']['forecast_reliability']['validation']=='unvalidated'
    assert sim['meta']['forecast_reliability']['validation']=='unvalidated'
    assert client.get('/api/health').json()['meta']['forecast_reliability'] is None
    assert client.get('/api/financial-health').json()['forecast_dependency'].startswith('none')
    from app.tools.registry import ToolRegistry
    from app.services.gateway import Gateway
    from tests.factories import make_profile
    tool=ToolRegistry(make_profile(),Gateway('baseline'))
    assert tool.call('get_forecast',{'days':30})['meta']['forecast_reliability']['validation']=='unvalidated'


def test_abstained_simulation_does_not_invent_zero_ending_balance():
    from tests.factories import make_profile
    profile=make_profile()
    from app.baseline.simulate import simulate
    from app.schemas.common import SpendingCut
    r=simulate(replace(profile,transactions=[]),SpendingCut(reduction_amount=Decimal(100)))
    assert r.baseline.end_balance is None and r.scenario.end_balance is None
    assert r.delta['end_balance_change'] is None


def test_short_history_does_not_call_calendar_model():
    from tests.factories import make_profile
    profile=make_profile()
    from intelligence.backend_adapter import forecast_profile
    txs=[replace(t,date=profile.as_of-timedelta(days=10)) for t in profile.transactions[:1]]
    r=forecast_profile(replace(profile,transactions=txs),7)
    assert r.meta.forecast_reliability.method!='lightgbm'
    assert r.meta.forecast_reliability.validation=='unvalidated'


def test_no_store_for_financial_endpoints(client):
    for path in ('/api/context','/api/dashboard','/api/forecast?days=7'):
        assert 'no-store' in client.get(path).headers['cache-control']


def test_normal_supported_history_keeps_calendar_model_and_shift_uses_baseline():
    from backend.intelligence.data import load_daily
    from backend.intelligence.forecasting import forecast_spending
    history=load_daily().query("customer_id == 'C001'").iloc[:125].copy()
    normal=forecast_spending(history,7)
    assert normal['model']=='lightgbm'
    assert not normal['support_check']['outside_training_frequency']
    history['spending']=20.
    shifted=forecast_spending(history,7)
    assert shifted['model']=='moving_average_28'
    assert shifted['support_check']['outside_training_frequency']
    assert sum(r['spending'] for r in shifted['daily'])==140


def test_database_substitution_is_critical_and_not_hidden_as_diagnostics():
    n=notices_for(['Configured PostgreSQL unavailable; generated demo records are being served.'],'bank_data')
    assert n[0].code=='data_source_substituted' and n[0].category=='critical'
