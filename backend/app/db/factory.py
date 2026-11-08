import importlib
import logging
from datetime import date

from app.config import Settings
from app.data.synthetic import build_demo_customer, build_random_customers
from app.db.memory import InMemoryRepository
from app.db.repository import Repository, SeedDataset

log = logging.getLogger(__name__)


def build_repo(settings: Settings) -> Repository:
    """Postgres when DATABASE_URL is set and app.db.postgres exists; else in-memory demo data."""
    if settings.database_url:
        try:
            pg = importlib.import_module("app.db.postgres")
            repo = pg.PgRepository(settings.database_url)
            log.warning("repository: postgres")
            return repo
        except Exception as exc:  # never crash startup for lack of a database
            log.warning("Postgres unavailable (%s); using in-memory demo data", type(exc).__name__)
    as_of = settings.as_of_date or date.today()
    ds = SeedDataset()
    for part in (build_demo_customer(as_of), build_random_customers(as_of, n=2, seed=42)):
        for name in ("users", "accounts", "transactions", "bills", "income_sources"):
            getattr(ds, name).extend(getattr(part, name))
    log.warning("repository: memory")
    return InMemoryRepository(ds)
