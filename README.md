# FinPilot (FinSight AI)

AI-powered financial resilience platform for HackUTD 2026 (PNC 360° Financial Health Navigator).
Flow: **Detect** (Guardian) → **Simulate** (Digital Twin) → **Recommend** (Copilot).
All data is synthetic. Forecasts are prototype estimates. Nothing moves money.

- Requirements: [docs/MVP-requirements.md](docs/MVP-requirements.md)
- API contract and examples: [docs/api-contracts.md](docs/api-contracts.md), `docs/examples/`
- Team handoff (frontend + AI/ML): [docs/handoff-member-3-and-1.md](docs/handoff-member-3-and-1.md)
- Gemini Financial Copilot setup and testing: [docs/ai-copilot.md](docs/ai-copilot.md)
- Copilot latency measurements: [docs/copilot-performance.md](docs/copilot-performance.md)
- Supabase setup: [docs/supabase-setup.md](docs/supabase-setup.md)

## Run the backend

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env            # optional; with no DATABASE_URL it serves built-in demo data
.venv/bin/uvicorn app.main:app --reload     # http://localhost:8000/docs
.venv/bin/pytest -q
```

Load the demo data into Supabase: `cd backend && .venv/bin/python -m scripts.seed_database --apply-schema --reset`

## Endpoints

`GET /healthz` · `GET /api/dashboard, /accounts, /transactions, /health, /forecast?days=7|30|90, /guardian` · `POST /api/simulate, /api/chat`.
All accept optional `?user_id=` (defaults to the demo customer, Alex Rivera).

## Architecture

Routes → services → repository (Postgres or in-memory) and pure calc functions. Intelligence calls go through a gateway that uses `backend/intelligence/*` modules (Member 3) when present, otherwise the built-in `backend/app/baseline/*`. See `backend/intelligence/README.md`.

## Demo script (3 minutes)

1. **Understand:** `/api/dashboard` shows accounts, spending, health score.
2. **Detect:** `/api/guardian` warns that checking (now $2,400) is projected to dip below the $500 buffer.
3. **Simulate:** POST the alert's `suggested_scenario` (try a $200 cut) to `/api/simulate` and compare projections.
4. **Recommend:** POST "what can I do?" to `/api/chat`; the reply quotes the real calculations.
5. **Prepare:** pick the more resilient plan.

## Deploy (Render)

Create a Blueprint from this repo (uses `render.yaml`). Set `DATABASE_URL` (Supabase Session pooler) and `CORS_ORIGINS` (the frontend URL). Free instances sleep; open `/healthz` before a demo. `AS_OF_DATE` pins the demo "today" to match the seeded data; reseed and update it when you want a new date.

## Safeguards

Synthetic data only; secrets in environment variables; deterministic Python for all numbers; the AI explains and calls read-only tools; uncertainty and prototype labels shown; no transactions or account changes.
