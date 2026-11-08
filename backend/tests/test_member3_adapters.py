"""Integration contracts for Member 3 with the actual backend-mvp gateway."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
import pytest

from app.main import create_app
from app.services.gateway import Gateway
from app.services.forecast import get_forecast
from app.services.health import get_health
from app.services.guardian import get_guardian
from app.services.simulate import run_simulation
from app.schemas.common import SpendingCut
from tests.factories import make_profile


def test_adapters_return_real_schema_types_and_keep_profile_unchanged():
    p = make_profile()
    gateway = Gateway('auto')
    original = list(p.transactions)
    health = get_health(p, gateway)
    assert health.meta.source == 'model'
    assert sum(c.weight for c in health.components) == pytest.approx(100)
    fc = get_forecast(p, gateway, 30)
    assert len(fc.series) == 30
    assert fc.series[0].date == p.as_of+timedelta(days=1)
    assert all(point.low <= point.projected_balance <= point.high for point in fc.series)
    assert any('Member 3 variable-spending' in s for s in fc.assumptions)
    assert get_guardian(p, gateway).alerts
    simulated = run_simulation(p, gateway, SpendingCut(reduction_amount=Decimal('100'), horizon_days=30))
    assert simulated.baseline.series == fc.series
    assert simulated.scenario.end_balance >= simulated.baseline.end_balance
    assert p.transactions == original


def test_foreign_profile_account_rejected_before_model_inference():
    from intelligence.backend_adapter import _history
    p = make_profile()
    with pytest.raises(ValueError, match='owned'):
        _history(replace(p, accounts=[replace(p.accounts[0], user_id='another-user')]))


def test_gateway_preserves_warned_baseline_metadata():
    p = make_profile()
    # Frequent-spending fixture is outside PNC's calendar pattern.
    fc = get_forecast(p, Gateway('auto'), 7)
    assert fc.meta.source in ('baseline', 'model')
    assert fc.meta.warning is not None


def test_auto_routes_and_offline_registry_chat(repo, settings, monkeypatch):
    monkeypatch.setenv('COPILOT_PROVIDER', 'offline')
    client = TestClient(create_app(repo, settings.model_copy(update={'intelligence_mode': 'auto'})))
    for endpoint in ('/api/dashboard', '/api/health', '/api/forecast?days=30', '/api/guardian'):
        response = client.get(endpoint)
        assert response.status_code == 200
        assert response.json()['meta']['is_prototype_estimate']
    response = client.post('/api/simulate', json={'scenario': {'reduction_amount': 100, 'horizon_days': 30}})
    assert response.status_code == 200
    chat = client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'What is my health score?'}]})
    assert chat.status_code == 200
    assert chat.json()['meta']['source'] == 'baseline'
    assert chat.json()['tool_calls'][0]['name'] == 'get_health_score'
