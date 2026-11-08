from copy import deepcopy
import json
from types import SimpleNamespace
import pandas as pd
import pytest
from backend.intelligence.features import make_features, FEATURES
from backend.intelligence.forecasting import forecast_spending
from backend.intelligence.service import analyze_with_spending
from backend.intelligence.simulator import simulate
from backend.intelligence.copilot import chat
from backend.intelligence.economic_pressure import economic_pressure


@pytest.fixture
def customer():
    return {'customer_id': 'test', 'as_of': '2026-10-31', 'checking_balance': 2400.,
            'savings_balance': 100., 'monthly_income': 3000., 'monthly_variable_spending': 900.,
            'monthly_debt_payments': 1200., 'bills': [{'name': 'rent', 'amount': 2000., 'day': 3}],
            'paydays': [15, 28], 'safety_buffer': 500., 'budget': 800.}


@pytest.fixture
def spending():
    return {'model': 'fixture', 'days': 30, 'daily': [
        {'date': d.date().isoformat(), 'spending': 30., 'lower': 20., 'upper': 40.}
        for d in pd.date_range('2026-11-01', periods=30)]}


def test_cash_dates_and_bounds(customer, spending):
    result = analyze_with_spending(customer, spending)
    fc = result['forecast']
    assert fc['daily'][2]['balance'] == 310.
    assert fc['daily'][14]['income'] == 1500.
    assert fc['ending_balance'] == 2500.
    assert all(r['balance_lower'] <= r['balance'] <= r['balance_upper'] for r in fc['daily'])
    assert {'low_balance', 'emergency_savings', 'debt_burden'} <= {a['id'] for a in result['guardian']}
    assert 0 <= result['health']['score'] <= 100
    json.dumps(result, allow_nan=False)


def test_simulation_saves_200_without_mutation(customer, spending):
    before = deepcopy((customer, spending))
    result = simulate(customer, spending, {'monthly_spending_cut': 200})
    assert result['ending_balance_change'] == pytest.approx(200, abs=.11)
    assert (customer, spending) == before
    emergency = simulate(customer, spending, {'emergency_expense': 700})
    assert emergency['ending_balance_change'] == -700


def test_transfer_preserves_liquid_money(customer, spending):
    result = simulate(customer, spending, {'monthly_savings_transfer': 100})
    assert result['ending_balance_change'] == -100
    assert result['savings_path'][-1]['savings_balance'] == 200
    assert result['after']['health'] == result['before']['health']


@pytest.mark.parametrize('scenario', [{'income_reduction_pct': 1.2}, {'emergency_expense': -1},
                                      {'monthly_spending_cut': float('nan')}, {'unknown': 2}])
def test_bad_scenarios(customer, spending, scenario):
    with pytest.raises(ValueError):
        simulate(customer, spending, scenario)


def test_feature_no_target_leakage():
    daily = pd.DataFrame({'date': pd.date_range('2026-01-01', periods=60),
                          'customer_id': 'test', 'spending': list(range(60))})
    original = make_features(daily)
    daily.loc[59, 'spending'] = 1000000
    changed = make_features(daily)
    assert original[FEATURES].equals(changed[FEATURES])


def test_bad_history(tmp_path):
    history = pd.DataFrame({'date': pd.date_range('2026-01-01', periods=60),
                            'customer_id': 'x', 'spending': 1.})
    forecast = forecast_spending(history, 7, tmp_path)
    assert len(forecast['daily']) == 7
    assert forecast['daily'][0]['spending'] == 1
    with pytest.raises(ValueError):
        forecast_spending(history.iloc[::2], 7, tmp_path)


def test_missing_budget_and_zero_income(customer, spending):
    customer['monthly_income'], customer['budget'] = 0., None
    result = analyze_with_spending(customer, spending)
    assert result['health']['observed_weight'] == .40
    json.dumps(result, allow_nan=False)


