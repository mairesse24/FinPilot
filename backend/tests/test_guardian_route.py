def test_guardian_returns_alerts_and_meta(client):
    b = client.get("/api/guardian").json()
    assert b["meta"]["source"] == "baseline" and isinstance(b["alerts"], list)


def test_guardian_unknown_user_404(client):
    assert client.get("/api/guardian?user_id=nope").status_code == 404
