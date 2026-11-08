# FinPilot (FinSight AI)

AI-powered financial resilience platform for HackUTD 2026 (PNC 360° Financial Health Navigator).
Flow: **Detect** (Guardian) → **Simulate** (Digital Twin) → **Recommend** (Copilot).
All data is synthetic. Forecasts are prototype estimates. Nothing moves money.

- Requirements: [docs/MVP-requirements.md](docs/MVP-requirements.md)
- API contract and examples: [docs/api-contracts.md](docs/api-contracts.md), `docs/examples/`
- Team handoff (frontend + AI/ML): [docs/handoff-member-3-and-1.md](docs/handoff-member-3-and-1.md)
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

## Member 3 intelligence tools (run from the repository root)

HackUTD 2026 · PNC Financial Wellness · **Member 3: AI, ML & Financial Intelligence**

Understand your money. Anticipate risks. Prepare for what's next.

This repository implements the intelligence portion of the team blueprint (previously named FinSight). Member 1 owns the frontend; Member 2 owns FastAPI, authentication, Supabase, ingestion and FRED retrieval.

Teammates: start with the [team integration handoff](docs/TEAM_INTEGRATION.md) for shared folder ownership, root-level Python imports, dependency setup and API/data boundaries. The [engineering audit](docs/ENGINEERING_AUDIT.md) lists unresolved correctness and validation findings; this branch is a prototype, not a completed production application.

## Run locally (PowerShell)

Python 3.11+; verified locally with Python 3.14. No API keys needed to train, forecast, simulate or run the offline copilot.

```powershell
# Already completed in this workspace. Run bootstrap on a fresh checkout.
powershell -ExecutionPolicy Bypass -File scripts/bootstrap-pnc.ps1
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-ml.txt
.venv/Scripts/python.exe -m backend.intelligence.training
.venv/Scripts/python.exe -m scripts.backtest
.venv/Scripts/python.exe -m scripts.demo
.venv/Scripts/python.exe -m pytest tests -q
```

The actual environment versions are recorded in `requirements-ml.lock.txt`. Trained LightGBM text artifacts are under `artifacts/models/` (local, ignored by Git). Evaluation reports under `artifacts/reports/` and the sample output `data/synthetic/demo.json` can be shared with teammates. Retrain on a fresh checkout before serving the model; without artifacts, inference explicitly falls back to a rolling average.

## Implemented

- LightGBM median and 10th/90th quantile spending models, temporal splits, six held-out customers, baseline comparisons, and recursive horizon checks.
- 7–90-day spending forecasts and scheduled income/bill checking projections with uncertainty stress envelopes.
- Five-component explainable wellness score with missing-data handling.
- Guardian rules for low balances, emergency reserves, debt burden, payment pressure, budget overruns and macroeconomic pressure.
- Digital Twin scenarios for income loss, emergencies, spending cuts, savings transfers, extra debt payments and variable cost inflation.
- Economic Pressure Index accepting a dated backend indicator snapshot.
- Read-only copilot tool loop plus an offline calculation-grounded explanation.

## Structure

```text
backend/intelligence/    Member 3's importable Python package
  data.py               PNC ledger adapter
  features.py           Past-only daily spending features
  training.py           Train, validate, evaluate, save models
  forecasting.py        Recursive forecasts and cash projection
  health_score.py       Explainable wellness score
  guardian.py           Evidence-backed risk rules
  economic_pressure.py  Dated economic snapshot calculations
  simulator.py          Pure hypothetical scenario calculations
  copilot.py            OpenAI tools and offline fallback
  service.py            Backend-facing orchestration functions
scripts/                Bootstrap, backtest and demo commands
tests/                  Intelligence validation and regression tests
docs/                   Architecture, contracts, model card and provenance
data/synthetic/         Ready-to-use JSON demo output
artifacts/reports/      Measured evaluation results
vendor/                 Ignored, pinned upstream PNC checkout
```

## Backend handoff

```python
from backend.intelligence.data import load_customer, load_daily
from backend.intelligence.service import analyze
from backend.intelligence.simulator import simulate

customer = load_customer('C001')
daily = load_daily()
history = daily[daily.customer_id == customer['customer_id']]
result = analyze(customer, history, days=30)
comparison = simulate(customer, result['forecast'], {'monthly_spending_cut': 200})
```

Member 2 should translate authenticated database records into this normalized input, then return the corresponding result fields from the team's API routes. See [API contracts](docs/intelligence-contracts.md) and [architecture](docs/architecture.md).

For a plain-language explanation of what is predicted, file storage versus database responsibilities, and the next AI/ML work, see [Member 3 next steps](docs/member-3-next-steps.md). Project coding instructions are in `AGENTS.md`; the installed engineering workflows are described in [engineering workflow](docs/engineering-workflow.md).

## Gemini chatbot and environment variables

