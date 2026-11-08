from app.schemas.health import HealthResult


def test_health_endpoint_matches_schema_and_has_meta(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    res = HealthResult.model_validate(r.json())
    assert res.meta.source == "baseline"
    assert len(res.components) == 5


def test_health_unknown_user_404(client):
    assert client.get("/api/health", params={"user_id": "nope"}).status_code == 404
