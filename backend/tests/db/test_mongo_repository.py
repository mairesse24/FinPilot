import os
import uuid
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import mongomock
import pytest
from bson import Decimal128

from app.calc.models import Account, Transaction
from app.data.synthetic import DEMO_USER_ID, build_demo_customer
from app.db.memory import InMemoryRepository
from app.db.mongo import MongoRepository
from app.db.repository import SeedDataset

AS_OF = date(2026, 6, 1)
COLLECTIONS = {"users", "accounts", "transactions", "recurring_bills", "income_sources"}


def make(ds=None):
    repo = MongoRepository("mongodb://unused", "finpilot", client=mongomock.MongoClient())
    repo.insert_dataset(ds or build_demo_customer(AS_OF))
    return repo


def test_roundtrip_matches_in_memory():
    ds = build_demo_customer(AS_OF)
    mem = InMemoryRepository(ds).load_profile(DEMO_USER_ID, AS_OF)
    mon = make(ds).load_profile(DEMO_USER_ID, AS_OF)
    assert mon.user == mem.user
    key = lambda x: x.id
    assert sorted(mon.accounts, key=key) == sorted(mem.accounts, key=key)
    assert sorted(mon.bills, key=key) == sorted(mem.bills, key=key)
    assert sorted(mon.income_sources, key=key) == sorted(mem.income_sources, key=key)
    assert [t.date for t in mon.transactions] == [t.date for t in mem.transactions]
    assert {t.id for t in mon.transactions} == {t.id for t in mem.transactions}
    assert sorted(mon.transactions, key=key) == sorted(mem.transactions, key=key)
    assert mon.as_of == AS_OF


def test_money_keeps_exact_cents():
    repo = make()
    prof = repo.load_profile(DEMO_USER_ID, AS_OF)
    checking = next(a for a in prof.accounts if a.account_type == "checking")
    assert checking.balance == Decimal("2400.00")
    assert str(checking.balance) == "2400.00"
    raw = repo._db["accounts"].find_one({"_id": checking.id})
    assert isinstance(raw["balance"], Decimal128)
    assert raw["user_id"] == DEMO_USER_ID
    assert isinstance(raw["apr"], (Decimal128, type(None)))


def test_optional_fields_round_trip_as_none():
    ds = build_demo_customer(AS_OF)
    ds.accounts.append(Account(id="acc-none", user_id=DEMO_USER_ID, name="Zzz", account_type="savings",
                               balance=Decimal("1.10")))
    acc = next(a for a in make(ds).load_profile(DEMO_USER_ID, AS_OF).accounts if a.id == "acc-none")
    assert acc.apr is None and acc.min_payment is None and acc.credit_limit is None


def _edge_repo():
    ds = build_demo_customer(AS_OF)
    acct = next(a for a in ds.accounts if a.account_type == "checking")
    ds.transactions = []
    for tid, d in (("e-old", AS_OF - timedelta(days=181)), ("e-start", AS_OF - timedelta(days=180)),
                   ("e-end", AS_OF), ("e-future", AS_OF + timedelta(days=1))):
        ds.transactions.append(Transaction(tid, acct.id, Decimal("-1.00"), "x", d))
    return make(ds)


def test_profile_window_edges():
    ids = {t.id for t in _edge_repo().load_profile(DEMO_USER_ID, AS_OF).transactions}
    # Same window as InMemoryRepository/PgRepository: start exclusive, as_of inclusive.
    assert "e-end" in ids and "e-start" not in ids
    assert "e-old" not in ids and "e-future" not in ids
    assert "e-start" in {t.id for t in _edge_repo().load_profile(DEMO_USER_ID, AS_OF - timedelta(days=1)).transactions}


def test_pagination_and_total():
    repo = make()
    page, total = repo.list_transactions(DEMO_USER_ID, limit=2, offset=0)
    assert len(page) == 2
    all_, total_all = repo.list_transactions(DEMO_USER_ID, limit=100000, offset=0)
    assert total == total_all == len(all_) > 2
    page2, _ = repo.list_transactions(DEMO_USER_ID, limit=2, offset=2)
    assert [t.id for t in page2] == [t.id for t in all_[2:4]]


