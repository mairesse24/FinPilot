# Switch the Backend Database to MongoDB Atlas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MongoDB Atlas the only database of the FinPilot backend, to qualify for the MongoDB prize.

**Architecture:** The database sits behind the `Repository` interface (`backend/app/db/repository.py`). Add a `MongoRepository`, choose it from `MONGODB_URI`, then remove the Postgres code. No API, schema or intelligence code changes.

**Tech Stack:** Python 3.12, FastAPI, `pymongo[srv]` (sync), `mongomock` (tests), MongoDB Atlas M0, Render.

**Spec:** the existing interface in `backend/app/db/repository.py`; data model in `docs/superpowers/specs/2026-11-07-backend-design.md` §4 (collections replace tables).

---

## Start here (for the human)

| Stage | Who | What | Time |
|---|---|---|---|
| **A** | **You** | Follow [docs/mongodb-setup.md](../../mongodb-setup.md). Result: a `MONGODB_URI=` line in `backend/.env`. Say "done". | 10 min |
| **B** | Agent | Tasks 1–3 below: settings, `MongoRepository`, seed script. | 30 min |
| **C** | Agent + you | Task 4: test against Atlas, then add `MONGODB_URI` in Render and redeploy. | 15 min |
| **D** | Agent | Task 5: delete Supabase/Postgres code and docs, so "MongoDB only" is true. | 10 min |

Stages A and B can run at the same time. Stage C needs both. **Rollback until Task 5:** delete `MONGODB_URI` in Render and redeploy.
**Prize check (please do):** read the prize rules and tell me if they need more than "MongoDB Atlas is the database" (for example a named feature such as Vector Search). I will add a task if so.

---

## Global Constraints

- Branch: create `mongodb` from `origin/gokul` (it already edits `factory.py` and `config.py`). Do not push to `main`.
- Run tests from the repo root with `pytest -q`. On a Mac without `libomp`, add `--ignore=tests/test_conditions.py --ignore=tests/test_intelligence.py`.
- Never print, log or commit the connection string or password. Redact it from error messages.
- Collections: `users, accounts, transactions, recurring_bills, income_sources`. Database name from `MONGODB_DB`, default `finpilot`.
- Ids: the existing string ids become `_id`. Money: `Decimal128`. Dates: `"YYYY-MM-DD"` strings. Each transaction document also stores `user_id`.
- Indexes: `transactions` on `(user_id, date desc)` and `(user_id, category, date desc)`.
- `pymongo` connects with `serverSelectionTimeoutMS=5000`, so an unreachable Atlas cannot hang startup.
- Startup never crashes for lack of a database: order is MongoDB → (Postgres, until Task 5) → built-in demo data.

## Review Focus

1. Atlas unreachable, or a wrong password → the app starts on the next fallback within seconds and logs one line without the secret. (Task 1)
2. Money keeps exact cents: `Decimal("2400.00")` stored and read back is equal, with no float. (Task 2)
3. The 180-day window: a transaction on day 180 is included, on day 181 excluded; one on `as_of` is included, one the day after is not. (Task 2)
4. `total` in `list_transactions` follows the filters, not the page size. (Task 2)
5. Same data, same answers: API output from `MongoRepository` equals the output from `InMemoryRepository`. (Task 4)

---

### Task 1: Settings, dependencies, and database selection

**Files:**
- Modify: `backend/app/config.py`, `backend/app/db/factory.py`, `backend/requirements.txt`, `backend/.env.example`
- Test: `backend/tests/db/test_factory.py`

**Interfaces:**
- Produces: `Settings.mongodb_uri: str | None = None`, `Settings.mongodb_db: str = "finpilot"`. `build_repo(settings) -> Repository` tries `app.db.mongo.MongoRepository(uri, db)` first, requiring `ping()` to be true.

