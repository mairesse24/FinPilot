"""The Nessie seeder creates fictional resources only; checking balance is configurable."""
from datetime import date
from types import SimpleNamespace

import pytest

from scripts import seed_nessie


class FakeResponse:
    status_code = 201

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeHttp:
    def __init__(self):
        self.posts = []

    def post(self, url, params=None, json=None):
        self.posts.append((url, json))
        return FakeResponse({"objectCreated": {"_id": f"id-{len(self.posts)}"}})


class FakeNessieClient:
    last = None

    def __init__(self, key, base_url="https://api.nessieisreal.com"):
        self.key, self.base_url, self.client = key, base_url, FakeHttp()
        FakeNessieClient.last = self

    def close(self):
        pass


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    monkeypatch.setattr(seed_nessie, "NessieClient", FakeNessieClient)
    monkeypatch.setattr(FakeNessieClient, "last", None)
    monkeypatch.setattr(seed_nessie, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(seed_nessie, "SCHEDULES", tmp_path / "schedules.json")
    settings = SimpleNamespace(nessie_api_key="test-key", nessie_base_url="https://api.nessieisreal.com",
                               as_of_date=date(2026, 11, 7))

    def run(**kwargs):
        seed_nessie.seed(settings, **kwargs)
        accounts = [b for u, b in FakeNessieClient.last.client.posts if u.endswith("/accounts") and b.get("type")]
        return {a["nickname"]: a["balance"] for a in accounts}, tmp_path / "schedules.json"
    return run


def test_default_checking_balance_is_unchanged(seeded):
    balances, _ = seeded()
    assert balances["FinPilot Demo Checking"] == 6500
    assert balances["ABC Bank Checking"] == 5000
    assert balances["XYZ Bank Checking"] == 20000


def test_checking_balance_is_configurable(seeded):
    balances, schedules = seeded(checking_balance=2400)
    assert balances["FinPilot Demo Checking"] == 2400
    assert balances["XYZ High-Yield Savings"] == 12000
    assert balances["ABC Travel Card"] == 1850
    assert len(balances) == 7
    assert schedules.exists()


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), "abc", True])
def test_bad_checking_balance_is_rejected_before_any_request(seeded, bad):
    with pytest.raises(ValueError):
        seeded(checking_balance=bad)
    assert FakeNessieClient.last is None or FakeNessieClient.last.client.posts == []
