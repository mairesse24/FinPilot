"""Seed MongoDB (or legacy Postgres). Run: python -m scripts.seed_database --reset

The MongoDB URI comes from --mongodb-uri, env MONGODB_URI or backend/.env (never printed).
Without a URI it falls back to Postgres (--apply-schema, --database-url).
"""
import argparse
import os
from datetime import date
from pathlib import Path

from app.data.synthetic import DEMO_USER_ID, build_demo_customer, build_random_customers
from app.db.repository import SeedDataset

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _env_value(key: str) -> str | None:
    """Parse KEY=value from backend/.env (the value is never printed)."""
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text().splitlines():
        if line.strip().startswith(key + "="):
            return line.split("=", 1)[1].strip().strip("'\"") or None
    return None


def _url_from_env_file() -> str | None:
    return _env_value("DATABASE_URL")


def resolve_mongodb_uri(flag: str | None) -> str | None:
    return flag or os.environ.get("MONGODB_URI") or _env_value("MONGODB_URI")


def build_dataset(as_of: date, users: int) -> SeedDataset:
    ds = SeedDataset()
    for part in (build_demo_customer(as_of), build_random_customers(as_of, n=users, seed=42)):
        for name in ("users", "accounts", "transactions", "bills", "income_sources"):
            getattr(ds, name).extend(getattr(part, name))
    return ds


def main(argv=None, repo=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--reset", action="store_true")
    p.add_argument("--apply-schema", action="store_true")
    p.add_argument("--as-of", type=date.fromisoformat, default=None)
    p.add_argument("--users", type=int, default=2)
    p.add_argument("--database-url", default=None)
    p.add_argument("--mongodb-uri", default=None)
    a = p.parse_args(argv)

    mongo = False
    if repo is None:
        uri = resolve_mongodb_uri(a.mongodb_uri)
        if uri:
            from app.db import mongo as mongo_mod
            db_name = os.environ.get("MONGODB_DB") or _env_value("MONGODB_DB") or "finpilot"
            repo = mongo_mod.MongoRepository(uri, db_name)
            if not repo.ping():
                print("error: cannot connect to MongoDB (check MONGODB_URI)")
                return 1
            mongo = True
    else:
        from app.db.mongo import MongoRepository
        mongo = isinstance(repo, MongoRepository)
    if repo is None:
        url = a.database_url or os.environ.get("DATABASE_URL") or _url_from_env_file()
        if not url:
            print("error: no database URL (use --database-url, DATABASE_URL or backend/.env)")
            return 2
        from app.db.postgres import PgRepository
        repo = PgRepository(url)
    if a.apply_schema and not mongo:
        repo.apply_schema()
    if a.reset:
        repo.reset()
    ds = build_dataset(a.as_of or date.today(), a.users)
    repo.insert_dataset(ds)
    print(f"seeded users={len(ds.users)} accounts={len(ds.accounts)} "
          f"transactions={len(ds.transactions)} bills={len(ds.bills)} "
          f"income_sources={len(ds.income_sources)}")
    print(f"demo user id: {DEMO_USER_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
