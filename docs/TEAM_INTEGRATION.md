# FinPilot team integration handoff

`gokul` includes the actual `backend-mvp` structure at `c033b4080fae94dbf4bda785f85a9a2e21d4f8c4` and Member 3's original intelligence modules, CLI commands, tests, mock data and reports. The GitHub repository retains the historical ForeCastle name; the application is FinPilot.

## Shared layout and ownership

```text
backend/app/                  Member 2: existing FastAPI, schemas, schedules, DB and baseline
backend/intelligence/         Member 3: original engines plus typed compatibility adapters
backend/scripts/              Member 2: original database seed command
backend/tests/                Backend tests plus Member 3 adapter/API tests
scripts/                      Original Member 3 commands plus backend example-dump script
tests/                        Original Member 3 tests
docs/api-contracts.md          Backend owner's canonical HTTP/Pydantic contract
docs/intelligence-contracts.md Preserved Member 3 dictionary/CLI contract
docs/examples/                Backend owner's endpoint examples
data/synthetic/               Fictional examples and editable stress cases
artifacts/reports/            Evaluation and stress reports
frontend/                     Reserved for Member 1; no placeholder app added
```

Keep routes, DB and response schemas in `backend/app/`; call intelligence functions rather than copying them into services. Coordinate shared schema changes with Member 1/2. The original audit predates this backend integration and must be read with that historical scope.

## Start the integrated backend (PowerShell, repository root)

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Open `http://localhost:8000/docs`. No configured database means built-in demo data. This command does not seed/reset a database; see `docs/supabase-setup.md` for the backend owner's explicit procedure. The backend's original `cd backend` / `uvicorn app.main:app` launch also works. Application imports remain `app.*`, while root CLI imports remain `backend.intelligence.*`. Both `scripts` namespaces are extended so database and ML commands coexist during tests.

The backend requirements retain all original dependencies and include the root copilot/ML requirements. Prefer Python 3.12+ for compatibility with the current ML lock; development is on Python 3.14. A clean-install version matrix has not been verified.

## Original Member 3 commands (repository root)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap-pnc.ps1
.venv/Scripts/python.exe -m backend.intelligence.training
.venv/Scripts/python.exe -m scripts.run forecast --customer C002 --all-horizons
.venv/Scripts/python.exe -m scripts.conditions_demo
.venv/Scripts/python.exe -m scripts.fetch_economy
.venv/Scripts/python.exe -m scripts.stress_test
```

Vendor data, `.venv`, raw FRED cache and model artifacts remain ignored. Fresh checkouts need bootstrap/training to use the saved models. API adapters use the supplied backend profile, not a substituted C002 snapshot. Missing/unsupported model history can select the explicit backend baseline. Deployment must provision models deliberately; artifact checksum/publication controls remain an audit remediation item.

## Gateway mappings

| Actual gateway lookup | Typed adapter | Original function retained |
| --- | --- | --- |
| `health_score.compute_health_score(profile)` | `backend_adapter.health_profile` | `health_score(customer)` |
| `forecast.forecast(profile, days)` | `forecast.py` → `backend_adapter.forecast_profile` | `forecasting.forecast_spending`, `project_cash` |
| `guardian.evaluate(profile, forecast)` | `backend_adapter.guardian_profile` | `guardian.detect_risks` |
| `simulate.simulate(profile, SpendingCut)` | `simulate.py` → `backend_adapter.simulate_profile` | `simulator.simulate(customer, spending, scenario)` |
| `copilot.chat(messages, tools)` | Compatibility dispatch → `registry_copilot.chat_messages` | Original dictionary/CLI `chat(...)` |

The adapter uses `FinancialProfile` and returns existing backend Pydantic models. Cash projections use the backend's Decimal weekly/biweekly/monthly schedule events. Basic ownership, duplicate IDs and future-history checks run before adapter inference. Backend categories differ from PNC training; warnings and actual fallback provenance are preserved.

Unavailable score components are omitted and weights renormalized to 100. `meta.source=model` means an intelligence implementation supplied the result, not that scoring or Guardian is trained ML. The gateway now preserves typed adapters' baseline source and warning rather than relabeling every return as model output.

The current backend schema exposes only SpendingCut. All seven original Member 3 scenario types and economic classifiers remain available through the original functions/CLI. There is no new `/api/economy` route or `EconomyResult` adapter. Category-specific forecast cuts are not implemented by the adapter and raise for explicit backend fallback. Preserve `INTELLIGENCE_MODE=baseline` for the backend owner's original demo behavior.

## Secrets and copilot

Each developer creates ignored local `.env` settings from the root/backend templates. Process environment takes precedence; registry chat lets backend `.env` override root `.env`. `COPILOT_PROVIDER=offline` uses the backend's deterministic calculation tools. Live Gemini/OpenAI use only the supplied profile's `tools.specs()`/`tools.call()`. Provider errors fall back through the backend gateway. No live LLM call was made during integration testing; original provider quota/service failures and semantic narration risks remain unresolved.

The optional `user_id` backend demo selector is not production authentication. Real deployments still need authorization and protected tenant access. Do not expose real account data using demo identity selection.

## Validation and known limits

From repository root run `.venv/Scripts/python.exe -m pytest -q`. The combined configuration covers both test folders. Integration verification: **146 passed, 1 skipped**; the skipped Postgres test requires a live DB and was not run. Automatic-mode checks exercise typed health, forecast, Guardian, simulation, API responses and offline registry chat. Original baseline tests remain intact. Source financial/model issues in `ENGINEERING_AUDIT.md` are not solved merely by adding adapters; the original audit is retained as a pre-merge snapshot.

Only `gokul` is pushed by this task. `main` and `backend-mvp` remain unchanged remotely. Including backend-mvp as a merge parent provides shared ancestry for later integration instead of disconnected copied history. Frontend alignment still needs Member 1's actual branch; unpublished layouts were not assumed.
