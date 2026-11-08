import os
from datetime import date

import pytest

from app.data.synthetic import DEMO_USER_ID, build_demo_customer
from app.db.repository import SeedDataset
from scripts.seed_database import main as seed_main

AS_OF = date(2026, 11, 7)


def test_seed_main_with_memory_repo(capsys):
    from app.db.memory import InMemoryRepository

    class Repo(InMemoryRepository):
        def apply_schema(self):
            pass

    repo = Repo()
    assert seed_main(["--reset", "--apply-schema", "--as-of", "2026-11-07"], repo=repo) == 0
    assert repo.get_user(DEMO_USER_ID) is not None
    assert DEMO_USER_ID in capsys.readouterr().out


pytestmark_pg = pytest.mark.skipif(not os.environ.get("DATABASE_URL"),
                                   reason="DATABASE_URL not set")


@pytest.fixture
def pg():
    from app.db.postgres import PgRepository
    repo = PgRepository(os.environ["DATABASE_URL"])
    repo.apply_schema()
    repo.reset()
    yield repo
    repo.close()


@pytestmark_pg
def test_roundtrip(pg):
    ds = build_demo_customer(AS_OF)
    pg.insert_dataset(ds)
    assert pg.ping() is True
    prof = pg.load_profile(DEMO_USER_ID, AS_OF)
    assert {a.id for a in prof.accounts} == {a.id for a in ds.accounts}
    assert {b.id for b in prof.bills} == {b.id for b in ds.bills}
    assert {s.id for s in prof.income_sources} == {s.id for s in ds.income_sources}
    checking = next(a for a in prof.accounts if a.account_type == "checking")
    assert checking.balance == next(a for a in ds.accounts if a.id == checking.id).balance
    page, total = pg.list_transactions(DEMO_USER_ID, limit=5, offset=0)
    assert total == len(ds.transactions) and len(page) == 5
    assert page[0].date >= page[-1].date
    assert pg.get_user("not-a-uuid") is None
    pg.reset()
    assert pg.get_user(DEMO_USER_ID) is None