def test_economy_no_fake_live_data(customer):
    assert economic_pressure(customer)['available'] is False
    result = economic_pressure(customer, {'as_of': '2026-10-31', 'inflation_yoy_pct': 4.,
                                         'policy_rate_pct': 4., 'unemployment_pct': 5., 'source': 'test fixture'})
    assert result['index'] == 50


def test_reject_dates(customer, spending):
    spending['daily'][0]['date'] = '2026-10-31'
    with pytest.raises(ValueError):
        analyze_with_spending(customer, spending)


def test_month_end_schedule(customer):
    customer['as_of'] = '2027-02-27'
    customer['bills'] = [{'name': 'month end', 'amount': 50., 'day': 31}]
    customer['paydays'] = [30, 31]
    path = {'daily': [{'date': '2027-02-28', 'spending': 0., 'lower': 0., 'upper': 0.}]}
    result = analyze_with_spending(customer, path)['forecast']['daily'][0]
    assert result['bills'] == 50
    assert result['income'] == 3000


def test_customer_scope(customer):
    from backend.intelligence.service import analyze
    history = pd.DataFrame({'date': pd.date_range('2026-10-01', periods=31),
                            'customer_id': 'someone-else', 'spending': 0.})
    with pytest.raises(ValueError, match='belong'):
        analyze(customer, history)


def test_copilot_tool_loop(customer, spending):
    analysis = analyze_with_spending(customer, spending)
    call = SimpleNamespace(type='function_call', name='get_analysis', arguments='{}', call_id='a')
    responses = iter([SimpleNamespace(output=[call]),
                      SimpleNamespace(output=[], output_text='Your ending balance is $2,500.00. [get_analysis]')])
    class FakeResponses:
        def create(self, **kwargs):
            assert kwargs['store'] is False
            return next(responses)
    result = chat('My risks?', customer, spending, analysis,
                  client=SimpleNamespace(responses=FakeResponses()), model='test-model')
    assert result['mode'] == 'openai'


def test_copilot_rejects_invented_numbers(customer, spending):
    analysis = analyze_with_spending(customer, spending)
    call = SimpleNamespace(type='function_call', name='get_analysis', arguments='{}', call_id='a')
    replies = iter([SimpleNamespace(output=[call]), SimpleNamespace(output=[], output_text='You will have $99999999.')])
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kw: next(replies)))
    assert chat('?', customer, spending, analysis, client=client, model='test')['mode'] == 'validated_fallback'


def test_gemini_personalized_dashboard(customer, spending):
    pytest.importorskip('google.genai')
    from google.genai import types
    analysis = analyze_with_spending(customer, spending)
    content = types.Content(role='model', parts=[types.Part.from_function_call(name='get_dashboard', args={})])
    answer = types.Content(role='model', parts=[types.Part.from_text(text='Your checking balance is $2,400.00. [get_dashboard]')])
    replies = iter([types.GenerateContentResponse(candidates=[types.Candidate(content=content)]),
                    types.GenerateContentResponse(candidates=[types.Candidate(content=answer)])])
    def generate(**kwargs):
        assert kwargs['config'].automatic_function_calling.disable
        return next(replies)
    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    result = chat('What is my balance?', customer, spending, analysis, client=client, model='test', provider='gemini')
    assert result['mode'] == 'gemini'
    assert result['tool_results'][0]['result']['customer']['checking_balance'] == 2400.


def test_gemini_simulation_tool(customer, spending):
    pytest.importorskip('google.genai')
    from google.genai import types
    analysis = analyze_with_spending(customer, spending)
    call = types.Content(role='model', parts=[types.Part.from_function_call(name='simulate', args={'monthly_spending_cut': 200})])
    answer = types.Content(role='model', parts=[types.Part.from_text(text='The spending-cut simulation improves your projected ending balance. [simulate]')])
    replies = iter([types.GenerateContentResponse(candidates=[types.Candidate(content=call)]),
                    types.GenerateContentResponse(candidates=[types.Candidate(content=answer)])])
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: next(replies)))
    result = chat('What if I cut spending?', customer, spending, analysis, client=client, model='test', provider='gemini')
    assert result['mode'] == 'gemini'
    assert result['tool_results'][0]['result']['ending_balance_change'] == pytest.approx(200, abs=.11)


