"""Demo fixes: shortfall-sized low-balance scenario and DEFAULT_MONTHLY_BUDGET assumption."""
from datetime import date
from decimal import Decimal
import pytest

from intelligence.backend_adapter import _customer, _low_balance_scenario
from tests.factories import make_profile

AS_OF = date(2026, 11, 7)


def rows(low_day, low=100.0):
    return [{'date': '2026-11-08', 'balance': 900.0}, {'date': low_day, 'balance': low}, {'date': '2026-12-30', 'balance': 700.0}]


def test_worked_example_clears_buffer():
    s = _low_balance_scenario(358.50, 500, rows('2026-11-17', 358.5), AS_OF)
    assert (s.reduction_amount, s.horizon_days) == (150, 10)
    assert 358.50 + float(s.reduction_amount) >= 500


@pytest.mark.parametrize('low,buffer,expected', [(500, 500, None), (600, 500, None), (450, 500, 50), (400, 500, 100), (401, 500, 100),
                                                 (-20, 500, 550), (0, 10**6, 100000)])
def test_amount_rounding_and_bounds(low, buffer, expected):
    s = _low_balance_scenario(low, buffer, rows('2026-11-17'), AS_OF)
    assert (s.reduction_amount if s else None) == expected


def test_horizon_edges():
    assert _low_balance_scenario(100, 500, rows('2026-11-07'), AS_OF).horizon_days == 1
    assert _low_balance_scenario(100, 500, rows('2027-03-01'), AS_OF).horizon_days == 90


def test_budget_env_adds_discipline_component(monkeypatch):
    from intelligence.health_score import health_score
    p = make_profile()
    monkeypatch.delenv('DEFAULT_MONTHLY_BUDGET', raising=False)
    c = _customer(p)
    base = health_score(c)
    assert c['budget'] is None and len([x for x in base['components'] if x['score'] is not None]) == 4
    monkeypatch.setenv('DEFAULT_MONTHLY_BUDGET', '1100')
    c = _customer(p)
    h = health_score(c)
    assert c['budget'] == 1100.0 and 'DEFAULT_MONTHLY_BUDGET' in c['assumptions'][0] and '$1100' in c['assumptions'][0]
    assert len([x for x in h['components'] if x['score'] is not None]) == 5
    assert h['score'] is not None and h['observed_weight'] == pytest.approx(1.0)


@pytest.mark.parametrize('value', ['', 'abc', 'nan', 'inf', '0', '-5'])
def test_garbage_budget_ignored(monkeypatch, value):
    monkeypatch.setenv('DEFAULT_MONTHLY_BUDGET', value)
    c = _customer(make_profile())
    assert c['budget'] is None and 'assumptions' not in c


def test_demo_customer_budget_1100_discipline_and_no_budget_alert(monkeypatch):
    from app.data.synthetic import DEMO_USER_ID, build_demo_customer
    from app.db.memory import InMemoryRepository
    from intelligence.health_score import health_score
    monkeypatch.setenv('DEFAULT_MONTHLY_BUDGET', '1100')
    p = InMemoryRepository(build_demo_customer(AS_OF)).load_profile(DEMO_USER_ID, AS_OF)
    c = _customer(p)
    d = next(x for x in health_score(c)['components'] if x['name'] == 'spending_discipline')
    print('demo spend', c['monthly_variable_spending'], 'discipline', d['score'])
    assert c['monthly_variable_spending'] <= 1.2 * c['budget']
