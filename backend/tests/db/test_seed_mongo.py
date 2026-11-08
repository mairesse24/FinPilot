from datetime import date
from decimal import Decimal

import mongomock

from app.data.synthetic import DEMO_USER_ID
from app.db.mongo import MongoRepository
from scripts import seed_database
from scripts.seed_database import build_dataset, main, resolve_mongodb_uri


def test_seed_main_loads_demo_into_mongo():
    repo = MongoRepository("mongodb://unused", client=mongomock.MongoClient())
    assert main(["--reset"], repo=repo) == 0
    profile = repo.load_profile(DEMO_USER_ID, date.today())
    checking = next(a for a in profile.accounts if a.account_type == "checking")
    assert checking.balance == Decimal("2400.00")
    users = build_dataset(date.today(), 2).users
    assert len(users) == 3
    assert all(repo.get_user(u.id) is not None for u in users)


def test_mongo_uri_resolution_order(tmp_path, monkeypatch, capsys):
    env = tmp_path / ".env"
    env.write_text("OTHER=1\nMONGODB_URI='mongodb://file-secret'\n")
    monkeypatch.setattr(seed_database, "ENV_PATH", env)
    monkeypatch.delenv("MONGODB_URI", raising=False)
    assert resolve_mongodb_uri(None) == "mongodb://file-secret"
    monkeypatch.setenv("MONGODB_URI", "mongodb://env-secret")
    assert resolve_mongodb_uri(None) == "mongodb://env-secret"
    assert resolve_mongodb_uri("mongodb://flag-secret") == "mongodb://flag-secret"
    env.write_text("")
    monkeypatch.delenv("MONGODB_URI")
    assert resolve_mongodb_uri(None) is None
    out = capsys.readouterr()
    assert "secret" not in out.out + out.err


def test_seed_returns_1_when_unreachable_without_leaking_uri(monkeypatch, capsys):
    class Down:
        def __init__(self, uri, db_name="finpilot"):
            pass

        def ping(self):
            return False

        def close(self):
            pass

    monkeypatch.setattr("app.db.mongo.MongoRepository", Down)
    rc = main(["--mongodb-uri", "mongodb://user:s3cret@host/"])
    out = capsys.readouterr()
    assert rc == 1
    assert "s3cret" not in out.out + out.err