def test_gemini_missing_config(customer, spending, monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_MODEL', raising=False)
    with pytest.raises(ValueError, match='Gemini requires'):
        chat('Hello', customer, spending, analyze_with_spending(customer, spending), provider='gemini')


def test_explicit_offline_never_needs_key(customer, spending):
    result = chat('My risks?', customer, spending, analyze_with_spending(customer, spending), provider='offline')
    assert result['mode'] == 'offline'


def test_chat_cli_timeout_is_actionable(monkeypatch, capsys):
    import httpx
    from scripts import run
    monkeypatch.setattr('sys.argv', ['run', 'chat', '--provider', 'gemini'])
    monkeypatch.setattr(run, 'load_customer', lambda _: {'customer_id': 'C002'})
    monkeypatch.setattr(run, 'load_daily', lambda: pd.DataFrame({'customer_id': ['C002']}))
    monkeypatch.setattr(run, 'analyze', lambda *a: {'forecast': {}})
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout('Secret-bearing raw exception should not be printed')
    monkeypatch.setattr(run, 'chat', timeout)
    with pytest.raises(SystemExit) as error:
        run.main()
    assert error.value.code == 1
    output = capsys.readouterr().err
    assert 'timed out' in output
    assert 'Secret-bearing' not in output


def test_chat_cli_service_failure_is_actionable(monkeypatch, capsys):
    from google.genai.errors import ServerError
    from scripts import run
    monkeypatch.setattr('sys.argv', ['run', 'chat', '--provider', 'gemini'])
    monkeypatch.setattr(run, 'load_customer', lambda _: {'customer_id': 'C002'})
    monkeypatch.setattr(run, 'load_daily', lambda: pd.DataFrame({'customer_id': ['C002']}))
    monkeypatch.setattr(run, 'analyze', lambda *a: {'forecast': {}})
    def fail(*args, **kwargs):
        raise ServerError(504, {'error': {'message': 'Raw provider text', 'code': 504}})
    monkeypatch.setattr(run, 'chat', fail)
    with pytest.raises(SystemExit) as error:
        run.main()
    assert error.value.code == 1
    output = capsys.readouterr().err
    assert 'HTTP 504' in output
    assert 'Retry later' in output
    assert 'Raw provider text' not in output


def test_savings_shortfall_alert_is_explicit_and_conserves_cash(customer):
    customer.update(checking_balance=100., savings_balance=500., savings_floor=450.,
                    fund_shortfalls_from_savings=True)
    path = {'daily': [{'date': '2026-11-01', 'spending': 200., 'lower': 200., 'upper': 200.}]}
    result = analyze_with_spending(customer, path)
    row = result['forecast']['daily'][0]
    assert row['balance'] == 0
    assert row['savings_balance'] == 400
    assert row['savings_withdrawal'] == 100
    assert row['combined_liquid_balance'] == 400
    alert = next(a for a in result['guardian'] if a['id'] == 'savings_below_floor')
    assert alert['evidence']['first_breach_date'] == '2026-11-01'
    customer['fund_shortfalls_from_savings'] = False
    unfunded = analyze_with_spending(customer, path)
    assert unfunded['forecast']['ending_savings'] == 500
    assert unfunded['forecast']['ending_balance'] == -100
    assert not any(a['id'] == 'savings_below_floor' for a in unfunded['guardian'])


def test_savings_cannot_fund_more_than_available(customer):
    customer.update(checking_balance=100., savings_balance=50., fund_shortfalls_from_savings=True)
    path = {'daily': [{'date': '2026-11-01', 'spending': 200., 'lower': 200., 'upper': 200.}]}
    result = analyze_with_spending(customer, path)['forecast']
    assert result['ending_savings'] == 0
    assert result['ending_balance'] == -50


def test_horizons_are_prefixes(customer, monkeypatch):
    from backend.intelligence import service
    history = pd.DataFrame({'customer_id': ['test'], 'date': [pd.Timestamp(customer['as_of'])], 'spending': [0.]})
    path = {'model': 'fixture', 'days': 90, 'daily': [
        {'date': day.date().isoformat(), 'spending': 10., 'lower': 5., 'upper': 20.}
        for day in pd.date_range('2026-11-01', periods=90)]}
    monkeypatch.setattr(service, 'forecast_spending', lambda *args: path)
    results = service.analyze_horizons(customer, history)
    assert [len(results[str(d)]['forecast']['daily']) for d in (7, 30, 90)] == [7, 30, 90]
    assert results['7']['forecast']['daily'] == results['90']['forecast']['daily'][:7]
    assert results['30']['forecast']['daily'] == results['90']['forecast']['daily'][:30]


def test_economic_features_do_not_use_future_data():
    from backend.intelligence.economic_outlook import monthly_features, FEATURES as EF
    index = pd.date_range('2015-01-31', periods=100, freq='ME')
    raw = pd.DataFrame({'CPIAUCSL': [200+i for i in range(100)], 'UNRATE': 4.,
                        'FEDFUNDS': 3., 'SP500': [2000+i*10 for i in range(100)]}, index=index)
    original = monthly_features(raw, '2022-12-31')
    raw.loc[raw.index >= '2023-01-01', :] = 999999.
    changed = monthly_features(raw, '2022-12-31')
    assert original[EF].equals(changed[EF])
    assert pd.isna(original.next_return.iloc[-1])
    assert original.inflation_lag.iloc[-1] == pytest.approx((raw.CPIAUCSL.iloc[93]/raw.CPIAUCSL.iloc[81]-1)*100)


def test_economic_research_separates_targets_and_abstains():
    import numpy as np
    from backend.intelligence.economic_outlook import research_outlook
    i = np.arange(130)
    raw = pd.DataFrame({'CPIAUCSL': 200+i*.3, 'UNRATE': 4+.1*np.sin(i),
                        'FEDFUNDS': 3+.2*np.sin(i/3), 'SP500': 1000*np.exp(.005*i+.05*np.sin(i))},
                       index=pd.date_range('2015-01-31', periods=130, freq='ME'))
    report = research_outlook(raw, '2025-10-31')
    assert set(report['household']) == {'next_inflation', 'next_unemployment'}
    assert report['market']['direction'] == 'abstain'
    assert report['market']['evaluation_months'] == 24
    assert report['point_in_time_validated'] is False
    json.dumps(report, allow_nan=False)


def test_cpi_inflation_uses_calendar_year_even_with_missing_months():
    from scripts.economy import indicator_snapshot
    raw = pd.DataFrame({'CPIAUCSL': [100., 110.], 'UNRATE': [4., 4.], 'FEDFUNDS': [3., 3.]},
                       index=pd.to_datetime(['2024-01-01', '2025-01-01']))
    snapshot = indicator_snapshot(raw, '2025-02-01')
    assert snapshot['inflation_yoy_pct'] == pytest.approx(10.)


def test_irregular_spending_uses_explicit_baseline_fallback(tmp_path):
    from backend.intelligence.features import FEATURES
    metadata = {'features': FEATURES, 'serving_model': 'lightgbm', 'training_history_profile': {
        'zero_day_fraction_min': .8, 'zero_day_fraction_max': .9, 'fallback_margin': .15}}
    (tmp_path / 'metadata.json').write_text(json.dumps(metadata))
    history = pd.DataFrame({'customer_id': 'irregular', 'date': pd.date_range('2026-01-01', periods=125), 'spending': 30.})
    result = forecast_spending(history, 7, tmp_path)
    assert result['model'] == 'moving_average_28'
    assert result['support_check']['outside_training_frequency'] is True
    assert result['warnings']
    assert sum(p['spending'] for p in result['daily']) == 210.
