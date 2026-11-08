# FinSight AI Backend — Design Spec

Date: 2026-11-07 · Owner: Member 2 (backend) · Parent: [MVP-requirements.md](../../MVP-requirements.md)

## 1. Purpose and success criteria

Build the FastAPI backend and Supabase data foundation so that:
- the frontend (Member 1) can build against stable, documented JSON immediately, and later against real data without changes;
- the AI/ML member (Member 3) can plug real forecasting, scoring, Guardian, simulation and Copilot code in with no backend rewrite;
- the end-to-end demo (Understand → Detect → Simulate → Recommend) works **from day one with deterministic baseline logic**, and gets better as real intelligence modules land.

Done means: all MVP endpoints return schema-valid data; the seeded demo customer reproduces the Guardian alert and the spending-cut recovery; tests pass; deployed on Render against Supabase.

## 2. Decisions and assumptions

| Decision | Choice | Why |
|---|---|---|
| DB access | `psycopg` 3 + `psycopg_pool`, plain SQL, Supabase **session pooler** URL | Only the DB is needed (no Supabase API keys, no ORM). `NUMERIC` maps to `Decimal`. Pooler works on IPv4 hosts. |
| Auth | None. One demo user by default; optional `?user_id=` | Per MVP decision. Tables keep `user_id` so auth can be added later. |
| PNC starter kit | **Not a dependency.** The repo URL was not findable, so this design builds its own synthetic data generator and baseline calculations. If the team gets the kit, a loader and calculation swap-ins fit behind the seams in §5 and §7. | Avoids blocking on an unseen repo. |
| Intelligence integration | Backend defines the function contract and ships deterministic baselines; Member 3's modules override them | Parallel work with no blocking. |
| Time | `as_of` date from env/flag, defaults to today | Makes seeded data and tests deterministic. |
| Money | `Decimal` in Python, `NUMERIC(14,2)` in DB, serialized as JSON numbers with 2 decimals | No float drift in balances. |
| Sign convention | `transactions.amount`: negative = money out, positive = money in. `accounts.balance`: always the positive amount held (assets) or owed (credit_card, loan) | Simple, documented, used consistently. |

## 3. Architecture

```
Routes (thin, HTTP only)
  └─ Services (orchestration: load profile, call gateway, shape response)
       ├─ Repository (SQL only; Protocol with Pg + InMemory implementations)
       ├─ Calc (pure functions over FinancialProfile; no I/O)
       └─ Intelligence Gateway ──► intelligence/<module>.py  (Member 3, if present)
                                └─► baseline/<module>.py      (backend fallback)
```

Units and boundaries:
- **Repository** answers "give me the data." It is the only code touching SQL. Tests use `InMemoryRepository`, so no database is needed for unit or API tests.
- **FinancialProfile** (dataclass bundle: user, accounts, last 180 days of transactions, bills, income sources, `as_of`) is the single input to all calculations. It is plain data, so Member 3 can unit-test their code with a fixture and no DB.
- **Calc** is pure, deterministic math: net worth, income/expense totals, emergency-savings months, debt-to-income, upcoming bills, daily balance projection.
- **Intelligence Gateway** picks real vs baseline per module and stamps `meta.source`.
- **Tool registry** exposes read-only functions (and OpenAI-style JSON schemas) the Copilot may call.

## 4. Data model

Schema file: `backend/app/db/schema.sql`. All tables have RLS enabled with no policies (see [supabase-setup.md](../../supabase-setup.md)).

From the proposal (unchanged): `users`, `accounts`, `transactions`, `recurring_bills`, `financial_snapshots`, `risk_alerts`.

Additions beyond the proposal's minimum (needed by the features, flagged for review):

| Table / column | Why |
|---|---|
| `income_sources(id, user_id, name, amount, frequency, next_pay_date)` | Cash-flow projection needs **known future income**; deriving paydays from history is fragile. |
| `accounts.name`, `accounts.apr`, `accounts.min_payment`, `accounts.credit_limit` | Debt Management score and "high debt burden" rule need payments and rates. |
| `recurring_bills.name`, `.category`, `.frequency` | Dashboard shows upcoming bills; projection repeats them. |
| `users.safety_buffer` (default 500) | Guardian threshold; Digital Twin and alerts reference it. |

`account_type` ∈ `checking | savings | credit_card | loan`. `frequency` ∈ `weekly | biweekly | monthly`. `severity` ∈ `low | medium | high`.
`financial_snapshots` is written by the seed script and on each `/api/health` call only if no snapshot exists for that date (cheap history for trend lines). `risk_alerts` is written by `/api/guardian` (replace-today semantics) so the dashboard can list active alerts.

