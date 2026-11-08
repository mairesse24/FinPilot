# FinSight AI (FinPilot) — MVP Requirements

Source: `HackUTD 2026.pdf` (PNC 360° Financial Health Navigator challenge). Team of three, 24–36 hours.
This document defines the MVP for the **whole project**. Section 9 scopes the part this repo's owner builds: the **backend (Member 2)**.

## 1. Product goal

One continuous flow: **Detect → Simulate → Recommend**.
Guardian finds a risk, the Digital Twin tests a fix, and the Copilot explains the result using verified backend numbers. Every other feature supports this flow.

## 2. Ownership

| Area | Owner | Notes |
|---|---|---|
| Frontend & UX | Member 1 | Next.js, builds against mock JSON until the APIs are live |
| Backend, DB, APIs | **Member 2 (this repo's owner)** | FastAPI, Supabase, data ingestion, deployment |
| AI/ML & intelligence | Member 3 | Forecasting, score, Guardian, simulator, Copilot logic in `backend/intelligence/` |

The backend exposes the intelligence functions through the API and helps with deterministic financial calculations.

## 3. MVP features (all six must work before anything else)

| # | Feature | Acceptance criteria |
|---|---|---|
| F1 | Unified dashboard | Shows checking, savings, loans, credit cards, net worth, income, spending, upcoming bills and active alerts for a synthetic user. Multiple accounts and transaction histories. |
| F2 | Explainable health score | 0–100 score from 5 weighted components (Cash Flow Stability 25%, Emergency Savings 25%, Debt Management 20%, Spending Discipline 15%, Payment Readiness 15%). Each component is 0–100. Response includes the metrics behind each component and strengths and weaknesses. |
| F3 | Predictive cash flow | 7, 30 and 90 day forecasts of variable spending. Projected balance combines the forecast with known income and bills. Includes an uncertainty range. Flags the projected low point and any cash shortage. |
| F4 | Guardian risk detection | At least 3 working rules: low projected balance, unusual spending, high debt burden (insufficient emergency savings and upcoming payment pressure are the next candidates). Every alert has cause, supporting numbers, severity and a recommended action. |
| F5 | Digital Twin | At least 1 working scenario (spending cut). Recalculates projected balance, health score and Guardian alerts, and returns the baseline and scenario together for comparison. |
| F6 | AI Copilot | Chat endpoint that calls approved read-only backend tools. Never invents financial values. Can explain a Guardian alert, the score and a simulation result. |

**Next priority (not MVP):** Economic Intelligence (FRED: CPI, unemployment, interest rates; Economic Pressure Index).
**Stretch:** Wrapped, AI narration, advanced anomaly detection.

## 4. Demo scenario (drives all acceptance testing)

One fictional customer, shown in 3 minutes:
1. **Understand:** accounts, spending patterns, health score.
2. **Detect:** Guardian warns the projected balance will fall below the safety buffer before the next bill (illustrative: $2,400 now, $320 projected low, $500 buffer).
3. **Simulate:** cut discretionary spending by $200, and the projected low rises (illustrative: $520).
4. **Recommend:** the Copilot explains the change and the remaining uncertainty using the real calculations.
5. **Prepare:** the user picks a more resilient plan.

The seed data must contain a customer that reproduces steps 1–4 deterministically.

## 5. Non-functional requirements

- **Synthetic data only.** No real bank credentials are ever requested.
- **Deterministic math.** Balances, scores and projections are plain Python functions. The LLM explains results and calls read-only tools only.
- **Uncertainty shown.** Forecasts include ranges and state their assumptions. Forecasts are labeled "prototype estimates based on simulated data". Recommendations are never presented as guaranteed.
- **Read-only.** The system never moves money, executes transactions or changes accounts.
- **Secrets.** API keys live in environment variables, never in frontend code or Git. The Supabase service-role key stays on the backend. If auth is enabled, per-user access controls apply.
- **Fallbacks:** rolling-average baseline if LightGBM isn't ready; PNC synthetic dataset if Nessie is unavailable; a clearly labeled cached snapshot if FRED fails.
- **Forecast evaluation:** chronological train/validation/test split, MAE, compared against a moving-average baseline.

## 6. Data model (Supabase PostgreSQL, the only database)

| Table | Fields |
|---|---|
| users | id, name, email |
| accounts | id, user_id, account_type, balance |
| transactions | id, account_id, amount, category, date |
| recurring_bills | id, user_id, amount, due_date |
| financial_snapshots | id, user_id, score, net_worth, date |
| risk_alerts | id, user_id, severity, description, created_at |

Money columns use `NUMERIC`. Relations use foreign keys. Timestamps are kept for history. Forecasts and simulations are computed on demand and not stored for the MVP.

## 7. API contract (agree on this before parallel work)

| Endpoint | Purpose | MVP? |
|---|---|---|
| GET `/api/dashboard` | Financial overview | Yes |
| GET `/api/accounts` | Account information | Yes |
| GET `/api/transactions` | Transaction history | Yes |
| GET `/api/health` | Score and explanations | Yes |
| GET `/api/forecast?days=30` | Cash-flow predictions (7/30/90) | Yes |
| GET `/api/guardian` | Risk alerts and causes | Yes |
| POST `/api/simulate` | What-if scenarios | Yes |
| POST `/api/chat` | AI Copilot | Yes |
| GET `/api/economy` | Economic indicators and pressure | Next priority |
| GET `/api/wrapped` | Financial recap | Stretch |

The backend defines the Pydantic request and response models and publishes example JSON in `docs/api-contracts.md` immediately, so the frontend can build against mocks.

## 8. Repository layout (from the proposal)

```
frontend/   app/ (dashboard, forecast, guardian, simulator, economy, copilot, wrapped), components/, lib/
backend/    app/ (main.py, routes/, services/, schemas/, db/), intelligence/, requirements.txt
data/synthetic/    scripts/seed_database.py    tests/    docs/api-contracts.md
```

## 9. Backend scope (Member 2, built in this repo)

**In the MVP**
- B1. FastAPI app skeleton, config from environment variables, CORS for the frontend, health-check route.
- B2. Supabase schema (the 6 tables above) and a DB access layer.
- B3. `scripts/seed_database.py`: load PNC synthetic data (adapted from the PNC starter kit) plus a deterministic demo customer that reproduces the demo scenario.
- B4. Pydantic schemas and example payloads for every MVP endpoint, published in `docs/api-contracts.md` first.
- B5. Routes and services for `/api/dashboard`, `/accounts`, `/transactions`.
- B6. Deterministic calculation services the intelligence layer can reuse: net worth, income and expenses, emergency-savings coverage, upcoming-bill totals, baseline balance projection.
- B7. Integration routes for `/api/health`, `/forecast`, `/guardian`, `/simulate` and `/chat`. They call `backend/intelligence/` functions. Until Member 3 delivers, they return clearly marked stub or baseline results with the final response shape.
- B8. Deployment to Render (or similar) with environment-based secrets, and backend tests.

**After the MVP**
- FRED client and `/api/economy` with a cached fallback snapshot.
- Nessie integration if available.
- Optional Supabase Auth with per-user access.
- `/api/wrapped`.

**Backend definition of done**
- Every MVP endpoint returns data matching its Pydantic schema and the examples in `docs/api-contracts.md`.
- The demo customer reproduces the scenario end to end through the API.
- Tests pass, the service is deployed, and the README explains setup and the demo.

## 10. Open questions (to settle in backend design)

1. Whether the Supabase project already exists, or whether I should provide setup steps and SQL.
2. Whether to use the PNC starter-kit repo directly. I need its URL or a local copy, because I can't inspect it from here.
3. Whether the MVP needs auth. The proposal says optional, and I suggest a single demo user without auth.
4. Which stubs Member 3 should replace first (suggested order: health score, forecast, then Guardian).
