import pytest


@pytest.mark.parametrize("scenario", [
    {"type": "spending_cut", "reduction_amount": 0},
    {"type": "spending_cut", "reduction_amount": -5},
    {"type": "spending_cut", "reduction_amount": 100, "horizon_days": 0},
    {"type": "spending_cut", "reduction_amount": 100, "horizon_days": 91},
    {"type": "bogus", "reduction_amount": 100},
])
def test_simulate_rejects_bad_scenarios(client, scenario):
    assert client.post("/api/simulate", json={"scenario": scenario}).status_code == 422


def test_simulate_response_matches_schema(client):
    r = client.post("/api/simulate", json={"scenario": {"type": "spending_cut",
                                                         "reduction_amount": 100,
                                                         "horizon_days": 14}})
    assert r.status_code == 200
    b = r.json()
    assert set(b["delta"]) == {"low_balance_change", "end_balance_change", "health_score_change"}
    assert b["meta"]["source"] == "baseline" and b["scenario"]["series"]