- [ ] **Step 1: Write the failing tests** (`test_factory.py`): `test_uses_mongo_when_reachable` (patch `MongoRepository` with a fake whose `ping()` returns `True` → returned object is that fake); `test_falls_back_when_ping_false` (→ not the Mongo fake); `test_falls_back_when_constructor_raises` (no exception escapes); `test_log_never_contains_uri` (use `caplog`; the secret string `"s3cret"` in the URI is absent from all log text).
- [ ] **Step 2:** Run `pytest backend/tests/db/test_factory.py -q`. Expected: FAIL (no `mongo` module / setting).
- [ ] **Step 3: Implement** the settings, the factory order from Global Constraints, and one log line `repository: mongodb`. Add `pymongo[srv]` and `mongomock` to `requirements.txt` with exact pinned versions (install first, then copy the installed versions). Add `MONGODB_URI=` and `MONGODB_DB=finpilot` to `.env.example`.
- [ ] **Step 4:** Run the tests again. Expected: PASS.
- [ ] **Step 5: Commit** `feat(db): choose MongoDB from MONGODB_URI`

---

### Task 2: `MongoRepository`

**Files:**
- Create: `backend/app/db/mongo.py`, `backend/tests/db/test_mongo_repository.py`

**Interfaces:**
- Consumes: `Repository`, `SeedDataset` (`backend/app/db/repository.py`); models in `backend/app/calc/models.py`.
- Produces: `class MongoRepository(uri: str, db_name: str = "finpilot")` with `get_user(user_id) -> User | None`, `load_profile(user_id, as_of: date) -> FinancialProfile | None` (transactions from `as_of - 180 days` through `as_of`), `list_transactions(user_id, *, limit, offset, category=None, date_from=None, date_to=None) -> tuple[list[Transaction], int]` (newest first), `reset() -> None` (drops only the five app collections), `insert_dataset(ds) -> None` (`insert_many` per collection, then creates the indexes), `ping() -> bool`, `close() -> None`. Constructor accepts an optional `client` argument so tests can inject `mongomock.MongoClient()`.

