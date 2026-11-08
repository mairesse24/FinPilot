# Backend MVP — 2-Hour Plan (supersedes the 15-task plan where they differ)

Specs still apply: `../specs/2026-11-07-backend-design.md`. Detailed task text (signatures, formulas, test names) lives in `2026-11-07-backend-implementation.md`; this file only says **what changes** and **who does what when**.
Execution: subagent-driven. Parallel agents only touch their own files.

## Cuts (all approved or defaulted)

| Cut | Replaced by |
|---|---|
| Custom error envelope | FastAPI default errors (`HTTPException` 404, default 422) |
| App crashes without `DATABASE_URL` | No `DATABASE_URL` → in-memory repo preloaded with the demo data |
| Writing alerts/snapshots on GET | Tables exist in `schema.sql`; nothing writes them. Drop `replace_alerts`, `list_alerts`, `save_snapshot_if_absent` |
| 10 random customers | Alex + 2 others |
| Health: two sub-metrics for cash flow and discipline | One metric each: cash flow = inflow÷outflow ratio; discipline = discretionary share of variable spend |
| `unusual_spending` Guardian rule | Removed (PDF lists anomaly detection as stretch). Keep 3 rules: low balance, debt burden, low emergency savings |
| `category` option in simulator | Removed. Cut applies to discretionary categories only |
| Chat keyword router with 5 intents | 3 intents: health, risk/forecast, "what if I cut $X". Registry keeps 5 read-only tools |
| 10 hand-written example JSON files + validator test | Example files are dumped from real baseline responses once endpoints work (Phase 3). Frontend reads `/openapi.json` until then |
| Edge-case test lists | Keep only: unknown user 404, bad params 422, empty-user no-crash, gateway fallback, demo scenario, one end-to-end test |
| Gateway "wrong return type" check | Keep: missing module → baseline; raises → baseline + warning |

## Timeline (120 min)

| Minutes | Who | Work | Done when |
|---|---|---|---|
| 0–10 | You | Review this page. **In parallel:** create Supabase project (`docs/supabase-setup.md` steps 1–3), put `DATABASE_URL` in `backend/.env` | You say "go"; `.env` exists |
| 10–35 | **Agent 1** (alone) | Foundation: scaffold + CORS + `/healthz`; domain models, metrics, projection; schemas; in-memory repo; demo data (Alex + 2); auto-registering routers; `/api/accounts`, `/api/transactions` | `pytest` green; `/openapi.json` shows all schema models → **tell Member 1 and 3** |
| 35–75 | **Agent 2** | Baseline health + `/api/health` | tests green |
|  | **Agent 3** | Baseline forecast → Guardian (3 rules) → simulator; `/api/forecast`, `/guardian`, `/simulate`; **tune Alex until demo scenario test passes** | demo-scenario test green |
|  | **Agent 4** | Gateway; `schema.sql`; `PgRepository`; `seed_database.py`; real Supabase load | `DATABASE_URL` run returns Alex |
| 75–100 | **Agent 5** | `/api/dashboard`; tool registry + baseline chat + `/api/chat`; dump `docs/examples/*.json` + `docs/api-contracts.md` | end-to-end test green |
| 100–120 | Agent 6 + me | `render.yaml`, README, deploy to Render, smoke test live URL, final review | live `/api/guardian` returns the alert |

Agents 2–4 depend only on Agent 1's output (models, schemas, repo, demo data). Agent 5 depends on 2–3.

## Hard rule if time slips
Drop in this order: Postgres (stay in-memory on Render) → chat router (fixed summary) → dashboard polish. Never drop: demo scenario, Guardian, simulate.
