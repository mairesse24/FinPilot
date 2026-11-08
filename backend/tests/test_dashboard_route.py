from datetime import timedelta

from fastapi.testclient import TestClient

from app.calc import metrics as m
from tests.conftest import EMPTY_UID
from tests.factories import make_profile
from tests.test_demo_scenario import demo_client
from datetime import date


def test_dashboard_totals_match_metrics(client):
    p = make_profile()
    d = client.get("/api/dashboard").json()
    assert d["net_worth"] == float(m.net_worth(p))
    assert d["assets"] == float(m.assets(p)) and d["liabilities"] == float(m.liabilities(p))
    assert d["income_30d"] == float(m.window_inflow(p, 30))
    assert d["spending_30d"] == float(m.window_outflow(p, 30))
    amounts = [c["amount"] for c in d["by_category"]]
    assert amounts == sorted(amounts, reverse=True)


def test_upcoming_bills_within_14_days_sorted(client):
    p = make_profile()
    bills = client.get("/api/dashboard").json()["upcoming_bills"]
    dates = [b["due_date"] for b in bills]
    assert dates == sorted(dates) and bills
    assert all(date.fromisoformat(x) <= p.as_of + timedelta(days=14) for x in dates)


def test_dashboard_includes_alerts_and_health(client):
    d = client.get("/api/dashboard").json()
    assert 0 <= d["health_score"] <= 100
    assert isinstance(d["active_alerts"], list) and d["meta"]["is_prototype_estimate"]


def test_dashboard_empty_user_is_zero_safe(client):
    r = client.get("/api/dashboard", params={"user_id": EMPTY_UID})
    assert r.status_code == 200
    d = r.json()
    assert d["net_worth"] == 0 and d["income_30d"] == 0 and d["spending_30d"] == 0
    assert d["by_category"] == [] and d["upcoming_bills"] == []


def test_dashboard_unknown_user_404(client):
    assert client.get("/api/dashboard", params={"user_id": "nope"}).status_code == 404


def test_dashboard_for_demo_customer_shows_net_worth_and_alert():
    d = demo_client(date(2026, 11, 7)).get("/api/dashboard").json()
    assert d["net_worth"] != 0
    assert any(a["rule"] == "low_projected_balance" for a in d["active_alerts"])