- [ ] **Step 1: Write the failing tests** (mongomock, built from `build_demo_customer`): `test_roundtrip_matches_in_memory` (profile accounts, bills, income, and transaction ids equal `InMemoryRepository`'s); `test_money_keeps_exact_cents` (checking balance `== Decimal("2400.00")`, and the raw stored value is `Decimal128`); `test_profile_window_edges` (transactions on `as_of-180d` and `as_of` are included, `as_of-181d` and `as_of+1d` are excluded); `test_pagination_and_total` (limit 2 → 2 items, `total` is the full count); `test_filters_change_total` (category filter and `date_from`/`date_to` both reduce `total`); `test_newest_first`; `test_unknown_user_returns_none`; `test_empty_user_returns_empty_lists`; `test_reset_drops_only_app_collections` (an extra collection `keep` survives); `test_ping_true_and_false` (false when the injected client's `admin.command` raises).
- [ ] **Step 2:** Run `pytest backend/tests/db/test_mongo_repository.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** `MongoRepository` and two small helpers `_to_decimal128(Decimal) -> Decimal128` and `_from_decimal128(Decimal128) -> Decimal`. Dates are stored and compared as ISO strings.
- [ ] **Step 4:** Run the tests again. Expected: all PASS.
- [ ] **Step 5: Commit** `feat(db): MongoRepository`

---

### Task 3: Seed script

**Files:**
- Modify: `backend/scripts/seed_database.py`
- Test: `backend/tests/db/test_seed_mongo.py`

**Interfaces:**
- Consumes: `MongoRepository`, `build_demo_customer`, `build_random_customers`, and the existing `main(argv=None, repo=None) -> int`.
- Produces: seeding uses `MongoRepository` when `MONGODB_URI` is set (from the environment or parsed from `backend/.env`, never printed). Flags: `--reset`, `--as-of YYYY-MM-DD`, `--users N` (default 2), `--mongodb-uri`. Output: counts and the demo user id only.

- [ ] **Step 1: Write the failing test:** `test_seed_main_loads_demo_into_mongo` (inject a mongomock-backed `MongoRepository`; after `main(["--reset"], repo=repo)` returns 0, `repo.load_profile(DEMO_USER_ID, today)` has checking balance `Decimal("2400.00")` and 3 users exist).
- [ ] **Step 2:** Run it. Expected: FAIL.
- [ ] **Step 3: Implement** the store selection and the new flag. Keep the old flags until Task 5.
- [ ] **Step 4:** Run it. Expected: PASS.
- [ ] **Step 5: Commit** `feat(seed): seed MongoDB`

---

### Task 4: Verify against Atlas, then cut over

**Files:** none new (a throwaway comparison script goes in the scratchpad, not the repo).

**Interfaces:** consumes Tasks 1–3 and the human's `MONGODB_URI` in `backend/.env`.

- [ ] **Step 1: Seed Atlas:** `cd backend && python -m scripts.seed_database --reset`. Expected output: counts (3 users, 8 accounts, ≈4,500 transactions) and the demo user id.
- [ ] **Step 2: Check the app log:** start the app with the real `.env`; `curl localhost:<port>/healthz` → `{"status":"ok","database":true}` and the log shows `repository: mongodb`.
- [ ] **Step 3: Same answers:** call `/api/dashboard, /accounts, /health, /forecast?days=30, /guardian` with `AS_OF_DATE` set to the seed date on (a) the Mongo app and (b) the in-memory app, and compare the JSON after removing `generated_at`. Expected: identical.
- [ ] **Step 4: Run the suite:** `pytest -q` (with the Mac ignores if needed). Expected: all pass.
- [ ] **Step 5 (human): Render.** Add `MONGODB_URI` in the service's **Environment** tab (value = the `.env` string) and redeploy. Agent then runs the live endpoint checks (`/healthz`, `/api/guardian`, `/api/simulate`, `/api/chat`) and confirms `database: true`.
- [ ] **Step 6: Commit** only if files changed: `chore: verify MongoDB cutover`

---

### Task 5: Remove Supabase/Postgres, so MongoDB is the only database

Run this only after Task 4 passes live.

**Files:**
- Delete: `backend/app/db/postgres.py`, `backend/app/db/schema.sql`, `backend/tests/db/test_postgres_integration.py`, `docs/supabase-setup.md`
- Modify: `backend/app/config.py` (remove `database_url`), `backend/app/db/factory.py` (order: MongoDB → demo data), `backend/requirements.txt` (remove `psycopg`, `psycopg-pool`), `backend/.env.example`, `backend/scripts/seed_database.py` (remove `--apply-schema` and `--database-url`), `render.yaml` (`DATABASE_URL` → `MONGODB_URI`), `README.md`, `docs/handoff-member-3-and-1.md`, `docs/MVP-requirements.md` (replace "Supabase PostgreSQL" with "MongoDB Atlas"), `docs/api-contracts.md` if it mentions it.

- [ ] **Step 1: Write the failing test:** `test_no_postgres_left` in `backend/tests/db/test_factory.py` — `importlib.util.find_spec("psycopg")` is `None` in the project requirements (check the text of `requirements.txt` has no `psycopg`), and `Settings()` has no attribute `database_url`.
- [ ] **Step 2:** Run it. Expected: FAIL.
- [ ] **Step 3: Delete and edit** the files above. Search the repo for `supabase`, `psycopg`, `DATABASE_URL` and `Postgres` (case-insensitive) and fix every remaining mention except history notes.
- [ ] **Step 4:** Run `pytest -q`. Expected: all pass; the grep above returns nothing in code or setup docs.
- [ ] **Step 5: Commit** `refactor: MongoDB Atlas is the only database`
- [ ] **Step 6:** Push the `mongodb` branch and tell the human which Render settings to change: delete `DATABASE_URL`, keep `MONGODB_URI`.

---

## Self-Review

- **Coverage:** switch (Tasks 1–3), proof against real Atlas (Task 4), prize-visible "only database" (Task 5), human steps separated (`docs/mongodb-setup.md`).
- **Consistency:** `MongoRepository(uri, db_name)`, `Settings.mongodb_uri/mongodb_db`, and the collection names match across tasks.
- **Open:** the prize rules may need more than Atlas as the database; the human confirms in the "Start here" box.
