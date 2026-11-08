from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data.synthetic import DEMO_USER_ID, build_demo_customer
from app.db.memory import InMemoryRepository
from app.main import create_app


def demo_client(as_of: date) -> TestClient:
    settings = Settings(_env_file=None, database_url=None, demo_user_id=DEMO_USER_ID,
                        intelligence_mode="baseline", as_of_date=as_of)
    return TestClient(create_app(repo=InMemoryRepository(build_demo_customer(as_of)),
                                 settings=settings))


def _alert(c):
    alerts = c.get("/api/guardian").json()["alerts"]
    return next(a for a in alerts if a["rule"] == "low_projected_balance")


@pytest.mark.parametrize("as_of", [date(2026, 11, 7), date(2026, 12, 15), date(2027, 3, 3)])
def test_demo_guardian_flags_low_balance(as_of):
    a = _alert(demo_client(as_of))
    assert a["numbers"]["current"] == 2400.00
    assert 250 <= a["numbers"]["projected_low"] <= 400 and a["numbers"]["projected_low"] < 500


@pytest.mark.parametrize("as_of", [date(2026, 11, 7), date(2026, 12, 15), date(2027, 3, 3)])
def test_demo_cut_of_200_clears_buffer(as_of):
    c = demo_client(as_of)
    sc = dict(_alert(c)["suggested_scenario"], reduction_amount=200)
    b = c.post("/api/simulate", json={"scenario": sc}).json()
    assert 500 <= b["scenario"]["projected_low"]["balance"] <= 650
    assert abs(b["delta"]["low_balance_change"] - 200) <= 1.0


def test_demo_scenario_holds_for_any_as_of():
    for as_of in (date(2026, 2, 1), date(2026, 8, 20), date(2027, 1, 28)):
        c = demo_client(as_of)
        a = _alert(c)
        assert 250 <= a["numbers"]["projected_low"] <= 400
        sc = dict(a["suggested_scenario"], reduction_amount=200)
        b = c.post("/api/simulate", json={"scenario": sc}).json()
        assert 500 <= b["scenario"]["projected_low"]["balance"] <= 650
