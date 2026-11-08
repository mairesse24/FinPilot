def test_forecast_days_must_be_7_30_or_90(client):
    assert client.get("/api/forecast?days=45").status_code == 422
    assert client.get("/api/forecast?days=7").status_code == 200


def test_forecast_default_is_30(client):
    assert client.get("/api/forecast").json()["days"] == 30


def test_forecast_response_has_meta_and_assumptions(client):
    b = client.get("/api/forecast").json()
    assert b["meta"]["source"] == "baseline" and len(b["assumptions"]) == 3
    assert len(b["series"]) == 30