def test_filters_change_total():
    repo = make()
    _, total = repo.list_transactions(DEMO_USER_ID, limit=1, offset=0)
    _, by_cat = repo.list_transactions(DEMO_USER_ID, limit=1, offset=0, category="groceries")
    assert 0 < by_cat < total
    d_from, d_to = AS_OF - timedelta(days=10), AS_OF - timedelta(days=5)
    items, by_date = repo.list_transactions(DEMO_USER_ID, limit=1000, offset=0, date_from=d_from, date_to=d_to)
    assert 0 < by_date < total
    assert all(d_from <= t.date <= d_to for t in items)
    assert {t.date for t in items} >= {d_from, d_to}


def test_newest_first():
    items, _ = make().list_transactions(DEMO_USER_ID, limit=1000, offset=0)
    assert [(t.date, t.id) for t in items] == sorted(((t.date, t.id) for t in items), reverse=True)


def test_unknown_user_returns_none():
    repo = make()
    assert repo.get_user("nope") is None
    assert repo.load_profile("nope", AS_OF) is None


def test_empty_user_returns_empty_lists():
    ds = build_demo_customer(AS_OF)
    ds.accounts, ds.transactions, ds.bills, ds.income_sources = [], [], [], []
    repo = make(ds)
    prof = repo.load_profile(DEMO_USER_ID, AS_OF)
    assert prof.accounts == prof.transactions == prof.bills == prof.income_sources == []
    assert repo.list_transactions(DEMO_USER_ID, limit=10, offset=0) == ([], 0)


def test_insert_dataset_is_idempotent_for_indexes_and_creates_them():
    repo = make()
    repo.insert_dataset(SeedDataset())
    keys = [tuple(v["key"]) for v in repo._db["transactions"].index_information().values()]
    assert (("user_id", 1), ("date", -1)) in keys
    assert (("user_id", 1), ("category", 1), ("date", -1)) in keys


def test_reset_drops_only_app_collections():
    repo = make()
    repo._db["keep"].insert_one({"_id": 1})
    repo.reset()
    names = set(repo._db.list_collection_names())
    assert "keep" in names and not (COLLECTIONS & names)
    assert repo.get_user(DEMO_USER_ID) is None


def test_ping_true_and_false():
    repo = make()
    assert repo.ping() is True
    client = mongomock.MongoClient()
    bad = MongoRepository("mongodb://unused", client=client)
    client.admin.command = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
    assert bad.ping() is False
    repo.close()


def test_connection_failure_never_leaks_uri(monkeypatch):
    secret = "mongodb://user:s3cr3tpass@host.invalid/"
    import app.db.mongo as m

    def boom(*a, **k):
        raise RuntimeError(f"bad {secret}")
    monkeypatch.setattr(m.pymongo, "MongoClient", boom)
    with pytest.raises(Exception) as ei:
        MongoRepository(secret)
    assert "s3cr3tpass" not in str(ei.value) and "s3cr3tpass" not in repr(ei.value)


@pytest.mark.skipif(not os.environ.get("MONGODB_URI"), reason="MONGODB_URI not set")
def test_integration_roundtrip_against_atlas():
    name = f"finpilot_itest_{uuid.uuid4().hex[:8]}"
    repo = MongoRepository(os.environ["MONGODB_URI"], name)
    try:
        ds = build_demo_customer(AS_OF)
        repo.insert_dataset(ds)
        assert repo.ping()
        mem = InMemoryRepository(ds).load_profile(DEMO_USER_ID, AS_OF)
        prof = repo.load_profile(DEMO_USER_ID, AS_OF)
        assert {t.id for t in prof.transactions} == {t.id for t in mem.transactions}
        assert {a.id: a.balance for a in prof.accounts} == {a.id: a.balance for a in mem.accounts}
        page, total = repo.list_transactions(DEMO_USER_ID, limit=3, offset=0)
        assert len(page) == 3 and total >= 3
    finally:
        repo.reset()
        repo.close()