Forecasting and training need **no API keys**. For the Gemini chatbot:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-copilot.txt
# Run only if .env does not exist yet:
Copy-Item .env.example .env
```

Edit `.env` locally:

```dotenv
COPILOT_PROVIDER=gemini
GEMINI_API_KEY=your-google-ai-studio-key
GEMINI_MODEL=gemini-3.8-flash
```

Get a key from [Google AI Studio](https://aistudio.google.com/apikey). The API key authenticates requests; the model name selects which hosted Gemini model answers them. Use a function-calling text model available to your account. The example follows Google's SDK documentation; availability for your key is not verified. Leave `OPENAI_API_KEY` and `OPENAI_MODEL` blank when using Gemini. No Supabase or FRED keys are needed by this intelligence package.

Print and save an actual spending/cash forecast:

```powershell
.venv/Scripts/python.exe -m scripts.run forecast --customer C002 --days 30
```

Ask a personalized question using the same synthetic customer's snapshot and calculations:

```powershell
.venv/Scripts/python.exe -m scripts.run chat --provider gemini --customer C002 --question "Why is my financial health score low?"
.venv/Scripts/python.exe -m scripts.run chat --provider gemini --customer C002 --question "What happens if I cut monthly spending by 200 dollars?"
```

The chat CLI loads `.env` without overriding existing process variables. For a key-free fixed summary, use `--provider offline`. The demo command always runs offline, even when keys exist. The backend must load its own environment once at startup; `chat()` itself does not read `.env` files.

If a live request waits without answering, check key/model access separately:

```powershell
.venv/Scripts/python.exe -m scripts.check_gemini
```

This makes one model-metadata request with a 10-second request timeout, without sending financial data or generating text. Success confirms metadata access, not text generation or remaining generation quota. Live chat uses one attempt per request, a 30-second request timeout and a 2,048-token output cap. Tool calling can require multiple requests; these are per-request settings rather than a total conversation deadline. The CLI reports transport failures and cancellation without a raw provider traceback.

For an optional tiny generation test, run `python -m scripts.check_gemini --generate` using the project interpreter. This uses generation quota. HTTP 503/504 indicates a Google service failure or deadline, not proof of an invalid key. During the November 7 live check, model metadata succeeded, the dashboard chat returned HTTP 504, and a follow-up diagnostic returned HTTP 503. A successful live dashboard answer is therefore still unverified.

Use `python -m scripts.check_gemini --list-models` to list advertised text-generation models, or `python -m scripts.check_gemini --model MODEL_ID --generate` to test another model without editing `.env`. A model being listed does not guarantee this key can access it or that generation is healthy. In the follow-up check, a minimal request to the configured model returned HTTP 503, and metadata access for the listed `gemini-2.5-flash` returned HTTP 403. Neither establishes a working alternative; the configured model was left unchanged.

Gemini has `get_dashboard`, `get_analysis` and `simulate` tools. It answers from passed customer data, never by seeing the browser screen. Member 2 must pass the logged-in user's current snapshot and analysis to `chat()`. This supports personalized balance, score, risk and scenario questions without retraining Gemini or adding a vector database. Category-by-category history, individual transactions, goals and conversational memory need additional scoped inputs/tools; unsupported facts must not be invented.

The adapter follows the [Google Gen AI SDK function-calling documentation](https://googleapis.github.io/python-genai/). It preserves model content between tool calls and validates numeric tokens against calculation outputs. That check cannot establish semantic accuracy. The Gemini integration has local SDK/fake-response tests; no live call was made.

## Optional OpenAI alternative

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-copilot.txt
$env:OPENAI_API_KEY = 'your-key'
$env:OPENAI_MODEL = 'your-enabled-model'
```

Set `COPILOT_PROVIDER=openai` to select this alternative; it is unnecessary for Gemini. Call `copilot.chat()` with the authenticated customer's existing analysis and forecast. This uses the [official Responses API function-calling flow](https://developers.openai.com/api/docs/guides/function-calling). The live API path was tested using a fake client, not a paid network call.

## Prototype boundaries

All bundled data and demo customers are synthetic. Health weights, risk thresholds and economic index weights are transparent design assumptions, not validated financial guidance. Forecasts are estimates. Quantile bounds are uncalibrated; summed bounds are stress envelopes rather than calibrated balance intervals. The economic module supplies no live indicators until Member 2 passes a dated snapshot. See the [model card](docs/model-card.md) for evaluation limits and ledger assumptions.

The starter repository is [devfulcrum/pnc-utd-hackathon-2026](https://github.com/devfulcrum/pnc-utd-hackathon-2026). Its license and pinned revision are documented in [third-party provenance](docs/third-party.md).

## Compare horizons, reserve alerts, and economic experiments

```powershell
.venv/Scripts/python.exe -m scripts.run forecast --customer C002 --all-horizons
.venv/Scripts/python.exe -m scripts.run forecast --customer C002 --all-horizons --savings-floor 1000 --fund-shortfalls-from-savings
.venv/Scripts/python.exe -m scripts.fetch_economy
.venv/Scripts/python.exe -m scripts.economy --as-of 2026-11-07 --customer C002
```

The first commands display consistent 7/30/90-day totals and app-ready Guardian events, including savings-floor breaches under the explicitly enabled reserve-funding assumption. They never execute transfers or send external messages. The economic commands download real public indicator histories and evaluate household macro forecasts separately from stock direction. Neither initial economic model beat its baselines, so stock direction currently **abstains**. See [economic research](docs/economic-research.md) for data, results and limitations. All these commands run without chatbot credits.

Observed-condition classification and exposure-based guidance are separate from those predictive experiments. Run `.venv/Scripts/python.exe -m scripts.conditions_demo` for a key-free example showing why the same weak market/economy can produce different guidance for different users. See [conditions and guidance](docs/conditions-and-guidance.md) for thresholds, loan/investment inputs and backend integration.

## CSV edge cases and stress output

```powershell
.venv/Scripts/python.exe -m scripts.stress_test
```

Edit `data/synthetic/stress-cases.csv` to change 52 declared cases. Inspect [readable stress results](artifacts/reports/stress-results.md), [CSV results](artifacts/reports/stress-results.csv) and the full JSON beside them. These exercise saved ML inference, condition rules, Guardian, simulations and separate macro/market research sensitivity. See [stress-testing methodology](docs/stress-testing.md) for the failures found, fixes and why case pass rate is not model accuracy.
