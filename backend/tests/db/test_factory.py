import logging
import sys
import types

import pytest

from app.config import Settings
from app.db.factory import build_repo

URI = "mongodb+srv://user:s3cret@cluster.example.mongodb.net/?retryWrites=true"


def _install(monkeypatch, *, ping=True, raises=None):
    class FakeMongoRepository:
        def __init__(self, uri, db_name="finpilot"):
            if raises:
                raise raises
            self.uri, self.db_name = uri, db_name

        def ping(self):
            return ping

    mod = types.ModuleType("app.db.mongo")
    mod.MongoRepository = FakeMongoRepository
    monkeypatch.setitem(sys.modules, "app.db.mongo", mod)
    return FakeMongoRepository


def _settings(**kw):
    return Settings(_env_file=None, mongodb_uri=URI, **kw)


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.mongodb_uri is None
    assert s.mongodb_db == "finpilot"


def test_uses_mongo_when_reachable(monkeypatch):
    fake = _install(monkeypatch, ping=True)
    repo = build_repo(_settings(mongodb_db="mydb"))
    assert isinstance(repo, fake)
    assert repo.uri == URI and repo.db_name == "mydb"


def test_falls_back_when_ping_false(monkeypatch):
    fake = _install(monkeypatch, ping=False)
    repo = build_repo(_settings())
    assert not isinstance(repo, fake)


def test_falls_back_when_constructor_raises(monkeypatch):
    fake = _install(monkeypatch, raises=RuntimeError(f"cannot connect {URI}"))
    repo = build_repo(_settings())
    assert not isinstance(repo, fake)


@pytest.mark.parametrize("mode", ["ok", "false", "raises"])
def test_log_never_contains_uri(monkeypatch, caplog, mode):
    _install(
        monkeypatch,
        ping=mode == "ok",
        raises=RuntimeError(f"bad {URI}") if mode == "raises" else None,
    )
    with caplog.at_level(logging.DEBUG):
        build_repo(_settings())
    assert "s3cret" not in caplog.text
    assert "s3cret" not in " ".join(str(r.args) for r in caplog.records)
