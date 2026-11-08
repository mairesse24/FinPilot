from datetime import date
import os

# app.main constructs its default repository at import time. Never let a local
# developer .env trigger live banking calls during test collection.
os.environ["DATA_SOURCE"] = "demo"

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db.memory import InMemoryRepository
from app.db.repository import SeedDataset
from app.main import create_app
from tests.factories import AS_OF, UID, empty_profile, make_profile

EMPTY_UID = "u-empty"


def to_dataset(*profiles) -> SeedDataset:
    ds = SeedDataset()
    for p in profiles:
        ds.users.append(p.user)
        ds.accounts += p.accounts
        ds.transactions += p.transactions
        ds.bills += p.bills
        ds.income_sources += p.income_sources
    return ds


@pytest.fixture
def settings() -> Settings:
    """Never reads the developer's .env."""
    return Settings(_env_file=None, data_source="demo", database_url=None, demo_user_id=UID,
                    intelligence_mode="baseline", as_of_date=AS_OF)


@pytest.fixture
def repo() -> InMemoryRepository:
    return InMemoryRepository(to_dataset(make_profile(), empty_profile(user_id=EMPTY_UID)))


@pytest.fixture
def client(repo, settings) -> TestClient:
    return TestClient(create_app(repo=repo, settings=settings))
