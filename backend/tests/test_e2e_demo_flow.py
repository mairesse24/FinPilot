from datetime import date

from app.schemas.chat import ChatResult
from app.schemas.dashboard import DashboardResult
from app.schemas.forecast import ForecastResult
from app.schemas.guardian import GuardianResult
from app.schemas.health import HealthResult
from app.schemas.simulate import SimulationResult
from tests.test_demo_scenario import demo_client


def test_full_demo_flow_over_http():
    c = demo_client(date(2026, 11, 7))
    DashboardResult.model_validate(c.get("/api/dashboard").json())
    HealthResult.model_validate(c.get("/api/health").json())
    ForecastResult.model_validate(c.get("/api/forecast", params={"days": 30}).json())
    g = c.get("/api/guardian")
    assert g.status_code == 200
    alert = next(a for a in GuardianResult.model_validate(g.json()).alerts
                 if a.suggested_scenario)
    sc = alert.suggested_scenario.model_dump(mode="json") | {"reduction_amount": 200}
    r = c.post("/api/simulate", json={"scenario": sc})
    assert r.status_code == 200
    sim = SimulationResult.model_validate(r.json())
    assert sim.scenario.projected_low.balance > sim.baseline.projected_low.balance
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "what can I do?"}]})
    assert r.status_code == 200
    ChatResult.model_validate(r.json())


def test_openapi_lists_every_mvp_route(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in ["/api/dashboard", "/api/accounts", "/api/transactions", "/api/health",
              "/api/forecast", "/api/guardian", "/api/simulate", "/api/chat", "/healthz"]:
        assert p in paths
