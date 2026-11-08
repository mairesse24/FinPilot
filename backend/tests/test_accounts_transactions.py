from tests.conftest import EMPTY_UID


def test_healthz_and_default_user_accounts(client):
    assert client.get("/healthz").json() == {"status": "ok", "database": True}
    body = client.get("/api/accounts").json()
    assert len(body["accounts"]) == 4 and body["accounts"][0]["balance"] == 1000.0


def test_transactions_paginates_and_totals(client):
    body = client.get("/api/transactions?limit=2").json()
    assert len(body["items"]) == 2 and body["total"] == 61
    assert body["items"][0]["date"] >= body["items"][1]["date"]


def test_transactions_filters(client):
    body = client.get("/api/transactions?category=income&from=2026-11-01&to=2026-11-07").json()
    assert body["total"] == 1


def test_unknown_user_404(client):
    assert client.get("/api/accounts?user_id=nope").status_code == 404
    assert client.get("/api/transactions?user_id=nope").status_code == 404


def test_bad_limit_422(client):
    assert client.get("/api/transactions?limit=501").status_code == 422


def test_empty_profile_no_crash(client):
    assert client.get(f"/api/accounts?user_id={EMPTY_UID}").json() == {"accounts": []}
    assert client.get(f"/api/transactions?user_id={EMPTY_UID}").json() == {"items": [], "total": 0}


def test_ninety_percent_savings_demo_is_read_only_and_returns_notification(client):
    dashboard = client.get("/api/dashboard").json()
    before = sum(a["balance"] for a in dashboard["accounts"] if a["account_type"] == "savings")
    response = client.post("/api/demo/savings-stress")
    assert response.status_code == 200
    result = response.json()
    assert result["mode"] == "simulation" and result["executed"] is False
    assert result["percentage"] == 90
    assert result["savings_after"] == round(before * 0.1, 2)
    assert result["alert"]["severity"] == "high"
    after = client.get("/api/dashboard").json()
    assert sum(a["balance"] for a in after["accounts"] if a["account_type"] == "savings") == before


def test_default_app_boots_without_database_with_demo_data(settings):
    from fastapi.testclient import TestClient
    from app.data.synthetic import DEMO_USER_ID
    from app.main import create_app
    s = settings.model_copy(update={"demo_user_id": DEMO_USER_ID})
    r = TestClient(create_app(settings=s)).get("/api/accounts").json()
    assert r["accounts"][0]["balance"] == 2400.0