## 5. Intelligence contract (the seam with Member 3)

Member 3 creates modules under `backend/intelligence/`. The gateway imports a module if it exists and exposes the named function; otherwise the baseline runs.

| Module | Function | Returns (schema in `app/schemas`) |
|---|---|---|
| `health_score.py` | `compute_health_score(profile)` | `HealthResult` |
| `forecasting.py` | `forecast(profile, days)` | `ForecastResult` |
| `guardian.py` | `evaluate(profile, forecast)` | `list[Alert]` |
| `simulator.py` | `simulate(profile, scenario)` | `SimulationResult` |
| `copilot.py` | `chat(messages, tools)` | `ChatResult` |
| `economic_pressure.py` | `compute(indicators, profile)` | `EconomyResult` (next priority) |

Rules:
- Inputs and outputs are the Pydantic models/dataclasses defined by the backend, so contracts are enforced in one place.
- `INTELLIGENCE_MODE=auto` (default) uses real modules when present; `baseline` forces fallbacks (useful for demos and tests).
- If a real module raises, the gateway logs it and falls back to the baseline, setting `meta.source="baseline"` and `meta.warning`. The demo never shows a 500 for this.
- Every response carries `meta`: `{source: "model"|"baseline", is_prototype_estimate: true, as_of, generated_at}`.

## 6. API

Common: JSON, no auth, `user_id` query param (default = demo user id from config). Errors: `{"error": {"code": "...", "message": "..."}}` with 404 unknown user, 422 invalid input. Health check at `GET /healthz` (since `/api/health` is the score). CORS limited to `CORS_ORIGINS`.

| Endpoint | Response (key fields) |
|---|---|
| `GET /api/accounts` | `accounts[]`: id, name, type, balance |
| `GET /api/transactions?limit&offset&category&from&to` | `items[]`: id, account_id, amount, category, date; `total` |
| `GET /api/dashboard` | `net_worth`, `assets`, `liabilities`, `accounts[]`, `income_30d`, `spending_30d`, `by_category[]`, `upcoming_bills[]` (next 14 days), `health_score`, `active_alerts[]`, `meta` |
| `GET /api/health` | `score`, `components[]` (name, weight, score, metrics{}, explanation), `strengths[]`, `weaknesses[]`, `meta` |
| `GET /api/forecast?days=7\|30\|90` | `days`, `series[]` (date, projected_balance, low, high, predicted_spend), `projected_low` {date, balance}, `safety_buffer`, `shortfall` (bool), `assumptions[]`, `evaluation` (MAE vs baseline, when real model present), `meta` |
| `GET /api/guardian` | `alerts[]`: id, rule, severity, title, cause, numbers{}, recommended_action, suggested_scenario (pre-filled `/api/simulate` body); `meta` |
| `POST /api/simulate` | Request: `scenario` = `{type:"spending_cut", reduction_amount, horizon_days=30, category?}`. Response: `baseline` and `scenario` blocks, each with `projected_low`, `end_balance`, `health_score`, `alerts[]`, plus `delta` and `series` for both; `meta` |
| `POST /api/chat` | Request: `messages[]` (role, content; client holds history), max 20 messages / 2,000 chars each. Response: `reply`, `tool_calls[]` (name, args, result summary), `meta` |
| `GET /api/economy` (next) | indicators (CPI, unemployment, rates) with values and dates, `pressure_index`, `source: live\|cached` |
| `GET /api/wrapped` (stretch) | Not in MVP |

`GET /api/guardian` includes `suggested_scenario` so a Guardian alert flows into the Digital Twin with one click, which is the core Detect → Simulate link.

Example payloads for every endpoint are written to `docs/api-contracts.md` **first** (contract-first), and the OpenAPI JSON at `/openapi.json` is the machine-readable contract. The frontend can generate types from it.

## 7. Baseline logic (deterministic, used until/unless Member 3 replaces it)

- **Health score:** the five components with the proposal's weights. Each is a documented piecewise-linear map to 0–100:
  - Cash Flow Stability: income ÷ expenses ratio and balance volatility.
  - Emergency Savings: liquid savings ÷ monthly essential expenses, full marks at 6 months.
  - Debt Management: monthly debt payments ÷ monthly income, full marks below 10%, zero above 50%.
  - Spending Discipline: variable-spend trend vs its 90-day average and share of discretionary spend.
  - Payment Readiness: liquid balance ÷ bills due in the next 30 days.
  - Each component returns the raw metrics and a plain-English explanation. Thresholds are constants in one file, labeled design assumptions.
