import importlib
import logging
from datetime import date

from app.config import Settings
from app.data.synthetic import build_demo_customer, build_random_customers
from app.db.memory import InMemoryRepository
from app.db.repository import Repository, SeedDataset

log = logging.getLogger(__name__)


def build_repo(settings: Settings) -> Repository:
    """MongoDB when MONGODB_URI is set, else Postgres when DATABASE_URL is set, else in-memory demo data."""
    if settings.data_source == "nessie":
        from app.data.nessie import build_nessie_repo
        return build_nessie_repo(settings)
    warnings = []
    if settings.mongodb_uri:
        try:
            mongo = importlib.import_module("app.db.mongo")
            repo = mongo.MongoRepository(settings.mongodb_uri, settings.mongodb_db)
            if repo.ping():
                log.warning("repository: mongodb")
                repo.source = "configured MongoDB"
                return repo
            log.warning("MongoDB not reachable; trying next database")
        except Exception as exc:  # never crash startup; never log the URI
            log.warning("MongoDB unavailable (%s); trying next database", type(exc).__name__)
        warnings.append("Configured MongoDB unavailable; falling back.")
    if settings.database_url:
        try:
            pg = importlib.import_module("app.db.postgres")
            repo = pg.PgRepository(settings.database_url)
            if repo.ping():
                log.warning("repository: postgres")
                repo.source = "configured PostgreSQL"
                return repo
            log.warning("Postgres not reachable; using in-memory demo data")
        except Exception as exc:  # never crash startup for lack of a database
            log.warning("Postgres unavailable (%s); using in-memory demo data", type(exc).__name__)
        warnings.append("Configured PostgreSQL unavailable; generated demo records are being served.")
    as_of = settings.as_of_date or date.today()
    ds = SeedDataset()
    for part in (build_demo_customer(as_of), build_random_customers(as_of, n=2, seed=42)):
        for name in ("users", "accounts", "transactions", "bills", "income_sources"):
            getattr(ds, name).extend(getattr(part, name))
    log.warning("repository: memory")
    repo = InMemoryRepository(ds)
    repo.source, repo.warnings = "generated demo", warnings
    return repo