- **Forecast:** variable daily spend = trailing 90-day mean by weekday; bills and income are placed on their dates; balance walks day by day; uncertainty band = ±1.28σ·√n of daily variable spend (≈80% interval), n days from today.
- **Guardian rules (≥3):** `low_projected_balance` (projected low < safety buffer within 30 days), `high_debt_burden` (debt payments > 36% of income), `low_emergency_savings` (< 1 month essentials), plus `unusual_spending` (week spend > 1.5× 90-day weekly mean). Each alert has cause, numbers, severity, action.
- **Simulate:** copy the profile, reduce variable spend by `reduction_amount` spread evenly over `horizon_days`, rerun forecast, health and Guardian, return the comparison.
- **Chat:** keyword intent router that calls registry tools and fills a template. No LLM. It exists so `/api/chat` works end to end before Member 3's OpenAI copilot lands.

## 8. Synthetic data and the demo customer

`scripts/seed_database.py [--reset] [--as-of YYYY-MM-DD] [--users N]` creates:
- **Demo customer ("Alex Rivera")**, hand-tuned and fixed: biweekly pay, rent due before the next paycheck, a checking balance of about $2,400, and discretionary spend such that the baseline projected low is **below the $500 buffer (target ≈ $320)** just before payday and a $200 cut lifts it **above $500 (target ≈ $520)**. A test asserts these inequalities, not exact cents.
- **N additional random users** (default 10, seeded RNG) with 12 months of transactions, varied income and debt, so there are "multiple simulated accounts".
- `--reset` truncates only the app tables. Dates are relative to `--as-of` (default today) so the scenario holds whenever you reseed; reseed before the demo.

## 9. Error handling, security, configuration

- Config via `pydantic-settings` from env: `DATABASE_URL`, `CORS_ORIGINS`, `DEMO_USER_ID`, `INTELLIGENCE_MODE`, `AS_OF_DATE` (optional), `OPENAI_API_KEY` (Member 3), `FRED_API_KEY` (next). `.env.example` committed, `.env` ignored. Secrets are never logged.
- All queries parameterized. `limit` capped at 500. Chat input length-capped. No endpoint writes financial state beyond snapshots/alerts; nothing moves money.
- Startup fails fast with a clear message if `DATABASE_URL` is missing; `/healthz` also reports DB reachability.

## 10. Testing

- Unit tests: calc functions and each baseline module on small hand-built profiles (including edge cases: no bills, zero income, empty history).
- API tests: FastAPI `TestClient` with `InMemoryRepository` injected via dependency override. Assert response validity against schemas and the demo-scenario inequalities.
- Gateway tests: real module present, absent, and raising.
- One optional integration test against Supabase, skipped unless `DATABASE_URL` is set.
- Run: `cd backend && pytest`.

## 11. Layout (backend part)

```
backend/
  app/{main.py, config.py, deps.py}
  app/routes/      one file per endpoint group
  app/schemas/     Pydantic models (shared contract)
  app/db/          schema.sql, pool.py, repository.py (Protocol + Pg), memory.py
  app/calc/        models.py (FinancialProfile), metrics.py, projection.py
  app/services/    profile.py, gateway.py, dashboard.py
  app/baseline/    health.py, forecast.py, guardian.py, simulate.py, chat.py
  app/tools/       registry.py
  intelligence/    (Member 3) README.md describing the §5 contract
  scripts/seed_database.py, scripts/synthetic.py
  tests/
  requirements.txt  .env.example  render.yaml (or documented Render settings)
docs/api-contracts.md   docs/supabase-setup.md
```

## 12. Deployment

Render web service, root `backend/`, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, env vars set in the dashboard. Free tier sleeps when idle, so hit `/healthz` before the demo. Heavy ML libraries (LightGBM) are added to requirements by Member 3 only when needed.

## 13. Out of scope for this spec

Frontend, ML training, OpenAI Copilot internals (Member 3); FRED/`/api/economy` and Wrapped (post-MVP, designed to slot into the same gateway and route pattern); authentication.

## 14. Risks

- Member 3's output shapes drifting from the schemas. Mitigation: schemas live in the backend, are published first, and are changed only by agreement.
- Demo scenario sensitivity to baseline formulas. Mitigation: a dedicated test pins the inequalities.
- Render cold start during the demo. Mitigation: warm up with `/healthz`.
